---
name: telegram-agent-switching-behavior-tests
behavior_version: 1
labt_version: 2
contract: CONTRACT.md
anatomy: ANATOMY.md
related_files:
  - src/lingtai/mcp_servers/telegram/reference/agent-switching/CONTRACT.md
  - src/lingtai/mcp_servers/telegram/reference/agent-switching/ANATOMY.md
  - src/lingtai/mcp_servers/telegram/SKILL.md
  - src/lingtai/mcp_servers/telegram/agent_switching.py
  - src/lingtai/mcp_servers/telegram/manager.py
  - src/lingtai/mcp_servers/telegram/server.py
  - tests/test_telegram_agent_switching.py
  - tests/test_telegram_agent_switching_ingress.py
maintenance: |
  Keep this switching Contract/Anatomy/Behavior loop reciprocal. Update the
  focused LABTs whenever admission, raw-first ordering, sticky ownership,
  target-only delivery, ACK dismissal, or cleanup semantics change.
---
# Telegram Agent Switching Behavior Tests

## Behavior TAS001 — raw-first target-only routing

- **id**: TAS001
- **guards**: `telegram-agent-switching-v1` § Behavior 2–8
- **runner**: repository Python
- **prerequisites**: temporary owner/target workdirs and fake Telegram accounts only
- **estimate**: ≈ 3 minutes

### Steps
1. Run `python -m pytest -q tests/test_telegram_agent_switching_ingress.py`.
2. Confirm handled updates persist the raw envelope before router evaluation and return before media, feedback, preview, Task Card, owner LICC, history, or provider effects.

### Expected evidence
- [ ] Only admitted direct-human plain text can route.
- [ ] Exactly one target inbox receives the body; the admin conversation does not.
- [ ] Router uncertainty fails closed after raw persistence.

### Pass / Fail
Pass only when the ingress matrix proves the raw-first and target-only boundaries.

## Behavior TAS002 — durable switching, reply, and transient ACK deletion

- **id**: TAS002
- **guards**: `telegram-agent-switching-v1` § Behavior 5–13
- **runner**: repository Python
- **prerequisites**: temporary state and fake Bot adapter only
- **estimate**: ≈ 4 minutes

### Steps
1. Run `python -m pytest -q tests/test_telegram_agent_switching.py`.
2. Inspect selection, sticky edit, no-republish, two-hour grant, reply drain, bounded cleanup, and route-ACK cases.

### Expected evidence
- [ ] Permanent body-free decisions prevent target republish, ACK resend, and authority remint.
- [ ] A positive ACK id alone queues one deletion after about three seconds; loss/failure only leaves the ACK visible.
- [ ] Cleanup is bounded/fair and cannot turn uncertainty into authority.

### Pass / Fail
Pass when the focused state/router suite proves all outcomes without network or live credentials.
