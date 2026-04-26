import os

import pytest

from subhub.config import load_config


@pytest.fixture(autouse=True)
def clear_runtime_env(monkeypatch):
    prefixes = ("SUBHUB_", "MATRIX_", "R2_")
    for name in list(os.environ):
        if name.startswith(prefixes):
            monkeypatch.delenv(name, raising=False)


def _empty_env_file(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("", encoding="utf-8")
    return env_file


def _set_required_env(monkeypatch):
    monkeypatch.setenv("MATRIX_HOMESERVER", "https://matrix.example.com")
    monkeypatch.setenv("MATRIX_USER", "@subhub:matrix.example.com")
    monkeypatch.setenv("MATRIX_PASSWORD", "secret")
    monkeypatch.setenv("MATRIX_ROOMS", "!room:matrix.example.com")
    monkeypatch.setenv("SUBHUB_LLM_BASE_URL", "https://llm.example.com/v1")
    monkeypatch.setenv("SUBHUB_LLM_API_KEY", "key")
    monkeypatch.setenv("SUBHUB_LLM_MODEL", "qwen-plus")
    monkeypatch.setenv("SUBHUB_SYSTEM_PROMPT", "prompt")


def test_load_config_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _set_required_env(monkeypatch)

    config = load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=True)

    assert config.matrix.homeserver == "https://matrix.example.com"
    assert config.matrix.rooms == ["!room:matrix.example.com"]
    assert config.data.filepath == (tmp_path / "db" / "subscriptions.json").resolve()
    assert config.data.dismissed_filepath == (tmp_path / "db" / "dismissed.json").resolve()
    assert config.download.root == (tmp_path / "downloads").resolve()
    assert config.download.images is True
    assert config.download.videos is False
    assert config.reminder.enabled is True
    assert config.reminder.use_llm is False
    assert config.llm.temperature == 0.7
    assert config.llm.max_history == 20
    assert config.llm.vision_enabled is False
    assert config.llm.skills_dir == (tmp_path / "skills" / "manage-subscriptions").resolve()
    assert config.r2.enabled is False
    assert config.log_level == "INFO"


def test_load_config_absolute_dismissed_path(tmp_path, monkeypatch):
    dismissed = tmp_path / "state" / "dismissed-state.json"
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SUBHUB_DB_DIR", str(tmp_path / "db"))
    monkeypatch.setenv("SUBHUB_DISMISSED_FILENAME", str(dismissed))

    config = load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=True)

    assert config.data.dismissed_filepath == dismissed.resolve()


def test_load_config_uses_report_base_currency(tmp_path, monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SUBHUB_REPORT_BASE_CURRENCY", "USD")

    config = load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=True)

    assert config.report.base_currency == "USD"


def test_load_config_reads_vision_and_r2_settings(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SUBHUB_LLM_TEMPERATURE", "0.3")
    monkeypatch.setenv("SUBHUB_LLM_MAX_HISTORY", "9")
    monkeypatch.setenv("SUBHUB_LLM_VISION_ENABLED", "true")
    monkeypatch.setenv("SUBHUB_SKILLS_DIR", "custom-skills")
    monkeypatch.setenv("SUBHUB_REMINDER_ENABLED", "false")
    monkeypatch.setenv("SUBHUB_LOG_LEVEL", "debug")
    monkeypatch.setenv("R2_ENDPOINT", "https://r2.example.com")
    monkeypatch.setenv("R2_ACCESS_KEY", "ak")
    monkeypatch.setenv("R2_SECRET_KEY", "sk")
    monkeypatch.setenv("R2_BUCKET", "linux-storage")
    monkeypatch.setenv("R2_PUBLIC_URL", "https://cdn.example.com")

    config = load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=True)

    assert config.llm.temperature == 0.3
    assert config.llm.max_history == 9
    assert config.llm.vision_enabled is True
    assert config.llm.skills_dir == (tmp_path / "custom-skills").resolve()
    assert config.reminder.enabled is False
    assert config.r2.enabled is True
    assert config.r2.bucket == "linux-storage"
    assert config.log_level == "DEBUG"


def test_load_config_reads_system_prompt_from_markdown_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _set_required_env(monkeypatch)
    prompt_file = tmp_path / "prompts" / "system_prompt.md"
    prompt_file.parent.mkdir(parents=True)
    prompt_file.write_text("system prompt from file\n{today_context}", encoding="utf-8")
    monkeypatch.setenv("SUBHUB_SYSTEM_PROMPT_FILE", str(prompt_file))
    monkeypatch.delenv("SUBHUB_SYSTEM_PROMPT", raising=False)

    config = load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=True)

    assert config.llm.system_prompt == "system prompt from file\n{today_context}"


def test_prompt_file_takes_precedence_over_inline_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _set_required_env(monkeypatch)
    prompt_file = tmp_path / "prompts" / "system_prompt.md"
    prompt_file.parent.mkdir(parents=True)
    prompt_file.write_text("prompt from file", encoding="utf-8")
    monkeypatch.setenv("SUBHUB_SYSTEM_PROMPT_FILE", str(prompt_file))
    monkeypatch.setenv("SUBHUB_SYSTEM_PROMPT", "prompt from env")

    config = load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=True)

    assert config.llm.system_prompt == "prompt from file"


def test_required_env_rejects_whitespace_only_value(tmp_path, monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("MATRIX_PASSWORD", "   ")

    with pytest.raises(ValueError, match="MATRIX_PASSWORD"):
        load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=True)


def test_matrix_rooms_rejects_empty_room_list(tmp_path, monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("MATRIX_ROOMS", ",")

    with pytest.raises(ValueError, match="MATRIX_ROOMS"):
        load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=True)


def test_load_config_legacy_toml_does_not_require_bot_runtime(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[data]
path = "./legacy-db"
filename = "legacy-subscriptions.json"
dismissed_filename = "legacy-dismissed.json"

[server]
host = "0.0.0.0"
port = 58001

[reminder]
reminder_days = [7, 3, 1]
check_interval_hours = 2

[report]
base_currency = "USD"

[webhook]
url = "http://127.0.0.1:59001/alert"
timeout_seconds = 7
""",
        encoding="utf-8",
    )

    config = load_config(config_path=str(config_file), env_path=_empty_env_file(tmp_path))

    assert config.data.filepath == (tmp_path / "legacy-db" / "legacy-subscriptions.json").resolve()
    assert config.data.dismissed_filepath == (tmp_path / "legacy-db" / "legacy-dismissed.json").resolve()
    assert config.server.host == "0.0.0.0"
    assert config.server.port == 58001
    assert config.reminder.reminder_days == [7, 3, 1]
    assert config.reminder.check_interval_hours == 2
    assert config.report.base_currency == "USD"
    assert config.webhook.url == "http://127.0.0.1:59001/alert"
    assert config.webhook.timeout_seconds == 7
    assert config.webhook.enabled is True
    assert config.matrix is None
    assert config.llm is None


def test_load_config_legacy_mode_ignores_partial_matrix_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MATRIX_HOMESERVER", "https://matrix.example.com")

    config = load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=False)

    assert config.matrix is None


def test_load_config_uses_default_reminder_days(tmp_path, monkeypatch):
    _set_required_env(monkeypatch)

    config = load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=True)

    assert config.reminder.reminder_days == [7, 3, 2, 1]


def test_load_config_can_override_reminder_days(tmp_path, monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SUBHUB_REMINDER_DAYS", "10, 5,2")

    config = load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=True)

    assert config.reminder.reminder_days == [10, 5, 2]


def test_load_config_legacy_mode_ignores_partial_llm_env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SUBHUB_LLM_BASE_URL", "https://llm.example.com/v1")

    config = load_config(env_path=_empty_env_file(tmp_path), require_bot_runtime=False)

    assert config.llm is None


def test_load_config_loads_config_path_sibling_env(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    config_dir = tmp_path / "config"
    cwd.mkdir()
    config_dir.mkdir()
    monkeypatch.chdir(cwd)
    config_file = config_dir / "config.toml"
    config_file.write_text(
        """
[server]
port = 58001
""",
        encoding="utf-8",
    )
    (config_dir / ".env").write_text("SUBHUB_PORT=58002\n", encoding="utf-8")

    config = load_config(config_path=str(config_file), env_path=None)

    assert config.server.port == 58002
