"""配置加载模块。从环境变量加载运行配置。"""

import os
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
    if value is None or value == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


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


def load_config(config_path: str | None = None,
                env_path: str | None = None) -> AppConfig:
    """加载 .env 和当前进程环境变量。

    config_path 保留在签名中以兼容现有调用；运行时配置不再要求 config.toml。
    """
    if env_path is None:
        load_dotenv()
    else:
        load_dotenv(env_path)

    db_dir = os.environ.get("SUBHUB_DB_DIR", _DEFAULT_DB_DIR)
    data_filename = os.environ.get("SUBHUB_DB_FILENAME", _DEFAULT_DATA_FILENAME)
    dismissed_filename = os.environ.get(
        "SUBHUB_DISMISSED_FILENAME", _DEFAULT_DISMISSED_FILENAME
    )

    return AppConfig(
        data=DataConfig(
            path=str(_resolve_path(db_dir)),
            filename=data_filename,
            dismissed_filename=dismissed_filename,
        ),
        server=ServerConfig(
            host=os.environ.get("SUBHUB_HOST", "127.0.0.1"),
            port=_env_int("SUBHUB_PORT", 8000),
        ),
        reminder=ReminderConfig(
            advance_days=_env_int("SUBHUB_REMINDER_ADVANCE_DAYS", 3),
            check_interval_hours=_env_int("SUBHUB_REMINDER_CHECK_INTERVAL_HOURS", 1),
            use_llm=_env_bool("SUBHUB_REMINDER_USE_LLM", False),
        ),
        report=ReportConfig(
            base_currency=os.environ.get("SUBHUB_BASE_CURRENCY", "CNY"),
        ),
        webhook=WebhookConfig(
            url=os.environ.get("SUBHUB_WEBHOOK_URL", ""),
            timeout_seconds=_env_int("SUBHUB_WEBHOOK_TIMEOUT_SECONDS", 5),
            enabled=bool(os.environ.get("SUBHUB_WEBHOOK_URL", "")),
        ),
        matrix=MatrixConfig(
            homeserver=_required_env("MATRIX_HOMESERVER"),
            user=_required_env("MATRIX_USER"),
            password=_required_env("MATRIX_PASSWORD"),
            rooms=[
                room.strip()
                for room in _required_env("MATRIX_ROOMS").split(",")
                if room.strip()
            ],
        ),
        llm=LLMConfig(
            base_url=_required_env("SUBHUB_LLM_BASE_URL"),
            api_key=_required_env("SUBHUB_LLM_API_KEY"),
            model=_required_env("SUBHUB_LLM_MODEL"),
            system_prompt=_required_env("SUBHUB_SYSTEM_PROMPT"),
        ),
        download=DownloadConfig(
            root=_resolve_path(os.environ.get("SUBHUB_DOWNLOAD_DIR", _DEFAULT_DOWNLOAD_DIR)),
            images=_env_bool("SUBHUB_DOWNLOAD_R2_IMAGES", True),
            videos=_env_bool("SUBHUB_DOWNLOAD_R2_VIDEOS", False),
            audios=_env_bool("SUBHUB_DOWNLOAD_R2_AUDIOS", False),
            files=_env_bool("SUBHUB_DOWNLOAD_R2_FILES", False),
        ),
    )
