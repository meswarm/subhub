"""配置加载模块。从环境变量加载运行配置。"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


_DEFAULT_DB_DIR = "db"
_DEFAULT_DATA_FILENAME = "subscriptions.json"
_DEFAULT_DISMISSED_FILENAME = "dismissed.json"
_DEFAULT_DOWNLOAD_DIR = "downloads"


@dataclass
class DataConfig:
    path: str
    filename: str
    dismissed_filename: str = _DEFAULT_DISMISSED_FILENAME

    @property
    def filepath(self) -> Path:
        return Path(self.path).expanduser().resolve() / self.filename

    @property
    def dismissed_filepath(self) -> Path:
        dismissed = Path(self.dismissed_filename).expanduser()
        if dismissed.is_absolute():
            return dismissed.resolve()
        return Path(self.path).expanduser().resolve() / dismissed


@dataclass
class ReminderConfig:
    reminder_days: list[int]
    check_interval_hours: int
    enabled: bool = True
    use_llm: bool = False


@dataclass
class ReportConfig:
    base_currency: str


@dataclass
class ServerConfig:
    host: str
    port: int


@dataclass
class WebhookConfig:
    url: str = ""
    timeout_seconds: int = 5
    enabled: bool = False


@dataclass
class MatrixConfig:
    homeserver: str
    user: str
    password: str
    rooms: list[str]


@dataclass
class LLMConfig:
    base_url: str
    api_key: str
    model: str
    system_prompt: str
    temperature: float = 0.7
    max_history: int = 20
    vision_enabled: bool = False
    skills_dir: Path | None = None


_DEFAULT_SKILLS_DIR = "skills/manage-subscriptions"
_DEFAULT_SYSTEM_PROMPT_FILE = "prompts/system_prompt.md"


@dataclass
class R2Config:
    endpoint: str = ""
    access_key: str = ""
    secret_key: str = ""
    bucket: str = "link-media"
    public_url: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.endpoint and self.access_key and self.secret_key)


@dataclass
class DownloadConfig:
    root: Path
    images: bool = True
    videos: bool = False
    audios: bool = False
    files: bool = False


@dataclass
class AppConfig:
    data: DataConfig
    server: ServerConfig
    reminder: ReminderConfig
    report: ReportConfig
    webhook: WebhookConfig = None
    matrix: MatrixConfig | None = None
    llm: LLMConfig | None = None
    r2: R2Config | None = None
    download: DownloadConfig | None = None
    log_level: str = "INFO"

    def __post_init__(self):
        if self.webhook is None:
            self.webhook = WebhookConfig()
        if self.r2 is None:
            self.r2 = R2Config()
        if self.download is None:
            self.download = DownloadConfig(root=Path(_DEFAULT_DOWNLOAD_DIR).resolve())


def find_config(name: str = "config.toml") -> Path | None:
    """多级查找配置文件。优先级：
    1. $SUBHUB_CONFIG 环境变量
    2. ~/.config/subhub/config.toml
    3. 包安装目录同级（通过 __file__ 推算到项目根）
    4. 当前工作目录
    """
    # 1. 环境变量
    env_val = os.environ.get("SUBHUB_CONFIG")
    if env_val:
        p = Path(env_val)
        if p.is_file():
            return p

    # 2. XDG 标准用户配置目录
    xdg = Path("~/.config/subhub").expanduser() / name
    if xdg.is_file():
        return xdg

    # 3. 包安装目录向上查找（src/subhub/config.py → 项目根）
    pkg_root = Path(__file__).resolve().parent.parent.parent  # src/../..
    pkg_conf = pkg_root / name
    if pkg_conf.is_file():
        return pkg_conf

    # 4. 当前工作目录
    cwd = Path.cwd() / name
    if cwd.is_file():
        return cwd

    return None


def _required_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value.strip()


def _matrix_rooms() -> list[str]:
    rooms = [room.strip() for room in _required_env("MATRIX_ROOMS").split(",") if room.strip()]
    if not rooms:
        raise ValueError("Missing required environment variable: MATRIX_ROOMS")
    return rooms


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value)


def _env_int_list(name: str, default: list[int]) -> list[int]:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return list(default)
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def _resolve_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    return value


def _load_legacy_config(config_path: str | None) -> dict:
    path = _resolve_legacy_config_path(config_path)
    if path is None:
        return {}

    with open(path, "rb") as f:
        return tomllib.load(f)


def _resolve_legacy_config_path(config_path: str | None) -> Path | None:
    if config_path is None:
        path = find_config()
        if path is None:
            return None
    else:
        path = Path(config_path).expanduser()
        if not path.is_file():
            found = find_config(config_path)
            if found is None:
                raise FileNotFoundError(f"Config file not found: {config_path}")
            path = found

    return path


def _load_env(config_path: str | None, env_path: str | None) -> None:
    if env_path is not None:
        load_dotenv(env_path)
        return

    config = _resolve_legacy_config_path(config_path)
    if config is not None:
        sibling_env = config.parent / ".env"
        if sibling_env.is_file():
            load_dotenv(sibling_env)
    load_dotenv()


def _has_all_env(names: tuple[str, ...]) -> bool:
    return all(os.environ.get(name) is not None for name in names)


def _optional_matrix_config(require_bot_runtime: bool) -> MatrixConfig | None:
    names = ("MATRIX_HOMESERVER", "MATRIX_USER", "MATRIX_PASSWORD", "MATRIX_ROOMS")
    if require_bot_runtime:
        return MatrixConfig(
            homeserver=_required_env("MATRIX_HOMESERVER"),
            user=_required_env("MATRIX_USER"),
            password=_required_env("MATRIX_PASSWORD"),
            rooms=_matrix_rooms(),
        )
    if not _has_all_env(names):
        return None
    return MatrixConfig(
        homeserver=_required_env("MATRIX_HOMESERVER"),
        user=_required_env("MATRIX_USER"),
        password=_required_env("MATRIX_PASSWORD"),
        rooms=_matrix_rooms(),
    )


def _optional_llm_config(require_bot_runtime: bool) -> LLMConfig | None:
    names = (
        "SUBHUB_LLM_BASE_URL",
        "SUBHUB_LLM_API_KEY",
        "SUBHUB_LLM_MODEL",
        "SUBHUB_SYSTEM_PROMPT",
    )
    if require_bot_runtime:
        return LLMConfig(
            base_url=_required_env("SUBHUB_LLM_BASE_URL"),
            api_key=_required_env("SUBHUB_LLM_API_KEY"),
            model=_required_env("SUBHUB_LLM_MODEL"),
            system_prompt=_load_system_prompt(require_required=True),
            temperature=float(os.environ.get("SUBHUB_LLM_TEMPERATURE", "0.7")),
            max_history=_env_int("SUBHUB_LLM_MAX_HISTORY", 20),
            vision_enabled=_env_bool("SUBHUB_LLM_VISION_ENABLED", False),
            skills_dir=_optional_skills_dir(),
        )
    if not _has_all_env(names):
        return None
    return LLMConfig(
        base_url=_required_env("SUBHUB_LLM_BASE_URL"),
        api_key=_required_env("SUBHUB_LLM_API_KEY"),
        model=_required_env("SUBHUB_LLM_MODEL"),
        system_prompt=_load_system_prompt(require_required=False),
        temperature=float(os.environ.get("SUBHUB_LLM_TEMPERATURE", "0.7")),
        max_history=_env_int("SUBHUB_LLM_MAX_HISTORY", 20),
        vision_enabled=_env_bool("SUBHUB_LLM_VISION_ENABLED", False),
        skills_dir=_optional_skills_dir(),
    )


def _optional_skills_dir() -> Path | None:
    raw = os.environ.get("SUBHUB_SKILLS_DIR", _DEFAULT_SKILLS_DIR).strip()
    if not raw:
        return None
    return _resolve_path(raw)


def _load_system_prompt(require_required: bool) -> str:
    prompt_file = os.environ.get("SUBHUB_SYSTEM_PROMPT_FILE", _DEFAULT_SYSTEM_PROMPT_FILE).strip()
    if prompt_file:
        path = _resolve_path(prompt_file)
        if path.is_file():
            return path.read_text(encoding="utf-8")
    prompt = os.environ.get("SUBHUB_SYSTEM_PROMPT", "")
    if prompt.strip():
        return prompt
    if require_required:
        raise ValueError(
            "Missing required environment variable: SUBHUB_SYSTEM_PROMPT or SUBHUB_SYSTEM_PROMPT_FILE"
        )
    return prompt


def load_config(config_path: str | None = None,
                env_path: str | None = None,
                require_bot_runtime: bool = False) -> AppConfig:
    """加载 legacy config.toml、.env 和当前进程环境变量。"""
    _load_env(config_path, env_path)

    legacy = _load_legacy_config(config_path)
    legacy_data = legacy.get("data", {})
    legacy_server = legacy.get("server", {})
    legacy_reminder = legacy.get("reminder", {})
    legacy_report = legacy.get("report", {})
    legacy_webhook = legacy.get("webhook", {})

    db_dir = _env_str("SUBHUB_DB_DIR", legacy_data.get("path", _DEFAULT_DB_DIR))
    data_filename = _env_str(
        "SUBHUB_DB_FILENAME", legacy_data.get("filename", _DEFAULT_DATA_FILENAME)
    )
    dismissed_filename = _env_str(
        "SUBHUB_DISMISSED_FILENAME",
        legacy_data.get("dismissed_filename", _DEFAULT_DISMISSED_FILENAME),
    )

    return AppConfig(
        data=DataConfig(
            path=str(_resolve_path(db_dir)),
            filename=data_filename,
            dismissed_filename=dismissed_filename,
        ),
        server=ServerConfig(
            host=_env_str("SUBHUB_HOST", legacy_server.get("host", "127.0.0.1")),
            port=_env_int("SUBHUB_PORT", legacy_server.get("port", 8000)),
        ),
        reminder=ReminderConfig(
            enabled=_env_bool("SUBHUB_REMINDER_ENABLED", True),
            reminder_days=_env_int_list(
                "SUBHUB_REMINDER_DAYS",
                legacy_reminder.get("reminder_days", [7, 3, 2, 1]),
            ),
            check_interval_hours=_env_int(
                "SUBHUB_REMINDER_CHECK_INTERVAL_HOURS",
                legacy_reminder.get("check_interval_hours", 1),
            ),
            use_llm=_env_bool("SUBHUB_REMINDER_USE_LLM", False),
        ),
        report=ReportConfig(
            base_currency=os.environ.get(
                "SUBHUB_REPORT_BASE_CURRENCY",
                os.environ.get(
                    "SUBHUB_BASE_CURRENCY", legacy_report.get("base_currency", "CNY")
                ),
            ),
        ),
        webhook=WebhookConfig(
            url=_env_str("SUBHUB_WEBHOOK_URL", legacy_webhook.get("url", "")),
            timeout_seconds=_env_int(
                "SUBHUB_WEBHOOK_TIMEOUT_SECONDS",
                legacy_webhook.get("timeout_seconds", 5),
            ),
            enabled=bool(_env_str("SUBHUB_WEBHOOK_URL", legacy_webhook.get("url", ""))),
        ),
        matrix=_optional_matrix_config(require_bot_runtime),
        llm=_optional_llm_config(require_bot_runtime),
        r2=R2Config(
            endpoint=os.environ.get("R2_ENDPOINT", ""),
            access_key=os.environ.get("R2_ACCESS_KEY", ""),
            secret_key=os.environ.get("R2_SECRET_KEY", ""),
            bucket=os.environ.get("R2_BUCKET", "link-media"),
            public_url=os.environ.get("R2_PUBLIC_URL", ""),
        ),
        download=DownloadConfig(
            root=_resolve_path(os.environ.get("SUBHUB_DOWNLOAD_DIR", _DEFAULT_DOWNLOAD_DIR)),
            images=_env_bool("SUBHUB_DOWNLOAD_R2_IMAGES", True),
            videos=_env_bool("SUBHUB_DOWNLOAD_R2_VIDEOS", False),
            audios=_env_bool("SUBHUB_DOWNLOAD_R2_AUDIOS", False),
            files=_env_bool("SUBHUB_DOWNLOAD_R2_FILES", False),
        ),
        log_level=os.environ.get("SUBHUB_LOG_LEVEL", "INFO").upper(),
    )
