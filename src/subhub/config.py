"""配置加载模块。从 config.toml 和 .env 加载所有配置。"""

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class DataConfig:
    path: str
    filename: str

    @property
    def filepath(self) -> Path:
        return Path(self.path) / self.filename


@dataclass
class LLMConfig:
    model: str
    base_url: str
    api_key: str


@dataclass
class ReminderConfig:
    advance_days: int
    check_interval_hours: int


@dataclass
class ReportConfig:
    base_currency: str


@dataclass
class AppConfig:
    data: DataConfig
    llm: LLMConfig
    reminder: ReminderConfig
    report: ReportConfig


def load_config(config_path: str = "config.toml", env_path: str = ".env") -> AppConfig:
    """加载配置文件和环境变量。"""
    load_dotenv(env_path)

    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise ValueError("DASHSCOPE_API_KEY 未在 .env 中设置")

    return AppConfig(
        data=DataConfig(
            path=raw["data"]["path"],
            filename=raw["data"]["filename"],
        ),
        llm=LLMConfig(
            model=raw["llm"]["model"],
            base_url=raw["llm"]["base_url"],
            api_key=api_key,
        ),
        reminder=ReminderConfig(
            advance_days=raw["reminder"]["advance_days"],
            check_interval_hours=raw["reminder"]["check_interval_hours"],
        ),
        report=ReportConfig(
            base_currency=raw.get("report", {}).get("base_currency", "CNY"),
        ),
    )
