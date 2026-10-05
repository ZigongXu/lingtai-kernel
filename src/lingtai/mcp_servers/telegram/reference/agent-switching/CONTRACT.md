---
name: telegram-agent-switching-v1
contract_version: 1
root_contract: CONTRACT.md
related_files:
  - src/lingtai/services/mcp_inbox.py
  - src/lingtai/mcp_servers/telegram/service.py
  - src/lingtai/mcp_servers/telegram/account.py
  - src/lingtai/mcp_servers/telegram/reference/agent-switching/BEHAVIORS.md
  - src/lingtai/mcp_servers/telegram/reference/agent-switching/ANATOMY.md
  - src/lingtai/mcp_servers/telegram/SKILL.md
  - src/lingtai/mcp_servers/telegram/agent_switching.py
  - src/lingtai/mcp_servers/telegram/manager.py
  - src/lingtai/mcp_servers/telegram/channel_reply.py
  - src/lingtai/mcp_servers/telegram/security.py
  - src/lingtai/mcp_servers/telegram/server.py
  - src/lingtai/services/mcp_licc.py
  - src/lingtai/adapters/channel_reply_state_lock.py
  - src/lingtai/adapters/posix/channel_reply_state_lock.py
  - src/lingtai/kernel/channel_reply/__init__.py
  - src/lingtai/kernel/channel_reply/_mutation_lock.py
  - src/lingtai/agent.py
  - src/lingtai/tools/channel_reply/CONTRACT.md
  - src/lingtai/tools/channel_reply/ANATOMY.md
  - pyproject.toml
  - MANIFEST.in
  - tests/test_telegram_agent_switching.py
  - tests/test_telegram_agent_switching_ingress.py
  - tests/test_telegram_agent_switching_contract_docs.py
  - tests/test_telegram_secret_redaction.py
  - tests/test_channel_reply.py
  - tests/test_agent.py
maintenance: |
  Governed by the root CONTRACT.md. Keep the paired Anatomy, packaged Telegram
  manual, implementation ordering, state schemas, and focused tests synchronized;
  reverify every cited line range and bump contract_version for a breaking change.
---
# Telegram Agent Switching V1

## Purpose

Telegram Agent Switching V1 is a default-off, target-only route from one admitted
human in an owner Bot's private chat to one uniquely verified live avatar
descendant. The owner retains the Bot token, account, chat, original-message
anchor, poller, and public Telegram MCP. The target receives one bounded LICC task
and short-lived Core `channel_reply/v1` authority; it never receives owner
credentials or an owner ChatSession.

The invariant is sticky source-chat ownership: once switching selection,
directive syntax, selection unavailability, or a live prior-original marker makes
an edited message switching-owned, that edit is handled locally and can reach
neither a target nor the ordinary owner-provider route. The only variation axis is
a genuinely ordinary unselected, unmarked, non-directive edit, which preserves
the existing admin projection with `wake=false`. Non-goals are group/channel/topic
routing, media or rich-message routing, edited-message routing, hostile-process
isolation, target access to Telegram, Linux/Windows/FreeBSD support, and any
change to ordinary admin ingress when switching does not apply.

## Behavior

Guarded by: [TAS001](BEHAVIORS.md#behavior-tas001), [TAS002](BEHAVIORS.md#behavior-tas002).

1. **Activation and platform.** The feature is disabled unless an account sets
   `agent_switching.enabled` to true. Automatic file-state locking is available
   only when runtime identity is exactly `os.name == "posix"` and
   `sys.platform == "darwin"`. A disabled account preserves ordinary startup.
   Explicit enablement on any other host fails eager manager construction before
   pollers start and leaves the MCP error-only until disabled or moved to macOS.
2. **Admission and selection.** Only an admitted non-Bot human in a positive-id
   private chat may use switching. A bare selector persistently pins one exact
   eligible descendant; a selector with text routes once without changing the
   pin. Duplicate or ambiguous descendant paths, stale/replaced/dead Agents,
   protocol mismatch, invalid selectors, and malformed callback bindings fail
   locally without owner fallback or target wake.
3. **Owner-local commands.** `/start`, `/start <args>`, and forms addressed to
   this Bot remain the normal owner-local setup path. For those commands,
   switching creates no response, authority, target wake, or selection mutation.
   Menu, status, reset, selection, and callback controls remain owner-local.
4. **Raw-first ingress order.** The manager first durably stores the lossless raw
   Telegram update or appends the raw edit to the original record. Only then does
   it invoke switching. The switching router resolves command/selection state and,
   for edits, original ownership plus edit-rejection state. A handled result
   returns before conversation preview, Task Card, notification, owner LICC,
   history, provider state, or ordinary fallback routing.
5. **Edited-message ownership.** V1 never target-routes an edited message. An
   admitted private-human edit is always local-handled when its text is selector-
   or `/agent`-directive-like under the current parser/username rules, saved
   selection is valid or unavailable, or original ownership is owned or
   unavailable. Reset and reselection cannot declassify a marked original.
   Only when the directive is ordinary, selection is absent, and original
   ownership is absent may the edit fall through to existing admin projection;
   that fallback records the edit and publishes it with `wake=false`.
6. **At-most-once edit rejection.** Before sending the generic local unsupported-
   edit reply, the owner reserves a strict body-free v1
   `edit-rejections/<event-digest>.json` decision keyed by the exact account,
   Telegram update, chat, human, and original-message identity. `new` sends one
   reply anchored to the edited Telegram message; `existing` sends none;
   malformed, unreadable, conflicting, future, or inaccessible state is
   unavailable and remains handled, possibly silent, rather than risking a
   duplicate reply or unintended fallback.
7. **Sticky original ownership.** Before creating any target-visible capsule,
   target router decision, or LICC event for a newly routed original, the owner
   commits `original-ownership/<identity-digest>.json`. Its strict body-free v1
   schema is exactly `version`, `identity_digest`, `created_at`, and `expires_at`.
   It contains no routed or edited body, selector, username, token, grant proof,
   destination, or local path. Missing records are create-once; exact valid
   duplicates reuse truth; expired valid records may be replaced. Malformed,
   unreadable, conflicting, future, unsafe, or inaccessible occupants fail closed
   before the first target-visible write and are preserved as unavailable evidence.
8. **Target publication and no-republish truth.** A successful route creates a
   short-lived target capsule, then a strict target-local producer decision, then
   one target LICC event. Producer decisions bind the target pin, grant reference,
   event id, body digest, payload digest, immutable grant-issued creation time,
   update time, and
   `reserved|published|failed` status without storing the body, proof, Bot token,
   or destination. Existing terminal or ambiguous reservations never authorize a
   second publication. Definite pre-publication failures receive a generic local
   error. Once publication may have happened, delivery is indeterminate: the
   router does not retry, remint, or assert an unprovable outcome. It may remain silent.
   Redelivery of the same Telegram update never republishes the task. After and
   only after a newly created inbox event returns success and its target decision
   is durably `published`, the router reserves a permanent strict body-free owner
   ACK decision before invoking the existing anchored local-reply helper once with
   exact body `Routed to @<target>.`. The decision binds the opaque route identity
   plus opaque target-pin and source account/chat/human/message digests; it persists
   no raw private Telegram identifiers. A valid positive Telegram message id marks
   `sent`; a normal invalid result or caught send exception marks `ambiguous`.
   Existing `reserved|sent|failed|ambiguous` decisions never call Telegram again.
   Reservation/finalization failure cannot roll back, revoke, remint, republish, or
   change target delivery. This is at-most-once ACK, not exactly-once: a crash after
   reservation but before a Telegram commit can permanently lose the display, and
   a crash after the send barrier but before finalization remains possible-send
   uncertainty forever. Only a positive ACK message id enters a process-local
   due-time/insertion-order queue for deletion at or after three monotonic seconds.
   The queue holds at most 1,024 items, drops the newest ACK on overflow, and the
   existing drain worker pops at most 100 due items per cycle before issuing each
   synchronous Telegram delete unlocked. Every deletion is one-shot and isolated:
   queue loss on process exit, overflow, or a Telegram deletion failure may leave
   the success ACK visible, but never retries deletion, ACK send, publication,
   remint, or target delivery. Generic route-error replies and ambiguous ACK sends
   never enter this queue and remain governed by their existing persistent/error
   semantics.
9. **Reply authority.** Owner-derived reply grants and target capsules expire exactly two hours after
   route creation. The grant's `created_at` is immutable owner/router issuance time
   and anchors that lifetime. Each concrete target submit instead creates
   request `created_at` as the current UTC submission time; it is not an exact owner authority value.
   Core still rejects stale or future request timestamps. The owner
   revalidates the exact target identity and reply anchor both before the sending
   barrier and at the Telegram call. A target may submit one plain-text reply; the
   owner derives the account, positive private chat id, and original message anchor.
   Missing, invalid, stale, replaced, or unreplyable anchors fail terminally without
   an unanchored fallback. Core terminal receipt enumeration is bounded and
   restart-safe. The target's ordinary Agent owns a 0.5-second worker that projects
   validated `sent|failed|dead|ambiguous` truth through its existing system
   notification Store using one opaque stable tuple key. It includes only status,
   request id, bounded public message, and optional public ref, then writes Core's
   strict result-notified marker only after compare/update applied or already-
   present return. A malformed/conflicting proof-free marker cannot suppress a
   valid receipt and is replaced only after that Store truth. Unnotified valid
   terminal truth is retention-pinned while the target is offline. Publication
   failure stays retryable; a crash between Store
   publication and the Core marker can cause one duplicate display, so this is not
   a cross-store exactly-once transaction.
10. **Selection state.** Selection reads are `absent`, `valid`, or `unavailable`.
    Malformed JSON, wrong fields, unsafe shape, conflicting identity, and read
    failures are unavailable rather than absent and cause local handling with no
    owner/provider or target projection. `/agent status` reports unavailable;
    reset clears it and a valid bare selector atomically replaces it. Reset or reselection controls future routing only;
    it does not erase delivered reply authority or sticky ownership within retention.
11. **Retention and fairness.** A dedicated worker runs once immediately after
    startup and every five minutes thereafter on a monotonic deadline. Each cycle
    budgets 128 total owner-state inspections. The cleanup schema v4 rotates the
    four owner classes `menus`, `dead`, `original_ownership`, and `edit_rejections`
    within that one total owner-state budget. Each class has a persistent native-directory
    cursor and bounded pending names; `next_class` makes the first class rotate
    fairly across restart. A failed class keeps its cursor and consumes its quota
    while other classes continue independently. Target roots use a separate
    persistent identity cursor and at most 128 roots per cycle, one Core record per
    selected root; owner Core cleanup is one additional record. No path performs a
    whole-directory materialization or sorted rescan. The independent reply-drain
    worker uses the same exact adapter/target transport for drain and cleanup.
    Core alternates one-inspection claims/outbox steps and persists proof-free,
    root-identity-bound native cursors; intermediate `progress` is not empty, so
    large unknown prefixes and process reconstruction cannot starve later work.
    Whole cycles, adapter construction/refresh, and individual targets are guarded
    independently. Public monotonic liveness exposes only each worker's last-cycle
    and last-success timestamps and never target, route, body, or authority data.
12. **Retention outcomes.** Menu records use their own expiry. Raw quarantine,
    valid original-ownership markers, and valid edit-rejection decisions expire
    after seven days; unsafe or malformed ownership evidence is preserved rather
    than deleted into apparent absence. Core grant/request/target-reply state uses
    its seven-day retention contract. Selection-unavailable tombstones remain
    until reset or valid replacement. Core owner no-remint decisions and Telegram
    target router decisions and owner-local route-ACK decisions are permanent
    proof-free/body-free truth. Valid target receipts/consumed markers remain
    pinned until a matching strict result-notified marker exists. Cleanup cannot
    authorize remint, republish, duplicate local rejection or route ACK, terminal
    notification loss, or ambiguous-delivery retry.
13. **Threat boundary.** Hidden marker/temp names, callback tokens, selector text,
    duplicate or ambiguous target paths, edit anchors, target-visible event files,
    and stale/corrupt/malicious local state are attacker-controlled inputs. Every
    authority-bearing read is exact-schema, identity-bound, bounded, no-symlink,
    and fail-closed. Failures must not expose Bot tokens, proofs, message bodies,
    usernames, selectors, tracebacks, or local filesystem paths in public errors
    or logs, and must not create unintended owner/provider or target delivery.
    Same-UID siblings can ultimately read one another's files; this is cooperative
    deployment isolation, not a hostile-process security boundary.

## Port

- `TelegramAgentSwitchingRouter.handle(account_alias, update, branch) -> bool` is
  the manager boundary. `True` means the raw record is the only owner ingress and
  the manager must return. `False` permits the pre-existing ordinary route.
- `channel_reply/v1` is the only target reply Port. Targets submit a fresh
  request id, current request timestamp, opaque grant reference, proof, and plain
  text through the intrinsic; account/chat/message authority stays owner-side.
- LICC v1 is the target task delivery Port. The owner publishes exactly one
  identity-bound event with `wake=true` only after durable original ownership and
  target reservation exist.
- There is no public Agent-switching MCP family and no target Telegram adapter.
  Telegram's existing public tool remains owner-local.

## Adapters

- `TelegramManager` is the raw-ingress and early-return adapter.
- `TelegramAgentSwitchingRouter` owns parsing, descendant discovery, selection,
  sticky edit policy, target reservation, publication, reply drains, and cleanup.
- `AgentSwitchingStateStore` owns strict private owner state, permanent body-free
  route-ACK decisions, and schema v4 cursors.
- `select_channel_reply_state_lock()` selects the Darwin POSIX descriptor-safe
  mutation adapter or fails closed on every other runtime identity.
- Core `ChannelReplyFileStore`, target capsule/submit Port, owner transport, and
  owner controller own single-use authority, receipts, restart-safe drain/
  notification enumeration, result-notified markers, recovery, and Core state.
- Outer `lingtai.Agent` owns terminal receipt projection into its already-existing
  system notification Store and the notifier thread's post-Core lifecycle.
- `TelegramChannelReplyAdapter` derives and revalidates the owner-side Telegram
  anchor and performs the only Bot API reply send.
- `push_inbox_event` atomically publishes the target LICC event; Telegram process
  logging safety sanitizes provider/public failures without message or secret echo.

## Contract rules

1. Raw Telegram persistence must precede switching evaluation. A handled switch or
   edit must return before every owner/provider and ordinary fallback surface.
2. Selected, marked, directive-like, unavailable-state, and prior-owned edits are
   source-chat-owned forever within their live evidence horizon; none may reach a
   target or be reclassified by reset/reselection.
3. Only a genuinely ordinary unselected, unmarked, non-directive edit may use the
   existing admin route, and that route must carry `wake=false`.
4. Original-ownership and edit-rejection ledgers remain strict, body-free v1
   schemas. Unknown fields, unsafe shapes, conflicting identity, parse/I/O errors,
   and future timestamps fail closed rather than becoming absence.
5. Original ownership must be durable before any target-visible capsule,
   reservation, or LICC publication. Edit-rejection truth must be durable before
   the one anchored local error. Ambiguity chooses silence, not duplicate effects.
6. Target producer decisions are separate from Core state and permanent. Neither
   cleanup nor missing target inbox files may authorize task republication.
7. Reply grants/capsules are two-hour, exact-target, single-use authority. Reply
   submission time is target-authored current UTC time; the owner keeps all
   destination and anchor authority and revalidates it at both send barriers.
8. Cleanup progress remains schema v4, one budget of 128 across four owner classes,
   persistently fair across restart, bounded without whole-directory scans, and
   isolated per surface. Seven-day deletion applies only to validated expirable
   records; unsafe ownership evidence is not erased into a fail-open absence.
9. Public/logged failure text is bounded and content-free. No error may disclose
   tokens, proofs, bodies, selectors, usernames, tracebacks, or local paths.
10. Explicit enablement must remain exact-Darwin-only and fail before pollers on an
    unsupported platform; disabled accounts must remain behaviorally unchanged.
11. The route ACK is reserved body-free before its only Telegram call and is
    attempted only after newly proven publication plus durable target `published`;
    all uncertainty is final and never changes route/grant/task truth.
12. Target drain is hard-bounded, unknown-preserving, restart-safe, and liveness-
    observable without private data. Progress is not no-work.
13. Terminal receipt notification is target-owned, public-field-only, and marked
    only after normal Store compare/update return. Offline truth is pinned; the
    cross-store marker gap is explicitly best-effort rather than exactly-once.

## Contract tests

- `tests/test_telegram_agent_switching.py:1750-1992` pins sticky edited-message
  ownership, unavailable-state handling, body-free v1 records, marker-before-
  target ordering, reset/reselection behavior, rejection idempotence, and expiry.
- `tests/test_telegram_agent_switching.py:1128-1749` pins schema v4 budgeting,
  persistent four-class/target fairness, bounded native enumeration, failure
  isolation, restart progress, and permanent no-republish decisions. Its
  responsiveness acceptance block at `tests/test_telegram_agent_switching.py:1993-2219`
  pins progress through 600 preserved unknown outbox names,
  shared drain/cleanup cache identity, per-target and whole-cycle worker isolation,
  monotonic liveness, body-free ACK reserve-before-send, send uncertainty, and
  finalization-crash no-resend/no-republish behavior.
- `tests/test_telegram_agent_switching_ingress.py:311-801` pins raw-first target-
  only routing, fail-closed exceptions, ordinary fallback, and zero provider
  projection for unavailable selection state.
- `tests/test_telegram_agent_switching_ingress.py:1423-1612` pins selected,
  directive-like, ordinary, corrupt-selection, prior-owned, and first-marker-
  failure edit ingress through the production manager.
- `tests/test_telegram_agent_switching_contract_docs.py:21-220` pins packaged
  Contract/Anatomy/manual truth, platform selection, ordering, schemas, threat
  boundary, and package data.
- `tests/test_channel_reply.py:190-5447` pins the exact platform adapter, Core
  single-use state/authority/recovery/retention, Telegram anchor adapter, native
  mutation boundary, bounded cleanup, and no-remint truth; its terminal block pins
  all four terminal notification statuses, stable strict markers, bounded restart
  enumeration, unknown preservation, and absent-root inertness.
- `tests/test_agent.py` pins public-only notification projection, mark-after-Store
  ordering, before/after-publication crash cuts, stable idempotency keys, and
  functional/closed notifier lifecycle.
- `tests/test_telegram_secret_redaction.py:37-526` pins process, logger, manager,
  and public-tool secret/error sanitization.

## Maintenance

When routing, edit classification, state schema, retention, platform support,
reply authority, or target publication changes, update this Contract, the paired
Anatomy, the packaged `SKILL.md`, and the focused tests in the same change. Re-run
Contract/doc governance plus the full eight-file offline matrix. Reverify every
Anatomy and test line range against current code; line drift is documentation
drift. Breaking Port or normative behavior changes require a `contract_version`
bump and an explicit migration/recovery statement.
