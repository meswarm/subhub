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

    config = load_config(env_path=_empty_env_file(tmp_path))

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

    config = load_config(env_path=_empty_env_file(tmp_path))

    assert config.data.dismissed_filepath == dismissed.resolve()


def test_load_config_uses_report_base_currency(tmp_path, monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("SUBHUB_REPORT_BASE_CURRENCY", "USD")

    config = load_config(env_path=_empty_env_file(tmp_path))

    assert config.report.base_currency == "USD"


def test_required_env_rejects_whitespace_only_value(tmp_path, monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("MATRIX_PASSWORD", "   ")

    with pytest.raises(ValueError, match="MATRIX_PASSWORD"):
        load_config(env_path=_empty_env_file(tmp_path))


def test_matrix_rooms_rejects_empty_room_list(tmp_path, monkeypatch):
    _set_required_env(monkeypatch)
    monkeypatch.setenv("MATRIX_ROOMS", ",")

    with pytest.raises(ValueError, match="MATRIX_ROOMS"):
        load_config(env_path=_empty_env_file(tmp_path))
