"""配置加载模块。从 config.toml 和 .env 加载所有配置。"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


# 默认数据目录
_DEFAULT_DATA_DIR = "~/.local/share/subhub"
_DEFAULT_DATA_FILENAME = "subscriptions.json"


@dataclass
class DataConfig:
    path: str
    filename: str

    @property
    def filepath(self) -> Path:
        return Path(self.path).expanduser().resolve() / self.filename


@dataclass
class ReminderConfig:
    advance_days: int
    check_interval_hours: int


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
class AppConfig:
    data: DataConfig
    server: ServerConfig
    reminder: ReminderConfig
    report: ReportConfig
    webhook: WebhookConfig = None

    def __post_init__(self):
        if self.webhook is None:
            self.webhook = WebhookConfig()


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


def load_config(config_path: str | None = None,
                env_path: str | None = None) -> AppConfig:
    """加载配置文件和环境变量。

    config_path: 显式指定配置文件路径。为 None 时使用 find_config 自动查找。
    env_path: 显式指定 .env 路径。为 None 时在配置文件同目录查找。
    """
    if config_path:
        resolved = Path(config_path)
    else:
        resolved = find_config()
    if not resolved or not resolved.is_file():
        raise FileNotFoundError("未找到 config.toml，请通过 --config 指定或放置到 ~/.config/subhub/")

    # .env 查找：显式指定 > 配置文件同目录 > 当前目录
    if env_path:
        load_dotenv(env_path)
    else:
        env_candidates = [resolved.parent / ".env", Path.cwd() / ".env"]
        for ep in env_candidates:
            if ep.is_file():
                load_dotenv(str(ep))
                break

    with open(resolved, "rb") as f:
        raw = tomllib.load(f)

    webhook_raw = raw.get("webhook", {})
    server_raw = raw.get("server", {})

    data_path = raw.get("data", {}).get("path", _DEFAULT_DATA_DIR)
    data_filename = raw.get("data", {}).get("filename", _DEFAULT_DATA_FILENAME)

    return AppConfig(
        data=DataConfig(path=data_path, filename=data_filename),
        server=ServerConfig(
            host=server_raw.get("host", "127.0.0.1"),
            port=int(server_raw.get("port", 8000)),
        ),
        reminder=ReminderConfig(
            advance_days=raw.get("reminder", {}).get("advance_days", 3),
            check_interval_hours=raw.get("reminder", {}).get("check_interval_hours", 1),
        ),
        report=ReportConfig(
            base_currency=raw.get("report", {}).get("base_currency", "CNY"),
        ),
        webhook=WebhookConfig(
            url=webhook_raw.get("url", ""),
            timeout_seconds=webhook_raw.get("timeout_seconds", 5),
            enabled=bool(webhook_raw.get("url", "")),
        ),
    )
