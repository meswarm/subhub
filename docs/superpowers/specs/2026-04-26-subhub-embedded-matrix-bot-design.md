# SubHub Embedded Matrix Bot Design

## Goal

Refactor SubHub from a FastAPI service controlled through Link API tools into a standalone Matrix bot. The bot receives Matrix text messages, uses an LLM with local function tools to manage subscription data, stores data in local JSON files, handles R2 markdown attachments according to explicit switches, and sends responses directly back to Matrix.

SubHub should no longer require `ltool`, `config.toml`, HTTP API endpoints, or webhook forwarding.

## Non-Goals

- Do not keep the FastAPI API as a supported runtime surface.
- Do not keep webhook delivery for reminders or external events.
- Do not accept Matrix native media events as an input path.
- Do not parse video, audio, or generic file contents.
- Do not keep generic Link API/CLI tool abstractions in the SubHub main path.

## Runtime Overview

`make run` starts one SubHub bot process:

```text
Matrix m.text message
  -> SubHub bot
  -> R2 markdown attachment resolver
  -> LLM engine
  -> local SubHub tools
  -> SubHubService / SubscriptionStore
  -> LLM final response
  -> Matrix text reply
```

The reminder loop runs inside the same bot process:

```text
Reminder task tick
  -> SubHubService.get_today_reminders()
  -> SUBHUB_REMINDER_USE_LLM=false: send formatted Matrix text directly
  -> SUBHUB_REMINDER_USE_LLM=true: ask LLM to format, then send Matrix text
```

## Configuration

All runtime configuration comes from `.env`. `config.toml` is removed.

Sensitive and deployment-specific values live in `.env`, including Matrix credentials, LLM credentials, R2 credentials, system prompt, reminder behavior, download behavior, and storage paths.

Long business rules and domain instructions stay in versioned skill files under the repository, such as `link/agents/skills/manage-subscriptions/SKILL.md` or a migrated `skills/manage-subscriptions/SKILL.md`.

Required Matrix and LLM settings:

```env
MATRIX_HOMESERVER=https://matrix.example.com
MATRIX_USER=@subhub:matrix.example.com
MATRIX_PASSWORD=...
MATRIX_ROOMS=!roomid:matrix.example.com

SUBHUB_SYSTEM_PROMPT=...
SUBHUB_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
SUBHUB_LLM_API_KEY=...
SUBHUB_LLM_MODEL=qwen-plus
SUBHUB_LLM_TEMPERATURE=0.7
SUBHUB_LLM_MAX_HISTORY=20
SUBHUB_LLM_VISION_ENABLED=true
```

`SUBHUB_LLM_VISION_ENABLED` is the only runtime switch for multimodal image input. It should be set to `true` only when the configured model accepts image input.

Data storage settings:

```env
SUBHUB_DB_DIR=db
SUBHUB_DB_FILENAME=subscriptions.json
SUBHUB_DISMISSED_FILENAME=dismissed.json
```

By default, subscription data is stored at `./db/subscriptions.json`, and reminder dismissal state is stored beside it at `./db/dismissed.json`. `SUBHUB_DISMISSED_FILENAME` is resolved relative to `SUBHUB_DB_DIR` unless it is configured as an absolute path.

Reminder settings:

```env
SUBHUB_REMINDER_ENABLED=true
SUBHUB_REMINDER_ADVANCE_DAYS=3
SUBHUB_REMINDER_CHECK_INTERVAL_HOURS=1
SUBHUB_REMINDER_USE_LLM=false
SUBHUB_REPORT_BASE_CURRENCY=CNY
```

R2 settings:

```env
R2_ENDPOINT=...
R2_ACCESS_KEY=...
R2_SECRET_KEY=...
R2_BUCKET=link-media
R2_PUBLIC_URL=
```

Download settings:

```env
SUBHUB_DOWNLOAD_DIR=downloads
SUBHUB_DOWNLOAD_R2_IMAGES=true
SUBHUB_DOWNLOAD_R2_VIDEOS=false
SUBHUB_DOWNLOAD_R2_AUDIOS=false
SUBHUB_DOWNLOAD_R2_FILES=false
```

The default download layout is:

```text
downloads/
  imgs/
  videos/
  audios/
  files/
```

## Matrix Input and Output

The bot only registers a handler for Matrix text messages. It ignores Matrix native image, video, audio, and file events. Large media must be sent through R2 markdown links embedded in text.

The Matrix client should:

- Login with the configured account.
- Join configured rooms.
- Ignore messages sent by itself.
- Ignore historical messages from the first sync.
- Forward only new `m.text` message bodies to the bot.
- Send replies as Matrix text messages.
- Expose typing indicators as a best-effort feature.

## R2 Attachment Handling

SubHub treats R2 as the file transport layer. The bot scans incoming Matrix text for markdown links whose URL starts with `r2://`.

For each R2 link:

- Infer media kind from the object key path segment or file extension.
- Use type-specific download switches to decide whether to download the object.
- Store downloaded objects under `SUBHUB_DOWNLOAD_DIR/{imgs,videos,audios,files}`.
- Do not download non-R2 links.
- Do not parse video, audio, or generic file contents.

Image behavior:

- If `SUBHUB_DOWNLOAD_R2_IMAGES=true`, download image links to `downloads/imgs`.
- If `SUBHUB_LLM_VISION_ENABLED=true`, convert the downloaded image into the LLM's multimodal input format.
- If image download is disabled or vision is disabled, pass a text description to the LLM instead.

Video, audio, and file behavior:

- Default download switches are disabled.
- If enabled, the file is saved only.
- The LLM receives a text attachment description with name, type, and local path.
- SubHub does not inspect or parse these contents in the first version.

## LLM Engine

The embedded LLM engine should be a slimmed-down version of Link's `LLMEngine`:

- Use OpenAI-compatible Chat Completions.
- Keep conversation history isolated by Matrix room.
- Apply `SUBHUB_LLM_MAX_HISTORY`.
- Build a system prompt from `.env`, dynamic context, and skills.
- Support function calling with a bounded tool-call loop.
- Support multimodal image input only when enabled by config and model capability.

Dynamic context should be resolved through local tools before each user message:

- Current date.
- Current subscriptions.
- Known accounts.
- Known payment channels.

## Local Tool System

SubHub should not use Link's `APITool`, `CLITool`, or webhook tool path.

Instead, implement local function tools that call `SubHubService` directly. Tool definitions must remain OpenAI function-calling compatible.

Initial tools:

- `get_today_context`
- `get_subscriptions_context`
- `get_accounts_context`
- `get_channels_context`
- `list_subscriptions`
- `create_subscription`
- `update_subscription`
- `delete_subscription`
- `generate_monthly_report`
- `dismiss_reminder`

Tool execution returns JSON strings. Validation and business rules stay in `SubHubService` and `SubscriptionStore`.

## Business Logic and Storage

Keep the current domain boundary:

- `SubscriptionStore` owns JSON persistence and thread-safe CRUD operations.
- `SubHubService` owns subscription management use cases, validation, context generation, reports, and reminder queries.
- `display.py` owns markdown formatting.

Adjust configuration wiring so these components no longer depend on `config.toml`.

## Reminder Behavior

The reminder system runs inside the bot process.

When reminders are enabled, the bot periodically calls `SubHubService.get_today_reminders()`.

If there are reminder items:

- With `SUBHUB_REMINDER_USE_LLM=false`, format a concise markdown message locally and send it directly to all configured Matrix rooms.
- With `SUBHUB_REMINDER_USE_LLM=true`, ask the LLM to produce a concise notification, then send that text to all configured Matrix rooms.

Dismissed reminders remain persisted in `dismissed.json`.
The dismissed reminder path is configured by `SUBHUB_DISMISSED_FILENAME` and defaults to `./db/dismissed.json`.

The reminder loop should log each tick at debug level and log sent reminders at info level. Failures should be logged without stopping the bot process.

## Files to Remove

Remove API/webhook runtime files:

- `src/subhub/api.py`
- `src/subhub/webhook.py`
- API-specific tests.
- Webhook-specific tests.

Remove dependencies that are only needed for the deleted API path:

- `fastapi`
- `uvicorn`
- `httpx`, if no remaining tests or modules need it.

Remove `config.toml` from the runtime contract and documentation.

## Files to Keep or Refactor

Keep and adapt:

- `src/subhub/store.py`
- `src/subhub/service.py`
- `src/subhub/display.py`
- `src/subhub/reminder.py`, or replace it with an async reminder task if that produces a cleaner bot lifecycle.
- `src/subhub/config.py`, rewritten to load `.env`.
- `src/subhub/main.py`, rewritten as the bot entry point.

Add focused bot/runtime modules, with exact names to be finalized in the implementation plan:

- Matrix text client.
- LLM engine.
- Local tool registry.
- SubHub local tools.
- R2 protocol and media store.
- Attachment resolver.
- Bot orchestrator.

## Makefile and Logging

`make run` should start the bot with `uv run subhub`.

`make test` should run the full test suite.

The process should log:

- Bot startup summary with sensitive values redacted.
- Matrix login and joined rooms.
- Registered tools and loaded skills.
- R2 enabled/disabled state and download switches.
- Reminder loop enabled/disabled state.
- LLM calls, tool calls, and failures.

Logging should use Python's standard `logging` module.

## Testing Strategy

Tests should cover:

- `.env` config loading, including defaults for `db/` and `downloads/`.
- Local tool definitions and direct execution against a temporary JSON store.
- R2 markdown parsing and per-type download switch behavior.
- Image-to-vision gating logic.
- Matrix native media handlers are not registered.
- Reminder direct-send and LLM-format branches.
- Existing store/service/report behavior after config removal.

Network-facing Matrix, LLM, and R2 clients should be tested with fakes or mocks. Unit tests should not require real credentials.

## Migration Notes

The old Link agent YAML can remain as historical reference during development, but it is no longer the supported way to run SubHub.

Existing users should move runtime settings from `config.toml` and `link/agents/subhub.yaml` into `.env`.

Existing subscription JSON data can be moved to `./db/subscriptions.json`, or `SUBHUB_DB_DIR` and `SUBHUB_DB_FILENAME` can point to the previous file location.
