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
    advance_days: int
    check_interval_hours: int
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
    download: DownloadConfig | None = None

    def __post_init__(self):
        if self.webhook is None:
            self.webhook = WebhookConfig()
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


def _resolve_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _env_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None:
        return default
    return value


def _load_legacy_config(config_path: str | None) -> dict:
    if config_path is None:
        path = find_config()
        if path is None:
            return {}
    else:
        path = Path(config_path).expanduser()
        if not path.is_file():
            found = find_config(config_path)
            if found is None:
                raise FileNotFoundError(f"Config file not found: {config_path}")
            path = found

    with open(path, "rb") as f:
        return tomllib.load(f)


def _optional_matrix_config(require_bot_runtime: bool) -> MatrixConfig | None:
    if require_bot_runtime:
        return MatrixConfig(
            homeserver=_required_env("MATRIX_HOMESERVER"),
            user=_required_env("MATRIX_USER"),
            password=_required_env("MATRIX_PASSWORD"),
            rooms=_matrix_rooms(),
        )
    if not any(os.environ.get(name) is not None for name in (
        "MATRIX_HOMESERVER", "MATRIX_USER", "MATRIX_PASSWORD", "MATRIX_ROOMS"
    )):
        return None
    return MatrixConfig(
        homeserver=_required_env("MATRIX_HOMESERVER"),
        user=_required_env("MATRIX_USER"),
        password=_required_env("MATRIX_PASSWORD"),
        rooms=_matrix_rooms(),
    )


def _optional_llm_config(require_bot_runtime: bool) -> LLMConfig | None:
    if require_bot_runtime:
        return LLMConfig(
            base_url=_required_env("SUBHUB_LLM_BASE_URL"),
            api_key=_required_env("SUBHUB_LLM_API_KEY"),
            model=_required_env("SUBHUB_LLM_MODEL"),
            system_prompt=_required_env("SUBHUB_SYSTEM_PROMPT"),
        )
    if not any(os.environ.get(name) is not None for name in (
        "SUBHUB_LLM_BASE_URL", "SUBHUB_LLM_API_KEY",
        "SUBHUB_LLM_MODEL", "SUBHUB_SYSTEM_PROMPT",
    )):
        return None
    return LLMConfig(
        base_url=_required_env("SUBHUB_LLM_BASE_URL"),
        api_key=_required_env("SUBHUB_LLM_API_KEY"),
        model=_required_env("SUBHUB_LLM_MODEL"),
        system_prompt=_required_env("SUBHUB_SYSTEM_PROMPT"),
    )


def load_config(config_path: str | None = None,
                env_path: str | None = None,
                require_bot_runtime: bool = False) -> AppConfig:
    """加载 legacy config.toml、.env 和当前进程环境变量。"""
    if env_path is None:
        load_dotenv()
    else:
        load_dotenv(env_path)

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
            advance_days=_env_int(
                "SUBHUB_REMINDER_ADVANCE_DAYS", legacy_reminder.get("advance_days", 3)
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
        download=DownloadConfig(
            root=_resolve_path(os.environ.get("SUBHUB_DOWNLOAD_DIR", _DEFAULT_DOWNLOAD_DIR)),
            images=_env_bool("SUBHUB_DOWNLOAD_R2_IMAGES", True),
            videos=_env_bool("SUBHUB_DOWNLOAD_R2_VIDEOS", False),
            audios=_env_bool("SUBHUB_DOWNLOAD_R2_AUDIOS", False),
            files=_env_bool("SUBHUB_DOWNLOAD_R2_FILES", False),
        ),
    )
