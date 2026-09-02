#!/usr/bin/env python3
"""Dry-run or apply the fixed Telegram Agent-switching overlay.

Default behavior is check-only: clone the requested target into a temporary
workspace, import the signed-off feature commit from the bundled Git objects,
and perform a three-way cherry-pick without mutating the source repository.
Use --apply with an explicit new branch name only after reviewing a successful
check receipt. This script never installs a wheel into a runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "overlay-manifest.json"
BUILD_WHEELHOUSE = ROOT / "artifacts" / "build-wheelhouse"


def run(
    argv: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    cp = subprocess.run(
        argv,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and cp.returncode:
        detail = (cp.stderr or cp.stdout).strip().splitlines()[-12:]
        raise RuntimeError(
            f"command failed ({cp.returncode}): {' '.join(argv)}\n"
            + "\n".join(detail)
        )
    return cp


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo, check=check)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict[str, Any]:
    data = json.loads(MANIFEST_PATH.read_text())
    if data.get("schema") != "lingtai.telegram-agent-switching-overlay/v1":
        raise RuntimeError("unsupported overlay manifest schema")
    for row in data["artifacts"]:
        path = ROOT / row["path"]
        if not path.is_file():
            raise RuntimeError(f"missing overlay artifact: {row['path']}")
        actual = sha256_file(path)
        if actual != row["sha256"] or path.stat().st_size != row["bytes"]:
            raise RuntimeError(f"overlay artifact integrity mismatch: {row['path']}")
    return data


def require_repo(repo: Path) -> None:
    if not repo.is_dir():
        raise RuntimeError(f"repository path is not a directory: {repo}")
    inside = git(repo, "rev-parse", "--is-inside-work-tree").stdout.strip()
    if inside != "true":
        raise RuntimeError("not a Git worktree")


def resolve(repo: Path, ref: str) -> str:
    return git(repo, "rev-parse", "--verify", f"{ref}^{{commit}}").stdout.strip()


def clone_at(source: Path, target_sha: str, dest: Path) -> None:
    run(["git", "clone", "--quiet", "--shared", "--no-checkout", str(source), str(dest)])
    git(dest, "checkout", "--quiet", "--detach", target_sha)


def import_overlay(repo: Path, manifest: dict[str, Any]) -> str:
    ref = "refs/lingtai-overlay/telegram-agent-switching-v1"
    bundle = ROOT / manifest["bundle"]["path"]
    git(repo, "fetch", "--quiet", str(bundle), f"{manifest['bundle']['ref']}:{ref}")
    commit = resolve(repo, ref)
    if commit != manifest["feature"]["commit"]:
        raise RuntimeError(f"bundle imported unexpected commit: {commit}")
    return ref


def cherry_pick_no_commit(repo: Path, commit: str) -> tuple[bool, str]:
    cp = git(repo, "cherry-pick", "--no-commit", commit, check=False)
    if cp.returncode:
        conflicts = git(repo, "diff", "--name-only", "--diff-filter=U", check=False).stdout.splitlines()
        return False, ", ".join(conflicts) or (cp.stderr.strip().splitlines()[-1] if cp.stderr.strip() else "unknown conflict")
    diff_check = git(repo, "diff", "--cached", "--check", check=False)
    if diff_check.returncode:
        return False, "git diff --cached --check failed"
    return True, ""


def parse_pytest(text: str) -> dict[str, Any]:
    failed = sorted(set(re.findall(r"^FAILED\s+(\S+)", text, flags=re.MULTILINE)))
    errors = sorted(set(re.findall(r"^ERROR\s+(\S+)", text, flags=re.MULTILINE)))
    passed_matches = re.findall(r"(?:^|\s)(\d+) passed", text)
    return {
        "passed": int(passed_matches[-1]) if passed_matches else 0,
        "failed_nodeids": failed,
        "error_nodeids": errors,
    }


def offline_build_env() -> dict[str, str]:
    if not BUILD_WHEELHOUSE.is_dir():
        raise RuntimeError(f"offline build wheelhouse missing: {BUILD_WHEELHOUSE}")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    env["PIP_NO_INDEX"] = "1"
    env["PIP_FIND_LINKS"] = str(BUILD_WHEELHOUSE)
    return env


def pytest_run(
    *,
    repo: Path,
    python: Path,
    label: str,
    paths: list[str],
    log_dir: Path,
) -> dict[str, Any]:
    log_dir.mkdir(parents=True, exist_ok=True)
    basetemp = log_dir / f"basetemp-{label}"
    # The maintained archive tests invoke an isolated `pip wheel` internally.
    # Preserve that real package boundary while provisioning its build system
    # solely from the integrity-checked wheelhouse bundled beside this script.
    env = offline_build_env()
    cp = run(
        [
            str(python),
            "-m",
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            "--tb=no",
            "--basetemp",
            str(basetemp),
            *paths,
        ],
        cwd=repo,
        env=env,
        check=False,
    )
    text = cp.stdout + ("\n" if cp.stdout and cp.stderr else "") + cp.stderr
    log_path = log_dir / f"{label}.log"
    log_path.write_text(text)
    parsed = parse_pytest(text)
    parsed.update({"label": label, "exit_code": cp.returncode, "log": str(log_path)})
    return parsed


def build_wheel(repo: Path, python: Path, out_dir: Path, label: str) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    cp = run(
        [str(python), "-m", "build", "--wheel", "--outdir", str(out_dir)],
        cwd=repo,
        env=offline_build_env(),
        check=False,
    )
    if cp.returncode:
        raise RuntimeError(f"{label} wheel build failed: {(cp.stderr or cp.stdout).strip().splitlines()[-1]}")
    wheels = sorted(out_dir.glob("*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"{label} wheel build produced {len(wheels)} wheels")
    wheel = wheels[0]
    return {
        "label": label,
        "path": str(wheel),
        "bytes": wheel.stat().st_size,
        "sha256": sha256_file(wheel),
    }


def check_mode(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, Any]:
    source = args.repo.resolve()
    target_sha = resolve(source, args.target)
    started = time.time()
    receipt: dict[str, Any] = {
        "schema": "lingtai.overlay-check-receipt/v1",
        "mode": "check",
        "source_repo": str(source),
        "target_ref": args.target,
        "target_sha": target_sha,
        "feature_commit": manifest["feature"]["commit"],
        "artifact_integrity": "pass",
        "mutated_source_repo": False,
    }
    with tempfile.TemporaryDirectory(prefix="lingtai-telegram-overlay-") as td:
        tmp = Path(td)
        base = tmp / "base"
        overlay = tmp / "overlay"
        clone_at(source, target_sha, base)
        clone_at(source, target_sha, overlay)
        overlay_ref = import_overlay(overlay, manifest)
        ok, reason = cherry_pick_no_commit(overlay, manifest["feature"]["commit"])
        receipt["apply"] = {"status": "pass" if ok else "conflict", "detail": reason}
        if not ok:
            receipt["elapsed_seconds"] = round(time.time() - started, 3)
            return receipt
        overlay_tree = git(overlay, "write-tree").stdout.strip()
        receipt["overlay_tree"] = overlay_tree
        receipt["exact_baseline"] = target_sha == manifest["feature"]["parent"]
        if receipt["exact_baseline"]:
            expected = manifest["feature"]["tree"]
            receipt["exact_tree_match"] = overlay_tree == expected
            if overlay_tree != expected:
                raise RuntimeError(f"exact baseline replay tree mismatch: {overlay_tree} != {expected}")
        if args.run_tests:
            if args.python is None:
                raise RuntimeError("--run-tests requires --python")
            # Preserve a virtualenv's bin/python symlink; resolving it would bypass
            # pyvenv.cfg and silently lose pytest/build from that environment.
            python = Path(os.path.abspath(os.fspath(args.python)))
            if not python.is_file():
                raise RuntimeError(f"test interpreter missing: {python}")
            logs = args.output_dir.resolve() / "test-logs"
            tests: list[dict[str, Any]] = []
            for group in manifest["compatibility_tests"]["must_pass"]:
                row = pytest_run(repo=overlay, python=python, label=group["name"], paths=group["paths"], log_dir=logs)
                if row["exit_code"] != 0 or row["passed"] != group["expected_passed"]:
                    raise RuntimeError(f"{group['name']} gate failed; see {row['log']}")
                tests.append(row)
            governance = manifest["compatibility_tests"]["baseline_compare"]
            base_row = pytest_run(repo=base, python=python, label="governance-base", paths=governance["paths"], log_dir=logs)
            overlay_row = pytest_run(repo=overlay, python=python, label="governance-overlay", paths=governance["paths"], log_dir=logs)
            new_failures = sorted(
                (set(overlay_row["failed_nodeids"]) | set(overlay_row["error_nodeids"]))
                - (set(base_row["failed_nodeids"]) | set(base_row["error_nodeids"]))
            )
            if new_failures:
                raise RuntimeError("overlay introduced governance failures: " + ", ".join(new_failures))
            if overlay_row["exit_code"] != 0 and not (overlay_row["failed_nodeids"] or overlay_row["error_nodeids"]):
                raise RuntimeError(f"governance overlay failed without parseable node IDs; see {overlay_row['log']}")
            tests.extend([base_row, overlay_row])
            receipt["tests"] = {"status": "pass", "groups": tests, "new_governance_failures": []}
        if args.build_wheels:
            if args.python is None:
                raise RuntimeError("--build-wheels requires --python")
            python = Path(os.path.abspath(os.fspath(args.python)))
            wheel_root = args.output_dir.resolve() / "wheels"
            receipt["wheels"] = [
                build_wheel(base, python, wheel_root / "rollback-base", "rollback-base"),
                build_wheel(overlay, python, wheel_root / "overlay", "overlay"),
            ]
        git(overlay, "update-ref", "-d", overlay_ref, check=False)
    receipt["elapsed_seconds"] = round(time.time() - started, 3)
    return receipt


def apply_mode(args: argparse.Namespace, manifest: dict[str, Any]) -> dict[str, Any]:
    if not args.branch:
        raise RuntimeError("--apply requires --branch NEW_NAME")
    repo = args.repo.resolve()
    if git(repo, "status", "--porcelain=v1", "--untracked-files=all").stdout.strip():
        raise RuntimeError("apply requires a completely clean repository")
    target_sha = resolve(repo, args.target)
    if git(repo, "show-ref", "--verify", "--quiet", f"refs/heads/{args.branch}", check=False).returncode == 0:
        raise RuntimeError(f"branch already exists: {args.branch}")
    overlay_ref = import_overlay(repo, manifest)
    try:
        if target_sha == manifest["feature"]["parent"]:
            git(repo, "branch", args.branch, manifest["feature"]["commit"])
        else:
            git(repo, "switch", "--quiet", "-c", args.branch, target_sha)
            cp = git(repo, "cherry-pick", manifest["feature"]["commit"], check=False)
            if cp.returncode:
                raise RuntimeError("cherry-pick conflicted; resolve only after updating the adaptation manifest, or run git cherry-pick --abort")
        head = resolve(repo, args.branch)
        return {
            "schema": "lingtai.overlay-apply-receipt/v1",
            "mode": "apply",
            "target_sha": target_sha,
            "branch": args.branch,
            "head": head,
            "exact_authoritative_commit": head == manifest["feature"]["commit"],
            "note": "No wheel was installed and no runtime/Agent was refreshed.",
        }
    finally:
        git(repo, "update-ref", "-d", overlay_ref, check=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True, help="clean upstream Git worktree/repository")
    parser.add_argument("--target", default="HEAD", help="upstream ref/commit to receive the overlay")
    parser.add_argument("--apply", action="store_true", help="create/apply to a real branch; default is isolated check-only")
    parser.add_argument("--branch", help="new branch name for --apply")
    parser.add_argument("--run-tests", action="store_true", help="run manifest compatibility tests in disposable clones")
    parser.add_argument("--build-wheels", action="store_true", help="build base rollback and overlay wheels; never installs them")
    parser.add_argument("--python", type=Path, help="Python with pytest/build installed")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "run-output", help="logs/wheels/receipt output")
    args = parser.parse_args()
    manifest = load_manifest()
    require_repo(args.repo.resolve())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    receipt = apply_mode(args, manifest) if args.apply else check_mode(args, manifest)
    receipt_path = args.output_dir.resolve() / ("apply-receipt.json" if args.apply else "check-receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt.get("apply", {}).get("status", "pass"), "receipt": str(receipt_path)}, sort_keys=True))
    return 0 if receipt.get("apply", {}).get("status") != "conflict" else 3


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"overlay replay failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
