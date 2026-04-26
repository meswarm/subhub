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
