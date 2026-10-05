---
name: channel-reply-behavior-tests
behavior_version: 1
labt_version: 2
contract: CONTRACT.md
anatomy: ANATOMY.md
related_files:
  - src/lingtai/tools/channel_reply/CONTRACT.md
  - src/lingtai/tools/channel_reply/ANATOMY.md
  - src/lingtai/tools/channel_reply/__init__.py
  - src/lingtai/kernel/channel_reply/__init__.py
  - src/lingtai/adapters/posix/channel_reply_state_lock.py
  - src/lingtai/agent.py
  - tests/test_channel_reply.py
maintenance: |
  Keep the Channel Reply Contract/Anatomy/Behavior loop reciprocal. Update these
  LABTs whenever authority, platform gating, one-shot delivery, or terminal
  notification behavior changes.
---
# Channel Reply Behavior Tests

## Behavior CR001 — closed-by-default declared capability

- **id**: CR001
- **guards**: `channel-reply` § Behavior and § Port and target transport
- **runner**: repository Python
- **prerequisites**: clean scratch directories; no Telegram credentials
- **estimate**: ≈ 2 minutes

### Steps
1. Run `python -m pytest -q tests/test_channel_reply.py`.
2. Inspect the focused results for unsupported-platform, missing-capsule, injected-Port, and manifest-marker cases.

### Expected evidence
- [ ] The official declared family remains visible while a closed Port performs no file/provider/channel effect.
- [ ] Only exact Darwin auto-composes the file Port; injected functional Ports remain supported.
- [ ] Functional composition alone advertises `channel_reply/v1`.

### Pass / Fail
Pass only when the focused suite proves all three outcomes without credentials or network access.

## Behavior CR002 — durable one-shot reply and public terminal truth

- **id**: CR002
- **guards**: `channel-reply` § Authority, identity, and retention
- **runner**: repository Python
- **prerequisites**: temporary owner/target stores
- **estimate**: ≈ 3 minutes

### Steps
1. Run the same focused suite's grant/request, crash-cut, duplicate, no-remint, drain, and notification cases.
2. Confirm any possible-send cut terminalizes as ambiguity and is never resent.

### Expected evidence
- [ ] Exactly one claim may cross the send barrier and destination/anchor remain owner-derived.
- [ ] Durable decisions prevent remint/replay after cleanup or malformed state.
- [ ] Terminal notification contains public fields only and is marked after Store publication.

### Pass / Fail
Pass when all one-shot and terminal-projection assertions hold; fail on any resend, target-chosen destination, or authority leak.
