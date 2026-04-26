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
    assert config.reminder.use_llm is False


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
advance_days = 5
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
    assert config.reminder.advance_days == 5
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
