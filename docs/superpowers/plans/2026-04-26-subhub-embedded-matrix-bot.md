# SubHub Embedded Matrix Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn SubHub into a standalone Matrix bot that uses an embedded LLM/tool runtime and local JSON storage, with no FastAPI API, webhook, `config.toml`, or `ltool` dependency.

**Architecture:** Keep `SubscriptionStore`, `SubHubService`, and `display.py` as the domain core. Add focused bot runtime modules for `.env` config, local tools, R2 markdown attachment resolution, LLM function calling, Matrix text transport, and async reminders. `make run` starts the bot process and `make test` verifies unit behavior with fakes.

**Tech Stack:** Python 3.12, uv, pytest, pytest-asyncio, python-dotenv, matrix-nio, openai, aiohttp, aiofiles, aioboto3.

---

## File Structure

- Modify: `pyproject.toml`
  - Remove FastAPI/Uvicorn/httpx.
  - Add Matrix/LLM/R2 runtime dependencies.
- Modify: `Makefile`
  - Keep `make run` as `uv run subhub`.
  - Keep `make test`.
- Delete: `config.toml`
- Modify: `README.md`, `README_EN.md`
  - Document `.env` bot runtime and remove API/webhook/ltool instructions.
- Modify: `src/subhub/config.py`
  - Replace TOML config loader with `.env` config dataclasses.
- Modify: `src/subhub/store.py`
  - Accept an explicit dismissed reminder filepath.
- Modify: `src/subhub/main.py`
  - Become the async bot entry point.
- Modify: `src/subhub/reminder.py`
  - Keep `check_reminders` and remove the thread-based runtime after the async reminder loop is in place.
- Create: `src/subhub/tools.py`
  - Local OpenAI-compatible tool definitions and execution.
- Create: `src/subhub/r2_protocol.py`
  - R2 URI, markdown, media-kind, local-path helpers.
- Create: `src/subhub/media_store.py`
  - R2/S3 download helper with local caching.
- Create: `src/subhub/attachments.py`
  - Resolve incoming R2 markdown links according to download and vision switches.
- Create: `src/subhub/skills.py`
  - Load `SKILL.md` files into the system prompt.
- Create: `src/subhub/llm_engine.py`
  - OpenAI-compatible chat completions, function calling, room history, optional image input.
- Create: `src/subhub/matrix_client.py`
  - Matrix text-only client wrapper.
- Create: `src/subhub/bot.py`
  - Orchestrator connecting Matrix, attachments, LLM, tools, service, reminders.
- Create: `src/subhub/reminder_task.py`
  - Async reminder loop and direct/LLM formatting branches.
- Create: `skills/manage-subscriptions/SKILL.md`
  - Migrated business skill content.
- Create: `skills/manage-subscriptions/references/domain-rules.md`
  - Migrated skill reference content.
- Create: `.env.example`
  - Non-secret template for all required runtime settings.
- Delete: `src/subhub/api.py`
- Delete: `src/subhub/webhook.py`
- Delete: `tests/test_api.py`
- Delete: `tests/test_webhook.py`
- Delete: `link/README.md`
- Delete: `link/config-template.yaml`
- Delete: `link/agents/subhub.yaml`
- Delete: `link/agents/skills/manage-subscriptions/SKILL.md`
- Delete: `link/agents/skills/manage-subscriptions/references/domain-rules.md`
- Modify: `tests/test_store.py`
  - Add dismissed filepath coverage.
- Create: `tests/test_config.py`
- Create: `tests/test_tools.py`
- Create: `tests/test_r2_protocol.py`
- Create: `tests/test_attachments.py`
- Create: `tests/test_llm_engine.py`
- Create: `tests/test_matrix_client.py`
- Create: `tests/test_reminder_task.py`
- Modify: `tests/test_reminder.py`
  - Keep coverage for `check_reminders`.

---

### Task 1: Add Bot Dependencies and Env Template

**Files:**
- Modify: `pyproject.toml`
- Create: `.env.example`

- [ ] **Step 1: Add bot runtime dependencies**

Keep the existing API dependencies until Task 8 removes the API entrypoint and tests. Add the bot runtime dependencies so the current API runtime remains testable during the transition:

```toml
dependencies = [
    "aiofiles>=23.0.0",
    "aiohttp>=3.9.0",
    "aioboto3>=13.0.0",
    "fastapi>=0.115.0",
    "httpx>=0.27.0",
    "matrix-nio>=0.24.0",
    "openai>=1.0.0",
    "python-dotenv>=1.0.0",
    "uvicorn>=0.30.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
]
```

Keep the existing script:

```toml
[project.scripts]
subhub = "subhub.main:main"
```

- [ ] **Step 2: Add `.env.example`**

Create `.env.example`:

```env
MATRIX_HOMESERVER=https://matrix.example.com
MATRIX_USER=@subhub:matrix.example.com
MATRIX_PASSWORD=change-me
MATRIX_ROOMS=!roomid:matrix.example.com

SUBHUB_SYSTEM_PROMPT=你是一个个人订阅管理助手。
SUBHUB_SKILLS_DIR=skills/manage-subscriptions
SUBHUB_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
SUBHUB_LLM_API_KEY=change-me
SUBHUB_LLM_MODEL=qwen-plus
SUBHUB_LLM_TEMPERATURE=0.7
SUBHUB_LLM_MAX_HISTORY=20
SUBHUB_LLM_VISION_ENABLED=false

SUBHUB_DB_DIR=db
SUBHUB_DB_FILENAME=subscriptions.json
SUBHUB_DISMISSED_FILENAME=dismissed.json
SUBHUB_REPORT_BASE_CURRENCY=CNY

SUBHUB_REMINDER_ENABLED=true
SUBHUB_REMINDER_ADVANCE_DAYS=3
SUBHUB_REMINDER_CHECK_INTERVAL_HOURS=1
SUBHUB_REMINDER_USE_LLM=false

R2_ENDPOINT=
R2_ACCESS_KEY=
R2_SECRET_KEY=
R2_BUCKET=link-media
R2_PUBLIC_URL=

SUBHUB_DOWNLOAD_DIR=downloads
SUBHUB_DOWNLOAD_R2_IMAGES=true
SUBHUB_DOWNLOAD_R2_VIDEOS=false
SUBHUB_DOWNLOAD_R2_AUDIOS=false
SUBHUB_DOWNLOAD_R2_FILES=false

SUBHUB_LOG_LEVEL=INFO
```

- [ ] **Step 3: Sync dependencies**

Run:

```bash
make sync
```

Expected: `uv sync` completes and `uv.lock` updates.

- [ ] **Step 4: Verify legacy tests still run**

Run:

```bash
make test
```

Expected: PASS. This guards the transition until the API is removed in Task 8.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock .env.example
git commit -m "chore: add matrix bot runtime dependencies"
```

---

### Task 2: `.env` Configuration and Store Paths

**Files:**
- Modify: `src/subhub/config.py`
- Modify: `src/subhub/store.py`
- Modify: `tests/test_store.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write config tests**

Create `tests/test_config.py`:

```python
from pathlib import Path

from subhub.config import load_config


def test_load_config_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MATRIX_HOMESERVER", "https://matrix.example.com")
    monkeypatch.setenv("MATRIX_USER", "@subhub:matrix.example.com")
    monkeypatch.setenv("MATRIX_PASSWORD", "secret")
    monkeypatch.setenv("MATRIX_ROOMS", "!room:matrix.example.com")
    monkeypatch.setenv("SUBHUB_LLM_BASE_URL", "https://llm.example.com/v1")
    monkeypatch.setenv("SUBHUB_LLM_API_KEY", "key")
    monkeypatch.setenv("SUBHUB_LLM_MODEL", "qwen-plus")
    monkeypatch.setenv("SUBHUB_SYSTEM_PROMPT", "prompt")

    config = load_config(env_path=None)

    assert config.matrix.homeserver == "https://matrix.example.com"
    assert config.matrix.rooms == ["!room:matrix.example.com"]
    assert config.data.filepath == (tmp_path / "db" / "subscriptions.json").resolve()
    assert config.data.dismissed_filepath == (tmp_path / "db" / "dismissed.json").resolve()
    assert config.download.root == (tmp_path / "downloads").resolve()
    assert config.download.images is True
    assert config.download.videos is False
    assert config.reminder.use_llm is False


def test_load_config_absolute_dismissed_path(tmp_path, monkeypatch):
    dismissed = tmp_path / "state" / "dismissed-state.json"
    monkeypatch.setenv("MATRIX_HOMESERVER", "https://matrix.example.com")
    monkeypatch.setenv("MATRIX_USER", "@subhub:matrix.example.com")
    monkeypatch.setenv("MATRIX_PASSWORD", "secret")
    monkeypatch.setenv("MATRIX_ROOMS", "!room:matrix.example.com")
    monkeypatch.setenv("SUBHUB_LLM_BASE_URL", "https://llm.example.com/v1")
    monkeypatch.setenv("SUBHUB_LLM_API_KEY", "key")
    monkeypatch.setenv("SUBHUB_LLM_MODEL", "qwen-plus")
    monkeypatch.setenv("SUBHUB_SYSTEM_PROMPT", "prompt")
    monkeypatch.setenv("SUBHUB_DB_DIR", str(tmp_path / "db"))
    monkeypatch.setenv("SUBHUB_DISMISSED_FILENAME", str(dismissed))

    config = load_config(env_path=None)

    assert config.data.dismissed_filepath == dismissed.resolve()
```

- [ ] **Step 2: Run config tests to verify failure**

Run:

```bash
uv run pytest tests/test_config.py -v
```

Expected: FAIL because `config.py` still loads TOML and old dataclasses.

- [ ] **Step 3: Rewrite `src/subhub/config.py`**

Replace `src/subhub/config.py` with `.env` dataclasses and helpers. Include:

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _float_env(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _path_from_env(value: str, base: Path | None = None) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute() and base is not None:
        path = base / path
    return path.resolve()


@dataclass(frozen=True)
class MatrixConfig:
    homeserver: str
    user: str
    password: str
    rooms: list[str]


@dataclass(frozen=True)
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    system_prompt: str
    temperature: float
    max_history: int
    vision_enabled: bool
    skills_dir: Path | None


@dataclass(frozen=True)
class DataConfig:
    db_dir: Path
    filename: str
    dismissed_filename: str

    @property
    def filepath(self) -> Path:
        return (self.db_dir / self.filename).resolve()

    @property
    def dismissed_filepath(self) -> Path:
        raw = Path(self.dismissed_filename).expanduser()
        if raw.is_absolute():
            return raw.resolve()
        return (self.db_dir / raw).resolve()


@dataclass(frozen=True)
class ReminderConfig:
    enabled: bool
    advance_days: int
    check_interval_hours: int
    use_llm: bool


@dataclass(frozen=True)
class ReportConfig:
    base_currency: str


@dataclass(frozen=True)
class R2Config:
    endpoint: str
    access_key: str
    secret_key: str
    bucket: str
    public_url: str

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint and self.access_key and self.secret_key)


@dataclass(frozen=True)
class DownloadConfig:
    root: Path
    images: bool
    videos: bool
    audios: bool
    files: bool


@dataclass(frozen=True)
class AppConfig:
    matrix: MatrixConfig
    llm: LLMConfig
    data: DataConfig
    reminder: ReminderConfig
    report: ReportConfig
    r2: R2Config
    download: DownloadConfig
    log_level: str


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def load_config(env_path: str | Path | None = ".env") -> AppConfig:
    if env_path:
        env_file = Path(env_path)
        if env_file.exists():
            load_dotenv(env_file)
    else:
        load_dotenv()

    cwd = Path.cwd()
    db_dir = _path_from_env(os.environ.get("SUBHUB_DB_DIR", "db"), cwd)
    download_root = _path_from_env(os.environ.get("SUBHUB_DOWNLOAD_DIR", "downloads"), cwd)
    skills_raw = os.environ.get("SUBHUB_SKILLS_DIR", "").strip()
    skills_dir = _path_from_env(skills_raw, cwd) if skills_raw else None

    return AppConfig(
        matrix=MatrixConfig(
            homeserver=_require("MATRIX_HOMESERVER"),
            user=_require("MATRIX_USER"),
            password=_require("MATRIX_PASSWORD"),
            rooms=_split_csv(_require("MATRIX_ROOMS")),
        ),
        llm=LLMConfig(
            base_url=_require("SUBHUB_LLM_BASE_URL"),
            api_key=_require("SUBHUB_LLM_API_KEY"),
            model=_require("SUBHUB_LLM_MODEL"),
            system_prompt=_require("SUBHUB_SYSTEM_PROMPT"),
            temperature=_float_env("SUBHUB_LLM_TEMPERATURE", 0.7),
            max_history=_int_env("SUBHUB_LLM_MAX_HISTORY", 20),
            vision_enabled=_bool_env("SUBHUB_LLM_VISION_ENABLED", False),
            skills_dir=skills_dir,
        ),
        data=DataConfig(
            db_dir=db_dir,
            filename=os.environ.get("SUBHUB_DB_FILENAME", "subscriptions.json"),
            dismissed_filename=os.environ.get("SUBHUB_DISMISSED_FILENAME", "dismissed.json"),
        ),
        reminder=ReminderConfig(
            enabled=_bool_env("SUBHUB_REMINDER_ENABLED", True),
            advance_days=_int_env("SUBHUB_REMINDER_ADVANCE_DAYS", 3),
            check_interval_hours=_int_env("SUBHUB_REMINDER_CHECK_INTERVAL_HOURS", 1),
            use_llm=_bool_env("SUBHUB_REMINDER_USE_LLM", False),
        ),
        report=ReportConfig(
            base_currency=os.environ.get("SUBHUB_REPORT_BASE_CURRENCY", "CNY"),
        ),
        r2=R2Config(
            endpoint=os.environ.get("R2_ENDPOINT", ""),
            access_key=os.environ.get("R2_ACCESS_KEY", ""),
            secret_key=os.environ.get("R2_SECRET_KEY", ""),
            bucket=os.environ.get("R2_BUCKET", "link-media"),
            public_url=os.environ.get("R2_PUBLIC_URL", ""),
        ),
        download=DownloadConfig(
            root=download_root,
            images=_bool_env("SUBHUB_DOWNLOAD_R2_IMAGES", True),
            videos=_bool_env("SUBHUB_DOWNLOAD_R2_VIDEOS", False),
            audios=_bool_env("SUBHUB_DOWNLOAD_R2_AUDIOS", False),
            files=_bool_env("SUBHUB_DOWNLOAD_R2_FILES", False),
        ),
        log_level=os.environ.get("SUBHUB_LOG_LEVEL", "INFO").upper(),
    )
```

- [ ] **Step 4: Add explicit dismissed path support to store**

Change `SubscriptionStore.__init__` signature:

```python
def __init__(self, filepath: Path, dismissed_filepath: Path | None = None):
    self._filepath = Path(filepath)
    self._subscriptions: list[Subscription] = []
    self._lock = threading.RLock()
    self._dismissed_filepath = (
        Path(dismissed_filepath)
        if dismissed_filepath is not None
        else self._filepath.parent / "dismissed.json"
    )
    self._load()
```

- [ ] **Step 5: Add store test for dismissed filepath**

Append to `tests/test_store.py`:

```python
def test_dismissed_filepath_can_be_configured(tmp_path):
    dismissed_path = tmp_path / "state" / "ignored.json"
    store = SubscriptionStore(tmp_path / "subs.json", dismissed_filepath=dismissed_path)
    sub = store.add(name="测试", account="a", payment_channel="b",
                    amount=10.0, currency="CNY", billing_cycle="monthly",
                    next_billing_date="2026-05-01", notes="")
    store.dismiss_reminder(sub.id, date(2026, 4, 8))

    assert dismissed_path.exists()
```

- [ ] **Step 6: Run tests**

Run:

```bash
uv run pytest tests/test_config.py tests/test_store.py -v
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add src/subhub/config.py src/subhub/store.py tests/test_config.py tests/test_store.py
git commit -m "feat: load bot runtime config from env"
```

---

### Task 3: Local SubHub Tools

**Files:**
- Create: `src/subhub/tools.py`
- Create: `tests/test_tools.py`

- [ ] **Step 1: Write local tool tests**

Create `tests/test_tools.py` with tests for definitions and execution:

```python
import json

import pytest

from subhub.service import SubHubService
from subhub.store import SubscriptionStore
from subhub.tools import SubHubToolRegistry, build_subhub_tools


@pytest.fixture
def registry(tmp_path):
    store = SubscriptionStore(tmp_path / "subs.json", dismissed_filepath=tmp_path / "dismissed.json")
    service = SubHubService(store=store, base_currency="CNY", reminder_advance_days=3)
    return SubHubToolRegistry(build_subhub_tools(service))


def test_tool_definitions_are_openai_compatible(registry):
    definitions = registry.get_all_definitions()
    names = {item["function"]["name"] for item in definitions}
    assert "create_subscription" in names
    assert "list_subscriptions" in names
    assert all(item["type"] == "function" for item in definitions)


@pytest.mark.asyncio
async def test_create_and_list_subscription(registry):
    created = await registry.execute_tool(
        "create_subscription",
        name="YouTube Premium",
        account="me@example.com",
        payment_channel="Visa",
        amount=28,
        currency="CNY",
        billing_cycle="monthly",
        next_billing_date="2026-05-01",
        notes="家庭组",
    )
    created_data = json.loads(created)
    assert created_data["ok"] is True
    assert created_data["data"]["item"]["name"] == "YouTube Premium"

    listed = json.loads(await registry.execute_tool("list_subscriptions"))
    assert listed["ok"] is True
    assert listed["data"]["total"] == 1


@pytest.mark.asyncio
async def test_unknown_tool_returns_json_error(registry):
    result = json.loads(await registry.execute_tool("missing_tool"))
    assert result["ok"] is False
    assert result["error"]["code"] == "TOOL_NOT_FOUND"
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_tools.py -v
```

Expected: FAIL because `subhub.tools` does not exist.

- [ ] **Step 3: Implement `src/subhub/tools.py`**

Implement:

```python
from __future__ import annotations

import inspect
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from subhub.service import SubHubService


ToolHandler = Callable[..., dict[str, Any] | Awaitable[dict[str, Any]]]


def _json_ok(data: Any) -> str:
    return json.dumps({"ok": True, "data": data}, ensure_ascii=False)


def _json_error(code: str, message: str) -> str:
    return json.dumps({"ok": False, "error": {"code": code, "message": message}}, ensure_ascii=False)


@dataclass(frozen=True)
class LocalTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler

    @property
    def definition(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def execute(self, **params: Any) -> str:
        try:
            result = self.handler(**params)
            if inspect.isawaitable(result):
                result = await result
            return _json_ok(result)
        except ValueError as exc:
            return _json_error("INVALID_ARGUMENT", str(exc))
        except Exception as exc:
            return _json_error("TOOL_ERROR", str(exc))


class SubHubToolRegistry:
    def __init__(self, tools: list[LocalTool]):
        self._tools = {tool.name: tool for tool in tools}

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools)

    def has_tools(self) -> bool:
        return bool(self._tools)

    def get_all_definitions(self) -> list[dict[str, Any]]:
        return [tool.definition for tool in self._tools.values()]

    async def execute_tool(self, tool_name: str, **params: Any) -> str:
        tool = self._tools.get(tool_name)
        if tool is None:
            return _json_error("TOOL_NOT_FOUND", f"未找到工具: {tool_name}")
        return await tool.execute(**params)


def _object_schema(properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": properties, "required": required or []}


def build_subhub_tools(service: SubHubService) -> list[LocalTool]:
    cycles = ["monthly", "quarterly", "semiannual", "yearly", "weekly", "daily", "permanent", "custom"]
    currencies = ["CNY", "USD", "EUR", "GBP", "JPY"]

    def create_subscription(**payload: Any) -> dict[str, Any]:
        return service.add_subscription(payload)

    def update_subscription(id: str | None = None, selector_name: str | None = None, **payload: Any) -> dict[str, Any]:
        result = service.update_subscription_by_selector(
            subscription_id=id,
            selector_name=selector_name,
            payload=payload,
        )
        if result is None:
            raise ValueError("未找到该订阅")
        return result

    def delete_subscription(id: str | None = None, name: str | None = None) -> dict[str, Any]:
        result = service.delete_subscription_by_selector(subscription_id=id, name=name)
        if result is None:
            raise ValueError("未找到匹配的订阅记录")
        return result

    return [
        LocalTool("get_today_context", "获取当前日期上下文。", _object_schema({}), lambda: service.get_context_today()),
        LocalTool("get_subscriptions_context", "获取当前订阅列表上下文。", _object_schema({}), lambda: service.get_context_subscriptions()),
        LocalTool("get_accounts_context", "获取常用登录账号上下文。", _object_schema({}), lambda: service.get_context_accounts()),
        LocalTool("get_channels_context", "获取常用支付渠道上下文。", _object_schema({}), lambda: service.get_context_channels()),
        LocalTool(
            "list_subscriptions",
            "查询订阅列表，可按名称或计费周期过滤。",
            _object_schema({
                "name": {"type": "string", "description": "服务名称关键词"},
                "billing_cycle": {"type": "string", "enum": cycles},
            }),
            lambda name=None, billing_cycle=None: service.list_subscriptions(name=name, billing_cycle=billing_cycle),
        ),
        LocalTool(
            "create_subscription",
            "新增订阅。只能在信息完整且用户确认后调用。",
            _object_schema({
                "name": {"type": "string"},
                "account": {"type": "string"},
                "payment_channel": {"type": "string"},
                "amount": {"type": "number"},
                "currency": {"type": "string", "enum": currencies},
                "billing_cycle": {"type": "string", "enum": cycles},
                "next_billing_date": {"type": "string"},
                "notes": {"type": "string"},
            }, ["name", "account", "payment_channel", "amount", "currency", "billing_cycle", "next_billing_date"]),
            create_subscription,
        ),
        LocalTool(
            "update_subscription",
            "更新订阅。优先传 id；如果只有名称，传 selector_name。",
            _object_schema({
                "id": {"type": "string"},
                "selector_name": {"type": "string"},
                "name": {"type": "string"},
                "account": {"type": "string"},
                "payment_channel": {"type": "string"},
                "amount": {"type": "number"},
                "currency": {"type": "string", "enum": currencies},
                "billing_cycle": {"type": "string", "enum": cycles},
                "next_billing_date": {"type": "string"},
                "notes": {"type": "string"},
            }),
            update_subscription,
        ),
        LocalTool(
            "delete_subscription",
            "删除订阅。删除前必须确认。",
            _object_schema({"id": {"type": "string"}, "name": {"type": "string"}}),
            delete_subscription,
        ),
        LocalTool(
            "generate_monthly_report",
            "生成月报。mode=budget 为预算折算，mode=actual 为实际扣款。",
            _object_schema({
                "month": {"type": "string"},
                "mode": {"type": "string", "enum": ["budget", "actual"], "default": "budget"},
            }),
            lambda month=None, mode="budget": service.get_monthly_report(month=month, mode=mode),
        ),
        LocalTool(
            "dismiss_reminder",
            "关闭提醒。target 可为订阅 id、订阅名称或 all。",
            _object_schema({"target": {"type": "string"}}, ["target"]),
            lambda target: service.dismiss_reminder(target),
        ),
    ]
```

- [ ] **Step 4: Run tests**

Run:

```bash
uv run pytest tests/test_tools.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/subhub/tools.py tests/test_tools.py
git commit -m "feat: add local subhub function tools"
```

---

### Task 4: R2 Protocol and Attachment Resolver

**Files:**
- Create: `src/subhub/r2_protocol.py`
- Create: `src/subhub/media_store.py`
- Create: `src/subhub/attachments.py`
- Create: `tests/test_r2_protocol.py`
- Create: `tests/test_attachments.py`

- [ ] **Step 1: Copy and adapt R2 protocol tests**

Create `tests/test_r2_protocol.py`:

```python
from subhub import r2_protocol


def test_iter_r2_markdown_links_supports_images_and_files():
    body = "看图 ![receipt](r2://bucket/room/imgs/a.png) 和 [file](r2://bucket/room/files/a.pdf)"
    links = list(r2_protocol.iter_r2_markdown_links(body))
    assert [link.group("alt") for link in links] == ["receipt", "file"]
    assert links[0].group("uri") == "r2://bucket/room/imgs/a.png"


def test_media_kind_from_object_key_prefers_directory():
    assert r2_protocol.infer_media_kind_from_object_key("room/imgs/a.bin") == "image"
    assert r2_protocol.infer_media_kind_from_object_key("room/videos/a.mp4") == "video"
    assert r2_protocol.local_cache_relative_path("room/imgs/a.png") == "imgs/a.png"
```

- [ ] **Step 2: Write attachment resolver tests**

Create `tests/test_attachments.py`:

```python
from pathlib import Path

import pytest

from subhub.attachments import AttachmentResolver
from subhub.config import DownloadConfig, R2Config


class FakeStore:
    def __init__(self, paths):
        self.paths = paths
        self.downloaded = []

    async def download(self, r2_uri: str, kind: str) -> Path | None:
        self.downloaded.append((r2_uri, kind))
        return self.paths.get(r2_uri)


@pytest.mark.asyncio
async def test_downloads_image_when_enabled(tmp_path):
    local = tmp_path / "downloads" / "imgs" / "a.png"
    local.parent.mkdir(parents=True)
    local.write_bytes(b"png")
    store = FakeStore({"r2://bucket/room/imgs/a.png": local})
    resolver = AttachmentResolver(
        download=DownloadConfig(root=tmp_path / "downloads", images=True, videos=False, audios=False, files=False),
        media_store=store,
        vision_enabled=True,
    )

    resolved = await resolver.resolve("看图 ![a](r2://bucket/room/imgs/a.png)")

    assert "[image:" in resolved.content
    assert resolved.image_paths == [local]
    assert store.downloaded == [("r2://bucket/room/imgs/a.png", "image")]


@pytest.mark.asyncio
async def test_does_not_download_video_by_default(tmp_path):
    store = FakeStore({})
    resolver = AttachmentResolver(
        download=DownloadConfig(root=tmp_path / "downloads", images=True, videos=False, audios=False, files=False),
        media_store=store,
        vision_enabled=True,
    )

    resolved = await resolver.resolve("视频 ![v](r2://bucket/room/videos/a.mp4)")

    assert "用户附件:video" in resolved.content
    assert store.downloaded == []
```

- [ ] **Step 3: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_r2_protocol.py tests/test_attachments.py -v
```

Expected: FAIL because modules do not exist.

- [ ] **Step 4: Implement `src/subhub/r2_protocol.py`**

Copy the protocol helpers from `/home/txl/Code/meswarm/link/link/r2_protocol.py` and keep only:

```python
validate_r2_prefix
attachment_dir_from_mime
sanitize_filename
build_object_key
parse_r2_uri
strip_r2_query
local_cache_relative_path
infer_media_kind_from_object_key
guess_mime_from_object_key
media_kind_from_mime
outbound_markdown_for_r2
iter_r2_markdown_links
```

Keep behavior identical to Link's implementation.

- [ ] **Step 5: Implement `src/subhub/media_store.py`**

Implement R2 downloads with `aioboto3`. The public method used by attachments must be:

```python
async def download(self, r2_uri: str, kind: str) -> Path | None:
    ...
```

It should save under `download.root / directory / filename`, where directory is `imgs`, `videos`, `audios`, or `files`.

- [ ] **Step 6: Implement `src/subhub/attachments.py`**

Implement:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from subhub import r2_protocol
from subhub.config import DownloadConfig


@dataclass
class ResolvedMessage:
    content: str
    image_paths: list[Path] = field(default_factory=list)


class AttachmentResolver:
    def __init__(self, download: DownloadConfig, media_store, vision_enabled: bool):
        self._download = download
        self._media_store = media_store
        self._vision_enabled = vision_enabled

    async def resolve(self, content: str) -> ResolvedMessage:
        result = content
        images: list[Path] = []
        for match in list(r2_protocol.iter_r2_markdown_links(content)):
            original = match.group(0)
            alt = match.group("alt")
            clean_uri = r2_protocol.strip_r2_query(match.group("uri"))
            parsed = r2_protocol.parse_r2_uri(clean_uri)
            if not parsed:
                continue
            _bucket, key = parsed
            kind = r2_protocol.infer_media_kind_from_object_key(key)
            mime = r2_protocol.guess_mime_from_object_key(key)
            should_download = {
                "image": self._download.images,
                "video": self._download.videos,
                "audio": self._download.audios,
                "file": self._download.files,
            }[kind]

            local_path = None
            if should_download and self._media_store is not None:
                local_path = await self._media_store.download(clean_uri, kind)

            if kind == "image" and local_path and self._vision_enabled:
                replacement = f"[image:{local_path}:{mime}] {alt}".strip()
                images.append(local_path)
            elif local_path:
                replacement = f"[用户附件:{kind} 名称:{alt or key} 本地路径:{local_path} 类型:{mime}]"
            else:
                replacement = f"[用户附件:{kind} 名称:{alt or key} 类型:{mime} 未下载]"

            result = result.replace(original, replacement)
        return ResolvedMessage(content=result, image_paths=images)
```

- [ ] **Step 7: Run tests**

Run:

```bash
uv run pytest tests/test_r2_protocol.py tests/test_attachments.py -v
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add src/subhub/r2_protocol.py src/subhub/media_store.py src/subhub/attachments.py tests/test_r2_protocol.py tests/test_attachments.py
git commit -m "feat: resolve r2 markdown attachments"
```

---

### Task 5: Skills and LLM Engine

**Files:**
- Create: `src/subhub/skills.py`
- Create: `src/subhub/llm_engine.py`
- Create: `tests/test_llm_engine.py`

- [ ] **Step 1: Write LLM engine tests with fake client**

Create `tests/test_llm_engine.py`:

```python
import json
from types import SimpleNamespace

import pytest

from subhub.llm_engine import LLMEngine


class FakeRegistry:
    def __init__(self):
        self.calls = []

    def has_tools(self):
        return True

    def get_all_definitions(self):
        return [{
            "type": "function",
            "function": {
                "name": "list_subscriptions",
                "description": "list",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }]

    async def execute_tool(self, name, **params):
        self.calls.append((name, params))
        return json.dumps({"ok": True, "data": {"items": []}}, ensure_ascii=False)


class FakeCompletions:
    def __init__(self):
        self.count = 0

    async def create(self, **kwargs):
        self.count += 1
        if self.count == 1:
            tool_call = SimpleNamespace(
                id="call_1",
                function=SimpleNamespace(name="list_subscriptions", arguments="{}"),
            )
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="", tool_calls=[tool_call]))])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="暂无订阅", tool_calls=None))])


class FakeClient:
    def __init__(self):
        self.chat = SimpleNamespace(completions=FakeCompletions())


@pytest.mark.asyncio
async def test_llm_engine_executes_tool_calls():
    registry = FakeRegistry()
    engine = LLMEngine(
        client=FakeClient(),
        model="test-model",
        system_prompt="prompt {today_context}",
        tool_registry=registry,
        context_hooks={"today_context": lambda: "2026-04-26"},
        temperature=0.7,
        max_history=20,
        vision_enabled=False,
    )

    reply = await engine.chat("room", "列出订阅")

    assert reply == "暂无订阅"
    assert registry.calls == [("list_subscriptions", {})]
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
uv run pytest tests/test_llm_engine.py -v
```

Expected: FAIL because `llm_engine.py` does not exist.

- [ ] **Step 3: Implement `src/subhub/skills.py`**

Implement a small loader:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Skill:
    name: str
    content: str


def load_skills_from_dir(skills_dir: Path | None) -> list[Skill]:
    if skills_dir is None or not skills_dir.exists():
        return []
    roots = [skills_dir] if (skills_dir / "SKILL.md").exists() else [p for p in skills_dir.iterdir() if p.is_dir()]
    skills: list[Skill] = []
    for root in roots:
        path = root / "SKILL.md"
        if path.exists():
            skills.append(Skill(name=root.name, content=path.read_text(encoding="utf-8")))
    return skills


def format_skills_for_prompt(skills: list[Skill]) -> str:
    if not skills:
        return ""
    sections = ["## Skills"]
    for skill in skills:
        sections.append(f"### {skill.name}\n{skill.content}")
    return "\n\n".join(sections)
```

- [ ] **Step 4: Implement `src/subhub/llm_engine.py`**

Implement the slim engine from the spec:

```python
from __future__ import annotations

import base64
import json
import logging
import re
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)
MAX_TOOL_CALL_ROUNDS = 10
_IMAGE_TAG_PATTERN = re.compile(r"\[image:(.+?):(.+?)\]")


class LLMEngine:
    def __init__(
        self,
        client,
        model: str,
        system_prompt: str,
        tool_registry,
        context_hooks: dict[str, Callable[[], str]] | None = None,
        skills_prompt: str = "",
        temperature: float = 0.7,
        max_history: int = 20,
        vision_enabled: bool = False,
    ):
        self._client = client
        self._model = model
        self._system_prompt = system_prompt
        self._tool_registry = tool_registry
        self._context_hooks = context_hooks or {}
        self._skills_prompt = skills_prompt
        self._temperature = temperature
        self._max_history = max_history
        self._vision_enabled = vision_enabled
        self._histories: dict[str, list[dict[str, Any]]] = {}

    def _history(self, room_id: str) -> list[dict[str, Any]]:
        return self._histories.setdefault(room_id, [])

    def _trim(self, room_id: str) -> None:
        max_len = self._max_history * 2
        if len(self._history(room_id)) > max_len:
            self._histories[room_id] = self._history(room_id)[-max_len:]

    def _context(self) -> dict[str, str]:
        return {name: hook() for name, hook in self._context_hooks.items()}

    def _messages(self, room_id: str) -> list[dict[str, Any]]:
        prompt = self._system_prompt
        context = self._context()
        if context:
            prompt = prompt.format(**context)
        if self._skills_prompt:
            prompt = f"{prompt}\n\n{self._skills_prompt}"
        return [{"role": "system", "content": prompt}, *self._history(room_id)]

    def _user_content(self, message: str) -> str | list[dict[str, Any]]:
        matches = _IMAGE_TAG_PATTERN.findall(message)
        if not matches or not self._vision_enabled:
            if matches:
                for file_path, mime in matches:
                    message = message.replace(f"[image:{file_path}:{mime}]", f"[用户发送了一张图片: {Path(file_path).name}]")
            return message
        parts: list[dict[str, Any]] = []
        text = _IMAGE_TAG_PATTERN.sub("", message).strip() or "请分析这张图片"
        for file_path, mime in matches:
            data = base64.b64encode(Path(file_path).read_bytes()).decode("utf-8")
            parts.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}})
        parts.append({"type": "text", "text": text})
        return parts

    async def chat(self, room_id: str, user_message: str) -> str:
        history = self._history(room_id)
        history.append({"role": "user", "content": self._user_content(user_message)})
        messages = self._messages(room_id)
        tools = self._tool_registry.get_all_definitions() if self._tool_registry.has_tools() else None

        for _round in range(MAX_TOOL_CALL_ROUNDS):
            kwargs = {"model": self._model, "messages": messages, "temperature": self._temperature}
            if tools:
                kwargs["tools"] = tools
            completion = await self._client.chat.completions.create(**kwargs)
            assistant_message = completion.choices[0].message
            if not assistant_message.tool_calls:
                content = assistant_message.content or ""
                history.append({"role": "assistant", "content": content})
                self._trim(room_id)
                return content
            messages.append({
                "role": "assistant",
                "content": assistant_message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in assistant_message.tool_calls
                ],
            })
            for call in assistant_message.tool_calls:
                try:
                    args = json.loads(call.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = await self._tool_registry.execute_tool(call.function.name, **args)
                messages.append({"role": "tool", "tool_call_id": call.id, "content": result})

        content = "抱歉，操作步骤过多，我需要简化处理方式。请重新描述你的需求。"
        history.append({"role": "assistant", "content": content})
        self._trim(room_id)
        return content
```

- [ ] **Step 5: Run tests**

Run:

```bash
uv run pytest tests/test_llm_engine.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/subhub/skills.py src/subhub/llm_engine.py tests/test_llm_engine.py
git commit -m "feat: add embedded llm function engine"
```

---

### Task 6: Matrix Text Client

**Files:**
- Create: `src/subhub/matrix_client.py`
- Create: `tests/test_matrix_client.py`

- [ ] **Step 1: Write Matrix client tests**

Create `tests/test_matrix_client.py`:

```python
def test_matrix_client_declares_text_only_events():
    from subhub.matrix_client import MatrixTextClient

    assert MatrixTextClient.event_types() == ("RoomMessageText",)
```

- [ ] **Step 2: Implement `src/subhub/matrix_client.py`**

Implement a wrapper around `nio.AsyncClient` that registers only `RoomMessageText`:

```python
from __future__ import annotations

import logging
from typing import Awaitable, Callable

from nio import AsyncClient, LoginResponse, RoomMessageText

logger = logging.getLogger(__name__)
MessageCallback = Callable[[str, str, str], Awaitable[None]]


class MatrixTextClient:
    def __init__(self, homeserver: str, user: str, password: str, rooms: list[str], client: AsyncClient | None = None):
        self._client = client or AsyncClient(homeserver, user)
        self._homeserver = homeserver
        self._user = user
        self._password = password
        self._rooms = rooms
        self._callback: MessageCallback | None = None
        self._first_sync_done = False
        self._should_stop = False

    @staticmethod
    def event_types() -> tuple[str, ...]:
        return ("RoomMessageText",)

    def on_message(self, callback: MessageCallback) -> None:
        self._callback = callback

    async def login(self) -> bool:
        response = await self._client.login(self._password)
        if isinstance(response, LoginResponse):
            logger.info("Matrix login succeeded for %s", self._user)
            return True
        logger.error("Matrix login failed for %s: %s", self._user, response)
        await self._client.close()
        return False

    async def _join_rooms(self) -> None:
        for room_id in self._rooms:
            await self._client.join(room_id)

    async def _on_room_message(self, room, event) -> None:
        if event.sender == self._client.user_id:
            return
        if not self._first_sync_done:
            return
        if self._callback:
            await self._callback(room.room_id, event.sender, event.body)

    async def send_text(self, room_id: str, text: str) -> None:
        await self._client.room_send(
            room_id=room_id,
            message_type="m.room.message",
            content={"msgtype": "m.text", "body": text},
        )

    async def set_typing(self, room_id: str, typing: bool, timeout: int = 30000) -> None:
        try:
            await self._client.room_typing(room_id, typing, timeout=timeout)
        except Exception:
            logger.debug("Matrix typing update failed", exc_info=True)

    async def start_sync(self) -> None:
        self._client.add_event_callback(self._on_room_message, RoomMessageText)
        await self._join_rooms()
        await self._client.sync(timeout=10000)
        self._first_sync_done = True
        while not self._should_stop:
            await self._client.sync(timeout=5000)

    async def stop(self) -> None:
        self._should_stop = True
        await self._client.close()

    @property
    def rooms(self) -> list[str]:
        return self._rooms
```

- [ ] **Step 3: Run tests**

Run:

```bash
uv run pytest tests/test_matrix_client.py -v
```

Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add src/subhub/matrix_client.py tests/test_matrix_client.py
git commit -m "feat: add matrix text client"
```

---

### Task 7: Reminder Task and Bot Orchestrator

**Files:**
- Create: `src/subhub/reminder_task.py`
- Create: `src/subhub/bot.py`
- Create: `tests/test_reminder_task.py`

- [ ] **Step 1: Write reminder task tests**

Create `tests/test_reminder_task.py`:

```python
from datetime import date

import pytest

from subhub.reminder_task import format_reminder_with_optional_llm


class FakeEngine:
    async def format_notification(self, payload):
        return f"LLM: {payload['message']}"


@pytest.mark.asyncio
async def test_direct_reminder_formatting():
    text = await format_reminder_with_optional_llm("hello", use_llm=False, llm_engine=None)
    assert text == "hello"


@pytest.mark.asyncio
async def test_llm_reminder_formatting():
    text = await format_reminder_with_optional_llm("hello", use_llm=True, llm_engine=FakeEngine())
    assert text == "LLM: hello"
```

- [ ] **Step 2: Implement `src/subhub/reminder_task.py`**

Implement:

```python
from __future__ import annotations

import asyncio
import logging
from datetime import date

from subhub.reminder import check_reminders

logger = logging.getLogger(__name__)


async def format_reminder_with_optional_llm(message: str, use_llm: bool, llm_engine) -> str:
    if use_llm and llm_engine is not None:
        return await llm_engine.format_notification({"message": message})
    return message


async def reminder_loop(config, store, matrix_client, llm_engine=None) -> None:
    interval = max(config.reminder.check_interval_hours, 1) * 3600
    while True:
        try:
            message = check_reminders(store, date.today(), config.reminder.advance_days)
            if message:
                text = await format_reminder_with_optional_llm(
                    message,
                    use_llm=config.reminder.use_llm,
                    llm_engine=llm_engine,
                )
                for room_id in matrix_client.rooms:
                    await matrix_client.send_text(room_id, text)
                logger.info("Sent subscription reminder to %s rooms", len(matrix_client.rooms))
        except Exception:
            logger.exception("Reminder loop failed")
        await asyncio.sleep(interval)
```

- [ ] **Step 3: Implement `src/subhub/bot.py`**

Implement orchestration:

```python
from __future__ import annotations

import asyncio
import logging

from openai import AsyncOpenAI

from subhub.attachments import AttachmentResolver
from subhub.llm_engine import LLMEngine
from subhub.media_store import R2MediaStore
from subhub.reminder_task import reminder_loop
from subhub.service import SubHubService
from subhub.skills import format_skills_for_prompt, load_skills_from_dir
from subhub.store import SubscriptionStore
from subhub.tools import SubHubToolRegistry, build_subhub_tools

logger = logging.getLogger(__name__)


class SubHubBot:
    def __init__(self, config, matrix_client):
        self._config = config
        self._matrix = matrix_client
        self._store = SubscriptionStore(config.data.filepath, dismissed_filepath=config.data.dismissed_filepath)
        self._service = SubHubService(self._store, base_currency=config.report.base_currency, reminder_advance_days=config.reminder.advance_days)
        self._tools = SubHubToolRegistry(build_subhub_tools(self._service))
        skills = load_skills_from_dir(config.llm.skills_dir)
        media_store = R2MediaStore(config.r2, config.download.root) if config.r2.enabled else None
        self._attachments = AttachmentResolver(config.download, media_store, config.llm.vision_enabled)
        client = AsyncOpenAI(api_key=config.llm.api_key, base_url=config.llm.base_url)
        self._llm = LLMEngine(
            client=client,
            model=config.llm.model,
            system_prompt=config.llm.system_prompt,
            tool_registry=self._tools,
            context_hooks={
                "today_context": lambda: self._service.get_context_today()["today"],
                "subscriptions_context": lambda: self._service.get_context_subscriptions()["markdown"],
                "accounts_context": lambda: self._service.get_context_accounts()["text"],
                "channels_context": lambda: self._service.get_context_channels()["text"],
            },
            skills_prompt=format_skills_for_prompt(skills),
            temperature=config.llm.temperature,
            max_history=config.llm.max_history,
            vision_enabled=config.llm.vision_enabled,
        )
        self._matrix.on_message(self._handle_message)

    async def _handle_message(self, room_id: str, sender: str, content: str) -> None:
        logger.info("Handling Matrix message from %s in %s", sender, room_id)
        await self._matrix.set_typing(room_id, True)
        try:
            resolved = await self._attachments.resolve(content)
            reply = await self._llm.chat(room_id, resolved.content)
            if reply.strip():
                await self._matrix.send_text(room_id, reply)
        except Exception:
            logger.exception("Message handling failed")
            await self._matrix.send_text(room_id, "抱歉，处理你的消息时出现了问题。")
        finally:
            await self._matrix.set_typing(room_id, False)

    async def start(self) -> None:
        if not await self._matrix.login():
            raise RuntimeError("Matrix 登录失败")
        tasks = []
        if self._config.reminder.enabled:
            tasks.append(asyncio.create_task(reminder_loop(self._config, self._store, self._matrix, self._llm)))
        await self._matrix.start_sync()
        for task in tasks:
            task.cancel()

    async def stop(self) -> None:
        await self._matrix.stop()
```

- [ ] **Step 4: Add `format_notification` to LLM engine**

Add method to `LLMEngine`:

```python
async def format_notification(self, payload: dict[str, Any]) -> str:
    prompt = json.dumps(payload, ensure_ascii=False, indent=2)
    completion = await self._client.chat.completions.create(
        model=self._model,
        messages=[
            {"role": "system", "content": "你是一个通知整理助手。输出简洁中文，不要代码块。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
    )
    return completion.choices[0].message.content or payload.get("message", "")
```

- [ ] **Step 5: Run tests**

Run:

```bash
uv run pytest tests/test_reminder.py tests/test_reminder_task.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add src/subhub/reminder_task.py src/subhub/bot.py src/subhub/llm_engine.py tests/test_reminder_task.py
git commit -m "feat: orchestrate bot and reminders"
```

---

### Task 8: Main Entry Point and API Removal

**Files:**
- Modify: `src/subhub/main.py`
- Modify: `pyproject.toml`
- Modify: `Makefile`
- Delete: `config.toml`
- Delete: `src/subhub/api.py`
- Delete: `src/subhub/webhook.py`
- Delete: `tests/test_api.py`
- Delete: `tests/test_webhook.py`

- [ ] **Step 1: Remove legacy API dependencies**

After API files and tests are removed in this task, replace project dependencies in `pyproject.toml` with:

```toml
dependencies = [
    "aiofiles>=23.0.0",
    "aiohttp>=3.9.0",
    "aioboto3>=13.0.0",
    "matrix-nio>=0.24.0",
    "openai>=1.0.0",
    "python-dotenv>=1.0.0",
]
```

- [ ] **Step 2: Update Makefile help text**

Change `make run` help text from API wording to bot wording:

```make
run: ## Start the SubHub Matrix bot
	$(UV) run subhub $(ARGS)
```

- [ ] **Step 3: Rewrite `src/subhub/main.py`**

Replace with:

```python
from __future__ import annotations

import argparse
import asyncio
import logging
import signal

from subhub.bot import SubHubBot
from subhub.config import load_config
from subhub.matrix_client import MatrixTextClient


def _configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


async def _amain(env_path: str | None) -> None:
    config = load_config(env_path=env_path)
    _configure_logging(config.log_level)
    logging.info(
        "Starting SubHub bot: rooms=%s db=%s downloads=%s r2=%s reminders=%s",
        config.matrix.rooms,
        config.data.filepath,
        config.download.root,
        "enabled" if config.r2.enabled else "disabled",
        "enabled" if config.reminder.enabled else "disabled",
    )
    matrix = MatrixTextClient(
        homeserver=config.matrix.homeserver,
        user=config.matrix.user,
        password=config.matrix.password,
        rooms=config.matrix.rooms,
    )
    bot = SubHubBot(config, matrix)
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)
    task = asyncio.create_task(bot.start())
    await stop_event.wait()
    await bot.stop()
    task.cancel()


def main() -> None:
    parser = argparse.ArgumentParser(description="SubHub Matrix bot")
    parser.add_argument("--env", default=".env", help="Path to .env file")
    args = parser.parse_args()
    asyncio.run(_amain(args.env))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Delete API/webhook files, tests, and config.toml**

Run:

```bash
git rm config.toml src/subhub/api.py src/subhub/webhook.py tests/test_api.py tests/test_webhook.py
```

- [ ] **Step 5: Sync dependencies**

Run:

```bash
make sync
```

Expected: `uv sync` completes and `uv.lock` removes legacy API-only packages if no longer needed.

- [ ] **Step 6: Run full tests**

Run:

```bash
make test
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml uv.lock Makefile src/subhub/main.py
git commit -m "refactor: remove api and start matrix bot"
```

---

### Task 9: Documentation and Final Verification

**Files:**
- Modify: `README.md`
- Modify: `README_EN.md`
- Modify: `docs/service.subhub-manual.md`
- Create: `skills/manage-subscriptions/SKILL.md`
- Create: `skills/manage-subscriptions/references/domain-rules.md`
- Delete: `link/README.md`
- Delete: `link/config-template.yaml`
- Delete: `link/agents/subhub.yaml`
- Delete: `link/agents/skills/manage-subscriptions/SKILL.md`
- Delete: `link/agents/skills/manage-subscriptions/references/domain-rules.md`

- [ ] **Step 1: Update README runtime docs**

Replace API startup instructions with:

````markdown
### 本地运行

复制 `.env.example` 为 `.env`，填写 Matrix、LLM 和 R2 配置后运行：

```bash
make sync
make run
```

SubHub 会以 Matrix 机器人身份登录并监听 `MATRIX_ROOMS` 中配置的房间。
````

- [ ] **Step 2: Document storage paths**

Add:

```markdown
默认数据文件为 `./db/subscriptions.json`，提醒忽略状态为 `./db/dismissed.json`。可通过 `SUBHUB_DB_DIR`、`SUBHUB_DB_FILENAME`、`SUBHUB_DISMISSED_FILENAME` 调整。
```

- [ ] **Step 3: Document R2-only file input**

Add:

```markdown
SubHub 只接收 Matrix 文本消息。图片、视频、音频和文件通过文本中的 `r2://` Markdown 链接传递；默认只下载图片，视频、音频和普通文件不下载也不解析。
```

- [ ] **Step 4: Migrate skills out of the Link runtime folder**

Run:

```bash
mkdir -p skills/manage-subscriptions/references
cp link/agents/skills/manage-subscriptions/SKILL.md skills/manage-subscriptions/SKILL.md
cp link/agents/skills/manage-subscriptions/references/domain-rules.md skills/manage-subscriptions/references/domain-rules.md
git rm link/README.md link/config-template.yaml link/agents/subhub.yaml link/agents/skills/manage-subscriptions/SKILL.md link/agents/skills/manage-subscriptions/references/domain-rules.md
```

Expected: skill files are migrated to `skills/`, and old Link-specific runtime config files are staged for deletion.

- [ ] **Step 5: Run verification**

Run:

```bash
make test
```

Expected: PASS.

Run:

```bash
uv run subhub --help
```

Expected: command prints `SubHub Matrix bot` help and exits 0.

- [ ] **Step 6: Commit**

```bash
git add README.md README_EN.md docs/service.subhub-manual.md skills/manage-subscriptions/SKILL.md skills/manage-subscriptions/references/domain-rules.md
git commit -m "docs: document embedded matrix bot runtime"
```

---

## Self-Review Checklist

- Spec coverage:
  - API/webhook removal: Task 1, Task 8, Task 9.
  - `.env` config only: Task 2.
  - DB and dismissed paths: Task 2.
  - Local JSON tools: Task 3.
  - R2 per-type switches: Task 4.
  - Vision switch: Task 4 and Task 5.
  - Matrix text-only input: Task 6.
  - Reminder direct/LLM branches: Task 7.
  - Make/logging/docs: Task 1, Task 8, Task 9.
- Placeholder scan:
  - The plan intentionally uses exact file paths, exact commands, and concrete code snippets for the implementation surface.
- Type consistency:
  - `AppConfig.data.dismissed_filepath` is used by `SubscriptionStore`.
  - `DownloadConfig` is shared by config and attachment tests.
  - `SubHubToolRegistry` exposes the same methods expected by `LLMEngine`.
  - `MatrixTextClient.rooms` is used by `reminder_loop`.
