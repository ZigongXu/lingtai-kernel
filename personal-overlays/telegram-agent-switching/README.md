# Personal Telegram Agent-switching overlay

This directory is the long-lived maintenance kit for Z.G's personal `@agent`
Telegram switching overlay.

It lives on the dedicated fork branch:

- maintenance kit: `personal/telegram-agent-switching-overlay`
- first accepted patched branch: `personal/telegram-agent-switching-v1-2026-09-01`

The fork's `main` branch is not used for personal changes. Official
`Lingtai-AI/lingtai-kernel` remains the upstream update source; every later
upstream update gets a new validated patched branch.

## Safety contract

The overlay remains:

- Darwin-only for automatic activation;
- disabled by default;
- HOLD / exploratory / product-decision-required upstream;
- cooperative same-UID rather than malicious same-UID containment.

Nothing in this directory installs a wheel, pushes a branch, updates the shared
Runtime, changes a Bot/configuration, refreshes an Agent, merges, releases, or
deploys.

## One-command maintenance flow

First fetch the upstream ref you want to test:

```bash
git fetch upstream main
```

Then run one command from any clean worktree of this fork:

```bash
./personal-overlays/telegram-agent-switching/maintain_overlay.py \
  --target upstream/main \
  --branch personal/telegram-agent-switching-YYYYMMDD-<upstream-short-sha> \
  --python /path/to/task-venv/bin/python
```

The supplied Python must already provide `pytest` and `build`. The command:

1. integrity-checks every bundled artifact;
2. replays the overlay in disposable clones;
3. runs the fixed feature/contract/tool/package tests;
4. compares governance failures against the clean target baseline;
5. builds a rollback-base wheel and an overlay wheel from the same target;
6. only after all gates pass, creates the requested **local** branch through a
   disposable apply clone without switching your current worktree.

Receipts, logs, and paired wheels are stored under the repository's Git metadata
at `personal-overlay-runs/` unless `--output-dir` is supplied. The command does
not push the created branch. After reviewing its receipt, push only the named
branch explicitly:

```bash
git push origin personal/telegram-agent-switching-YYYYMMDD-<upstream-short-sha>
```

To validate and build paired wheels without creating a branch:

```bash
./personal-overlays/telegram-agent-switching/maintain_overlay.py \
  --target upstream/main \
  --check-only \
  --python /path/to/task-venv/bin/python
```

## Exact first accepted version

| Field | Value |
|---|---|
| Tested upstream parent | `a10f0e4ad8dec25aa3a3a7d4cd4e855c00b73f2e` |
| Feature commit / first versioned branch head | `22567449cd799411b4d3b2f423b107c7508dfc1b` |
| Feature tree | `cb4d01525787a476fc78002f19857761b683a854` |
| Stable patch ID | `5f77cf7b6c6e8382f90e454dbab5e54cc3ee4d15` |
| Touched paths | 48 |
| Automatic platform gate | Darwin only |
| Default activation | Off |

Accepted exact-parent evidence: 434 focused tests, 8 contract-document tests,
180 tool-glossary tests, 21 real package-data tests, zero new governance failed
or error node IDs, and paired uninstalled rollback/overlay wheels.

## Package contents

- `overlay-manifest.json` — authoritative IDs, upgrade policy, fixed tests,
  known risks, and closed boundaries.
- `replay_overlay.py` — low-level check/apply primitive; default check-only.
- `maintain_overlay.py` — high-level full-check-then-local-branch command.
- `artifacts/telegram-agent-switching.patch` — binary full-index patch.
- `artifacts/telegram-agent-switching.bundle` — prerequisite-aware Git objects.
- `artifacts/touched-files.txt` — exact 48-path inventory.
- `artifacts/build-wheelhouse/` — pinned offline PEP 517 build inputs.

## Upgrade policy

A conflict, exact-parent tree mismatch, changed fixed-test count, package failure,
or new governance failure means **stop**. Do not force the old patch through.
Create a new version-specific adaptation commit, repeat the same full gates,
then update this kit's manifest, patch/bundle IDs, tree/commit IDs, tests, and
paired rollback/overlay wheel receipt.

Local installation is a separate phase. Before changing the shared Runtime,
compare the candidate with the version actually installed, preserve an exact
rollback artifact, validate in an isolated no-IM canary, and roll out one Agent
at a time with IM principals and the orchestrator last.
