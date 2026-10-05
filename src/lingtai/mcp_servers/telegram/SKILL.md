---
name: telegram-mcp-manual
description: |
  Progressive-disclosure usage manual for the Telegram MCP tool. The resident
  schema carries safe first-use guidance; call `manual` for the action map,
  inbound-first/reply routing, channel/media/rendering rules, settings, Task Card
  projection, and error handling.
version: 1.10.0
last_changed_at: 2026-10-05T00:00:00Z
related_files:
- src/lingtai/tools/channel_reply/manual/SKILL.md
- src/lingtai/mcp_servers/telegram/reference/agent-switching/BEHAVIORS.md
- src/lingtai/mcp_servers/telegram/reference/agent-switching/CONTRACT.md
- src/lingtai/mcp_servers/telegram/reference/agent-switching/ANATOMY.md
- src/lingtai/mcp_servers/telegram/security.py
- src/lingtai/mcp_servers/telegram/channel_reply.py
- src/lingtai/mcp_servers/telegram/agent_switching.py
- src/lingtai/mcp_servers/ANATOMY.md
- src/lingtai/mcp_servers/task_card/event_projection.py
- src/lingtai/mcp_servers/task_card/resident.py
- src/lingtai/mcp_servers/local_commands/ANATOMY.md
- src/lingtai/mcp_servers/local_commands/core.py
- src/lingtai/mcp_servers/telegram/manager.py
- src/lingtai/mcp_servers/telegram/account.py
- src/lingtai/mcp_servers/telegram/render.py
- src/lingtai/mcp_servers/telegram/server.py
- src/lingtai/mcp_servers/telegram/_family.py
- src/lingtai/mcp_servers/telegram/settings.py
- src/lingtai/mcp_servers/telegram/service.py
- src/lingtai/mcp_servers/telegram/notification_header.md
- src/lingtai/mcp_servers/telegram/task_card/_family.py
- src/lingtai/mcp_servers/telegram/task_card/ANATOMY.md
- src/lingtai/mcp_servers/telegram/task_card/SKILL.md
- src/lingtai/mcp_servers/telegram/reference/rate-limits/SKILL.md
- src/lingtai/tools/task_card/manual/SKILL.md
- tests/test_telegram_structured_rendering.py
- tests/test_telegram_settings.py
- ENVIRONMENT_VARIABLES.md
maintenance: |
  Tracks the MCP server's manager/config/settings behavior; update when setup,
  settings precedence/redaction, or the public API surface changes. Keep this
  manual a concise router: detailed provider facts belong in the linked
  rate-limit and Task Card references, while this page retains first-use safety
  distinctions.
---

# Telegram MCP — usage manual

This progressive disclosure manual complements the routine schema. Use the schema for routine calls;
`telegram(action='manual', input={}, reasoning='...')` loads deeper guidance.
Registration, activation, private config, and setup belong
to `mcp-manual` → `reference/curated-addons.md`.

## First successful action: inbound first

The closed root is `{action, input, reasoning, summarize?}`: the first three
are required, `summarize` is optional and not action input, and only the selected
action's fields belong in `input`. `reasoning` is audit metadata, not a message;
`manual` and `settings` take `{}`.

1. When a current notification already carries the message to handle, its own
   compound `id` is a valid `reply` target directly. Do not call `check`,
   `read`, or `search` merely to reread that same text or to obtain an id
   already given. Otherwise, begin read-only with `check`, `read`, or `search`.
   `check` shows recent chats and incoming unread counts without marking read;
   `read` is the one-chat view, marks returned records read, and is also the
   correct way to recover required content absent from all available current
   copies. A `text_truncated` shorter preview does not require a reread when
   full current raw content is already available. Needed media without a
   local `path` or recorded `download_error` may require recovery.
2. Answer on Telegram, not private output. For one incoming message, `reply`
   with its exact compound `message_id` as given by the current notification/persistent
   record or `read`/`search`; never guess an ID.
3. For a standalone message, `send` to a real numeric `chat_id` with text, media (optionally captioned),
   rich content, or an indicator as described below. Contacts are local aliases, not inbound permission; account
   setup/configuration is not a tool call.
4. Inspect `status`, action fields, and `error` before assuming an effect.
   `send`, `reply`, `edit`, and `delete` are external message changes: verify
   the exact target first. `status='blocked'` is a duplicate-guard decision,
   not proof that the requested attachment was delivered; do not replay blindly.

Account aliases are optional where accepted; omission selects the service
default. With multiple accounts, pass one explicitly for stateful work. IDs are
`account_alias:chat_id:message_id`; synthetic `updates` IDs are read/search-only.

## Action map

| Action | Use and effect |
|---|---|
| `send` | New numeric-chat message: `text`, `media`, `structured_message`, or ephemeral `chat_action`. |
| `check` | Recent conversation summaries and incoming unread counts; no read effect. |
| `read` | Combined incoming/outgoing records for one chat; marks returned records read and clears its wake mirror. |
| `reply` | New durable message to a copied compound target; marks it handled and adds the replied reaction; does not edit it. |
| `search` | Case-insensitive regex over stored inbound text, sender fields, and update type; no read/send effect. |
| `edit` / `delete` | Edit/delete one bot message by compound ID; verify the exact target. |
| `contacts` / `add_contact` / `remove_contact` | Read/change local aliases only; no inbound authorization. |
| `accounts` | List safe account details; credentials are not returned. |
| `settings` | Read-only settings inventory; no writer. |
| `manual` | Return this packaged page and metadata; no Telegram operation. |

## Send, reply, media, and rendering

`send` requires a real numeric `chat_id` and text, media with an optional `text` caption,
native rich content, or an ephemeral indicator. These are not an exclusive
text/media choice. Content-bearing `send`, `reply`, and `edit` default to
`rendering_mode='Markdown'`. Modes are exactly `plain_text`, `HTML`, `Markdown`,
`MarkdownV2`, `entities`, and `rich`: named modes map to Telegram `parse_mode`,
`entities` supplies `MessageEntity[]`, and `plain_text` omits `parse_mode`. Do
not mix entity data with a parse-mode choice. Omit `rendering_mode` for ordinary
messages and write valid Telegram Markdown; use `plain_text` only when literal,
unformatted output is intentional, never as a generic safety fallback.

The resident Telegram Task Card is separate: its automatic and programmable
sections share one original Telegram `parse_mode='HTML'` message. Automatic rows
HTML-escape their dynamic plain text before adding the small supported visual
markup; when the shared frame is within its source budget, the adapter trims
only escaped dynamic content to account for those fixed tags and emojis. Author
the programmable `taskcard/taskcard.md` body as Markdown. At resident send/edit,
Telegram escape-first renders its ATX headings/subheadings, `**bold**`, inline
backtick code, and unordered, ordered, or task-list items into the closed Bot API
HTML subset. Raw HTML/special characters cannot become markup, and malformed or
unmatched delimiters remain safe literal text. The resident still stores the
authored bytes for diff-only composition. This changes no ordinary
`send`/`reply`/`edit` default and no other channel's Task Card renderer.

### Reply vs send

`reply` requires a copied compound `message_id` plus `text` or
`structured_message`. It sends a new response threaded to that target, marks
it handled, and attempts the replied reaction; `send` is a standalone message.
A successful reply is not a guarantee that the best-effort reaction succeeded.

`media` is `{type: 'photo'|'document', path: '...'}`. Use `document` for charts,
plots, reports, HTML/SVG/PNG/PDF exports, CSVs, and other generated artifacts the
user should open intact. Use `photo` only for an inline preview: Telegram may
crop, compress, or thumbnail it, making text-heavy graphics unreadable. Attach
the file, not a local path in message text; the outbound path must be inside the
agent working directory and readable/non-empty. `reply_markup` is only for
`send`/`edit`; `caption_entities` only for media `send` in `entities` mode;
`link_preview_options` and `disable_web_page_preview` are send-only text options.

For native rich content, omit `text` and `media`, set `rendering_mode='rich'`,
and supply `structured_message` with required `title`. Optional fields are
`summary`, `facts` (`{label, value}`), `bullets`, ordered `steps`, `code`
(`text`, optional `language`), `next` (`label`, `text`), and `footer`. Native
heading/paragraph/list/pre/divider/footer blocks preserve authored wording and
meaningful emoji. Rich content can send/reply/edit text or rich messages, but
cannot edit a media caption.

For work likely to exceed five seconds, `placeholder=true` sends interim text
and returns a compound ID; edit it at meaningful phases, then send the final
answer as a separate durable `send` or `reply`. A placeholder is progress-only
and separate from the Task Card. A `chat_action` (`typing`, `upload_photo`,
`upload_document`, `upload_voice`) without text/media is only an ephemeral
indicator, expires after about five seconds, and is not a message record; repeat
it deliberately or pass `''`/omit it.

## Read, search, and inbound records

`read` requires `chat_id` and accepts `limit` (default `10`); it combines
inbound/outgoing records, marks returned records read, and clears the matching
notification mirror. `chat_id='updates'` recovers synthetic non-chat updates
read-only. `search` requires regex `query`, accepts optional `account`/`chat_id`,
searches inbound text, sender names/usernames, and update type, does not mark
read, and errors on invalid regex syntax.

Each record has a concise view plus additive `telegram` with the complete raw Bot
API Update, branch, actor policy result, and unknown nested fields. Edited
messages retain append-only raw `edits`; `event_id` is root identity and
`current_event_id` the latest edit. Reactions, polls, member/boost/business
events, inline callbacks, and unknown branches are synthetic `updates` records
(`synthetic=true`) and never outbound targets. Use the raw envelope when preview
fields are insufficient.

Inbound photo/document/voice/audio retains metadata and, when available, an
absolute inbox `path`; voice may add `voice_transcript`. Use `vision` for
image-like attachments, not filename guesses. `download_error` retains metadata
without a path: read the text and ask for a resend/another transfer method. The
hosted Bot API `getFile` limit is 20 MB; no local Bot API server is configured.
Notification previews follow `notification_header.md`: for an ordinary
(non-synthetic) message record, handle the latest unresponded incoming
message using its own `id` and current full text directly — not for
ambiguity, callback presence, media, or an id already given. Synthetic
`updates` records and callback-only entries stay read/search-only and are
never reply targets. The agent SHOULD NOT reread required content already
complete in the final current notification, including usable raw Telegram
text/caption: `text_truncated` on a shorter copy or older-history overflow
does not change that. Call `read` only for required content absent from all
current copies (including omitted/id-only records), or needed media with no
local `path` and no `download_error`. An attachment already carrying
`download_error` needs a resend, not a reread.

## Slash commands and local preferences

The `/` picker and runtime handlers are separate. Optional per-account `commands`
register menu names without `/` through `setMyCommands`; registration creates no
handler. Built-ins include `/help`, `/status`, `/kanban`, `/system`, `/refresh`,
`/sleep`, `/clear`, and `/taskcard`; unknown commands remain ordinary inbound
messages. `/taskcard`, `/taskcard on|off`, `/taskcard N`, and
`/taskcard lang en|zh` change local preferences. `commands: []` clears the menu;
omitted/`null` uses the built-in menu. Config edits and refresh/restart are setup
operations, not MCP calls. Never print/place a bot token in this manual, chat,
logs, tests, or examples.

## SETTINGS SHOW

Call `telegram(action='settings', input={}, reasoning='inspect Telegram settings')`.
Success is exactly `{"settings": [...]}`; rows have `key`, `current`, `default`,
`configurable`, and `comment`. There is no writer. An unavailable fact returns
one `SETTINGS_UNAVAILABLE` failure with no partial rows. Account/config authority
is redacted; contacts, read markers, message records, offsets, and resident
routes are operational state. All six account/config rows redact both current
and default; all eleven rows are configurable. Account changes use the
authorized private account JSON procedure, preserve siblings/credentials and
policy, then restart/refresh and verify with SHOW plus the account/status path.
Restore the preserved prior value through the same owner if rollback is needed;
SHOW itself grants no change authority.

### Telegram config path
`config.path` is the resolved `LINGTAI_TELEGRAM_CONFIG` captured at startup;
relative values use `LINGTAI_AGENT_DIR` (or cwd). SHOW redacts it. Change through
the authorized launcher/config procedure and restart or refresh the MCP.

### Account aliases
`accounts.aliases` is the live service-order `accounts[].alias` snapshot and is
redacted because aliases bind account state and compound IDs. Change only in the
private account JSON, preserving credentials/policy, then restart/refresh and
verify with SHOW plus `accounts`.

### Bot tokens
`accounts.bot_tokens` aggregates credentials; both values are redacted. Only with
explicit owner authorization, rotate
through BotFather and private JSON, preserve permissions, restart/refresh, and
verify through the established account/status path. Never put a token in chat,
logs, tests, examples, or a settings response.

### Allowed users
`accounts.allowed_users`: omitted, `null`, and `[]` all mean unrestricted
admission; current/default values are redacted because IDs identify humans. A
saved contact does not alter this list.

### Account poll intervals
`accounts.poll_intervals` snapshots each `poll_interval`, default `1.0`; values
are preserved as-is without extra runtime validation and redacted in SHOW.

### Slash-command menu
`accounts.commands`: omitted/`null` means built-in, `[]` clears, and other
Telegram-compatible `{command, description}` objects apply best-effort at
startup. The aggregate is redacted; verify with SHOW, `/`, or safe status.

### Task Card poll interval
`automatic.poll_interval_seconds` is the import-time
`LINGTAI_TASKCARD_POLL_INTERVAL` snapshot (default `5.0`) for journal tailing,
programmable polling, and resident throttling. `float()` is used; non-finite
values make the all-or-nothing response unavailable. Change launcher environment
and fully restart the MCP.

### Task Card delivery
`automatic.enabled` is agent-wide `taskcard` in
`<workdir>/telegram/taskcard.json` (default `true`): it gates both slots without
stopping mechanics. Use `/taskcard on|off`, then `/taskcard` and SHOW.

### Task Card normal rows
`automatic.normal_rows` is the rolling API-call-group window (default `3`,
accepted `1..10`), not a tool-row count. Use `/taskcard N` and SHOW;
compatibility `max_refreshes` is not an active Telegram runtime ceiling.

### Task Card locale
`automatic.locale` is `en` by default and accepts `en` or `zh`; use
`/taskcard lang en|zh` and SHOW.

### Task Card display expression
`automatic.display_expression` is an allowlisted ordered list in
`<workdir>/telegram/taskcard.json`; default
`["footer","header","rows","blank","divider","metadata","time","ask_agent"]`.
A custom nonempty list has at most 32 entries from `header`, `rows`, `blank`,
`footer`, `divider`, `metadata`, `time`, `ask_agent`; invalid values fall back
wholesale. There is no slash editor: use an authorized atomic File/Shell edit,
preserve siblings, and verify with SHOW.

## Task Card: independent automatic and programmable projections

Automatic Task Card mechanically projects safe public `diary`/`tool_call`
events from durable history; it is not a turn-local heartbeat or completion
lifecycle. It omits hidden thinking, raw arguments/results, prompts, credentials,
paths, and private diagnostics; `normal_rows` counts API-call groups. The
`taskcard` boolean suppresses presentation of both slots while mechanics continue.

The public `task_card` tool is intrinsic and channel-neutral. Read
[`../../tools/task_card/manual/SKILL.md`](../../tools/task_card/manual/SKILL.md)
for `start | inspect | retry | stop | remove | settings | manual`, renderer,
recovery, limits, and cleanup. Telegram neither owns that tool/renderer nor
accepts its JSON/controller instructions. It only reads `taskcard/status` and
`taskcard/taskcard.md`: exact `active` + nonempty body projects a programmable
frame; exact `inactive` idempotently excludes only that frame. Missing/unreadable
status, active with missing/blank body, other status, or unchanged bytes are
no-ops. Telegram never rewrites producer files. Projection specifics are in
[`task_card/SKILL.md`](task_card/SKILL.md) and [`task_card/CONTRACT.md`](task_card/CONTRACT.md).

A changed programmable body causes a real Telegram edit/send and consumes quota;
diff-only skipping protects unchanged bytes, not renderer churn. Read
[`reference/rate-limits/SKILL.md`](reference/rate-limits/SKILL.md) before changing
cadence or recovery; it owns published quotas and `retry_after` semantics.

## AGENT SWITCHING: default-off target-only routing

Agent switching is a per-account, default-off transport feature.

**Platform warning:** V1 automatic state-lock selection is enabled only when the
runtime identity is exactly `os.name == "posix"` and `sys.platform == "darwin"`
(macOS). Linux, Windows, FreeBSD, and every other host are unsupported. On an
unsupported host, leaving the feature disabled preserves normal Telegram startup;
explicitly enabling it makes eager manager construction fail closed before any
poller starts, and the MCP remains error-only until the setting is disabled or the
Bot is moved to a supported macOS host. Do not use the example below on an
unsupported host.

Enable it only with an explicit account setting:

```json
{
  "accounts": [
    {
      "alias": "main",
      "bot_token": "<secret>",
      "allowed_users": [12345678],
      "agent_switching": {"enabled": true}
    }
  ]
}
```

When enabled, admitted humans in a private chat can use these local controls:

- `@agent-name` persistently selects one eligible target for later ordinary
  text messages from the same account + chat + human.
- `@agent-name <text>` routes one non-empty plain-text message without changing
  the saved selection.
- Exactly `@` or `/agent` lists eligible targets; `/agent status` shows the
  current target and `/agent reset` returns later messages to the owner Agent.
- `/agent@BotUsername ...` is accepted only for this Bot. Command and selector
  tokens are delimited by Telegram/Python whitespace (spaces, tabs, or newlines);
  malformed `/agent...` prefixes fail locally, while ordinary selected-message
  bodies retain their exact text. Names use exact LingTai Agent names (ASCII
  letters, digits, `_`, `-`); there is no fuzzy or display-name matching.
- `/start`, `/start <args>`, and forms addressed to this Bot remain the normal
  owner/admin setup path even after callback or persistent target selection. The
  switching router does not answer, mutate selection, mint authority, or wake a
  target; the account's existing local setup handler supplies the normal response.
- If saved selection state is corrupt, unsafe, unavailable, or unreadable, ordinary
  messages fail locally with no owner/admin or target provider projection. `/agent
  status` reports the unavailable state. `/agent reset` clears it, and a valid bare
  selector such as `@agent-name` atomically replaces it; neither path revokes
  authority already delivered to a target.

The `/agent` BotCommand entry is composed only for enabled accounts. If
`commands` is omitted, the normal defaults plus `/agent` are registered. A
custom non-empty list gains `/agent` unless it already contains that command;
a configured description is preserved. Explicit `commands: []` remains an
explicit empty Telegram menu even though typed controls are still handled.

Routing is deliberately narrower than the public Telegram MCP:

- Only verified live direct or nested avatar descendants advertising
  `channel_reply/v1` are eligible. Discovery rejects duplicate/ineligible chains
  before resolution, so lookup exposes one generic local ineligibility result
  rather than an unreachable special ambiguity message. Stale, replaced, dead,
  old-protocol, or otherwise ineligible targets fail the same way; there is no
  owner-Agent fallback.
- The owner keeps the lossless raw Telegram transport record, then stops before
  conversation preview, Task Card, LICC notification, or owner provider history.
  Exactly one target-local at-most-once LICC task is published for a successful
  route. After the new task is proven published, the router sends one anchored
  local confirmation with exact body `Routed to @<target>.`. It reserves a
  permanent body-free decision before the Telegram call, bound only to opaque
  route/target-pin/source-identity digests rather than private Telegram IDs, so
  replay/restart never sends a second confirmation. A positive Telegram message
  id queues only that successful confirmation for one best-effort deletion at or
  after about three monotonic seconds. The process-local queue is bounded and not
  durable; overflow, exit, or deletion failure may leave the confirmation visible
  but can never resend the confirmation, republish the task, reroute, or remint.
  Errors and uncertain sends are not auto-dismissed.
  This is at-most-once, not exactly-once: a crash
  around that send can leave the route delivered but the confirmation permanently
  absent or uncertain. The target receives a short-lived `channel_reply` capsule
  and never the Telegram Bot token, poller, public Telegram MCP, or owner ChatSession.
- Every owner-derived reply grant and target capsule expires exactly two hours
  after the route's creation time. Grant `created_at` is immutable owner/router
  issuance time and anchors that lifetime. For each concrete `channel_reply`
  submit, the target generates request `created_at` as the current UTC submission
  time; it is not exact owner authority and stale/future request checks still
  apply. `/agent reset` or reselection controls only future message routing: it
  does not retroactively revoke or erase a grant already delivered to a target,
  which may still submit its one reply until consumed, revoked by terminal
  failure, or expired.
- A target reply can use the capsule once. Immediately before the persisted
  sending barrier and again before the Telegram call, the owner revalidates the
  exact target identity, ledger chain, manifest, protocol, and live presence.
  Stale queued replies fail terminally without a Telegram call, and stale cached
  adapters are retired. The owner derives the account, chat, and original
  message anchor; deleted or unreplyable anchors fail terminally rather than
  sending an unanchored fallback. The running target is automatically awakened by
  its existing system notification path when the queued reply becomes
  `sent`, `failed`, `dead`, or `ambiguous`; it need not resubmit merely to poll.
  That event contains only public status/request/message/reference fields and no
  grant, proof, reply/routed body, Telegram destination, or path. Offline validated
  terminal truth is retained until notification is marked. The Store event and
  Core marker are separate, so a crash between them can produce a duplicate
  display; this is best-effort at-least-once with a stable dedupe key, not
  cross-store exactly-once.
- V1 accepts only ordinary non-empty text in admitted private human chats.
  Groups, channels, topics, media/captions, current or legacy forwarded messages,
  service events, and rich/media replies are not routed. When a saved target or
  one-shot directive applies, unsupported content receives a local error and
  wakes neither target nor owner. With neither selection nor switching directive,
  ordinary admin behavior remains unchanged.
- V1 never routes an edited message. After the lossless raw edit is durable, an
  admitted private-human edit is switching-owned when its text is selector- or
  `/agent`-directive-like under the existing parser/username rules, a saved
  selection is valid, selection state is unavailable, or `original-ownership`
  proves that exact original account/chat/user/message identity was routed within
  the seven-day horizon. It receives one generic local unsupported-content error
  anchored to the edited Telegram message and stops before owner preview, Task
  Card, notification, LICC, history, provider state, or any target publication.
  A strict body-free `edit-rejections/<digest>.json` decision makes replay of the
  same Telegram update local-reply idempotent across restart; unavailable decision
  state remains handled and may stay silent rather than risk a duplicate error.
  Reset or reselection changes only future new-message routing: it cannot
  declassify or reassign a marked original. With no selection, directive-like
  text, unavailable state, or live prior marker, ordinary admin edit behavior
  remains unchanged.
- Definite pre-publication failures get a generic local error. After a publication
  boundary, delivery may be indeterminate; V1 never retries or remints and may stay
  silent rather than claim success or failure that it cannot prove. Repeating the
  same Telegram update does not republish the target task.
- Before creating any target-visible capsule, router decision, or inbox event for
  a newly routed original, the owner commits a strict versioned private atomic and
  fsynced `state/original-ownership/<digest>.json` marker. Its filename/key is an
  opaque digest of the exact account/chat/user/message identity; the record stores
  only that digest plus creation/expiry times, never a routed/edited body, Telegram
  username, selector, or other human content. Missing markers are created once,
  exact duplicates reuse the same truth, and malformed, unreadable, conflicting,
  or inaccessible occupants fail closed before any target task.
- A dedicated worker runs retention immediately after startup and then every five
  minutes using a monotonic cadence. Each cycle inspects at most 128 total picker,
  raw-quarantine, original-ownership, and edit-rejection items and at most 128 currently registered
  target reply roots; one surface failure is isolated from all others and from
  poll/reply drains. Expired picker records are removed, raw quarantine and valid
  original-ownership markers and edit-rejection decisions are retained seven days,
  and Core grant/request/target reply state uses its seven-day retention rules.
  Menu/dead/original-ownership/edit-rejection discovery and target rotation are
  truly paginated with durable native cursors, not whole-directory scans.
  All four owner classes rotate fairly across restart. Reply drain also keeps a
  durable root-bound cursor and reuses the same exact target transport as cleanup,
  so bounded polls eventually pass large preserved unknown prefixes after restart.
  Drain and cleanup isolate each target/surface and whole cycle; monotonic liveness
  records last cycle and last success without route/private data.
  Unsafe or malformed ownership evidence is preserved rather than deleted into an
  apparent admin absence. Core separately persists fair cleanup class and scan
  progress, so sustained claims and process restart cannot starve receipts,
  consumed/dead state, capsules, or temp reconciliation. Tiny
  selection-unavailable tombstones remain until reset/reselection. Proof-free
  owner Core no-remint decisions and Telegram target router decisions are retained
  permanently, including terminal/ambiguous truth; cleanup never authorizes a
  remint, republish, or ambiguous-delivery retry.

The paired packaged state/writer details are in
`reference/agent-switching/CONTRACT.md` and
`reference/agent-switching/ANATOMY.md`.

This is a cooperative same-UID boundary, not hostile process isolation: sibling
Agents sharing the same OS account can ultimately read one another's files.
Strict owner/target state, single-use grants, no-symlink checks, and target-only
projection prevent accidental authority sharing and cross-Agent conversation
leaks within that deployment model.

## Errors and rate limits

Inspect every result's `error`, `status`, and action fields; no hidden retries are
scheduled. HTTP 429 returns `status='error'`, `error_code=429`, and
`auto_retry=false`; valid nonnegative `retry_after` adds `retryable=true` and
wait seconds for a new action. Missing/malformed cooldown metadata is omitted,
never guessed; do not send a second notice through the rate-limited route. Read
the rate-limit reference for official quotas, undocumented scope, and safe policy.
A duplicate send is `status='blocked'`, not a replay reason; media download
failure stays on the inbound record and triggers no automatic reply. The current
in-process send guard counts prior successful sends by account/chat/text; it
does not compare attachment bytes or paths. Reconcile the intended artifact
with returned receipts before any new authorized send; never alter wording just
to bypass the guard.
