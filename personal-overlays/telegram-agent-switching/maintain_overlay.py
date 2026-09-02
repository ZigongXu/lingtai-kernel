#!/usr/bin/env python3
"""Validate the bundled Telegram Agent-switching overlay, then create a local branch.

The command is intentionally fail-closed. It always performs the full disposable
replay, fixed compatibility tests, baseline-governance comparison, and paired
wheel build before it creates a branch. Branch creation happens in a disposable
shared clone and is fetched back into the source repository, so the caller's
checked-out worktree is never switched. It never pushes, installs a wheel,
updates a Runtime, or refreshes an Agent.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parent
REPLAY = ROOT / "replay_overlay.py"


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and cp.returncode:
        detail = (cp.stderr or cp.stdout).strip().splitlines()[-16:]
        raise RuntimeError(
            f"command failed ({cp.returncode}): {' '.join(argv)}\n"
            + "\n".join(detail)
        )
    return cp


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo, check=check)


def resolve(repo: Path, ref: str) -> str:
    return git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").stdout.strip()


def require_clean_repo(repo: Path) -> None:
    if not repo.is_dir():
        raise RuntimeError(f"repository path is not a directory: {repo}")
    if git(repo, "rev-parse", "--is-inside-work-tree").stdout.strip() != "true":
        raise RuntimeError(f"not a Git worktree: {repo}")
    dirty = git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip()
    if dirty:
        raise RuntimeError("maintenance command requires a completely clean repository")


def validate_branch_name(repo: Path, branch: str) -> None:
    git(repo, "check-ref-format", "--branch", branch)
    exists = git(
        repo,
        "show-ref",
        "--verify",
        "--quiet",
        f"refs/heads/{branch}",
        check=False,
    )
    if exists.returncode == 0:
        raise RuntimeError(f"branch already exists: {branch}")


def git_dir(repo: Path) -> Path:
    raw = git(repo, "rev-parse", "--path-format=absolute", "--git-dir").stdout.strip()
    return Path(raw).resolve()


def load_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise RuntimeError(f"expected JSON object: {path}")
    return data


def run_replay(argv: list[str]) -> None:
    cp = run([sys.executable, str(REPLAY), *argv], check=False)
    if cp.returncode:
        detail = (cp.stderr or cp.stdout).strip().splitlines()[-20:]
        raise RuntimeError("overlay replay failed:\n" + "\n".join(detail))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo",
        type=Path,
        default=None,
        help="clean LingTai Kernel worktree (default: current Git worktree root)",
    )
    parser.add_argument(
        "--target",
        default="upstream/main",
        help="already-fetched upstream ref/commit to receive the overlay",
    )
    parser.add_argument(
        "--python",
        type=Path,
        required=True,
        help="task-local Python with pytest and build installed",
    )
    parser.add_argument(
        "--branch",
        help="new local validated branch; required unless --check-only",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="run all gates and build paired wheels without creating a branch",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="new receipt/log/wheel directory (default: inside the repository Git dir)",
    )
    args = parser.parse_args()

    if not REPLAY.is_file():
        raise RuntimeError(f"missing bundled replay tool: {REPLAY}")
    repo = (
        args.repo.resolve()
        if args.repo is not None
        else Path(git(Path.cwd(), "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    )
    require_clean_repo(repo)

    python = Path(os.path.abspath(os.fspath(args.python)))
    if not python.is_file():
        raise RuntimeError(f"test/build interpreter missing: {python}")
    probe = run([str(python), "-c", "import build, pytest"], check=False)
    if probe.returncode:
        raise RuntimeError("--python must provide both pytest and build")

    target_sha = resolve(repo, args.target)
    if not args.check_only:
        if not args.branch:
            raise RuntimeError("--branch is required unless --check-only is used")
        validate_branch_name(repo, args.branch)
    elif args.branch:
        raise RuntimeError("--branch and --check-only cannot be used together")

    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    output = (
        args.output_dir.resolve()
        if args.output_dir is not None
        else git_dir(repo) / "personal-overlay-runs" / f"{stamp}-{target_sha[:12]}"
    )
    if output.exists():
        raise RuntimeError(f"output directory already exists: {output}")
    output.mkdir(parents=True)

    check_output = output / "check"
    run_replay(
        [
            "--repo",
            str(repo),
            "--target",
            target_sha,
            "--run-tests",
            "--build-wheels",
            "--python",
            str(python),
            "--output-dir",
            str(check_output),
        ]
    )
    check_receipt_path = check_output / "check-receipt.json"
    check_receipt = load_json(check_receipt_path)
    if check_receipt.get("apply", {}).get("status") != "pass":
        raise RuntimeError("check receipt does not record a clean replay")
    if check_receipt.get("tests", {}).get("status") != "pass":
        raise RuntimeError("check receipt does not record passing compatibility tests")
    wheels = check_receipt.get("wheels")
    if not isinstance(wheels, list) or len(wheels) != 2:
        raise RuntimeError("check receipt does not record paired rollback/overlay wheels")

    combined: dict[str, Any] = {
        "schema": "lingtai.personal-overlay-maintenance-receipt/v1",
        "mode": "check-only" if args.check_only else "check-and-create-branch",
        "source_repo": str(repo),
        "target_ref": args.target,
        "target_sha": target_sha,
        "check_receipt": str(check_receipt_path),
        "branch": None,
        "branch_head": None,
        "pushed": False,
        "installed": False,
        "runtime_refreshed": False,
    }

    if not args.check_only:
        apply_output = output / "apply"
        with tempfile.TemporaryDirectory(prefix="lingtai-personal-overlay-apply-") as td:
            apply_repo = Path(td) / "repo"
            run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(repo), str(apply_repo)])
            git(apply_repo, "checkout", "--quiet", "--detach", target_sha)
            run_replay(
                [
                    "--repo",
                    str(apply_repo),
                    "--target",
                    target_sha,
                    "--apply",
                    "--branch",
                    args.branch,
                    "--output-dir",
                    str(apply_output),
                ]
            )
            apply_receipt_path = apply_output / "apply-receipt.json"
            apply_receipt = load_json(apply_receipt_path)
            branch_head = apply_receipt.get("head")
            if not isinstance(branch_head, str) or len(branch_head) != 40:
                raise RuntimeError("apply receipt has no valid branch head")
            if apply_receipt.get("target_sha") != target_sha:
                raise RuntimeError("apply receipt target differs from the checked target")
            git(
                repo,
                "fetch",
                "--quiet",
                str(apply_repo),
                f"refs/heads/{args.branch}:refs/heads/{args.branch}",
            )
            if resolve(repo, args.branch) != branch_head:
                raise RuntimeError("fetched branch head differs from the apply receipt")
            combined.update(
                {
                    "branch": args.branch,
                    "branch_head": branch_head,
                    "apply_receipt": str(apply_receipt_path),
                }
            )

    combined_path = output / "maintenance-receipt.json"
    combined_path.write_text(json.dumps(combined, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "status": "pass",
                "target_sha": target_sha,
                "branch": combined["branch"],
                "branch_head": combined["branch_head"],
                "receipt": str(combined_path),
                "note": "No branch was pushed; no wheel was installed; no Runtime or Agent was refreshed.",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(2)
