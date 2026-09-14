import json
import imagent.client as client


def test_env_var_takes_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-from-env")
    monkeypatch.setattr(client, "_CONFIG_PATH", tmp_path / "config.json")
    (tmp_path / "config.json").write_text(json.dumps({"OPENAI_API_KEY": "sk-from-file"}))
    assert client.resolve_api_key() == "sk-from-env"


def test_config_file_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"OPENAI_API_KEY": "sk-from-file"}))
    monkeypatch.setattr(client, "_CONFIG_PATH", cfg)
    assert client.resolve_api_key() == "sk-from-file"


def test_missing_key_returns_none(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(client, "_CONFIG_PATH", tmp_path / "nope.json")
    assert client.resolve_api_key() is None


def test_placeholder_key_is_ignored(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"OPENAI_API_KEY": "sk-..."}))
    monkeypatch.setattr(client, "_CONFIG_PATH", cfg)
    assert client.resolve_api_key() is None


def test_model_catalog_defaults():
    assert client.DEFAULT_MODEL == "gpt-image-2.5-flare"
    assert set(client.MODELS) == {"gpt-image-2", "gpt-image-2.5-flare",
                                  "gpt-image-2.5-sunburst"}
    assert "gpt-image-1-mini" not in client.MODELS
    assert "gpt-image-2-2026-04-21" not in client.MODELS
    assert "gpt-image-2.5-flare-2026-09-08" not in client.MODELS
    # Retired: both shut down before this release's models do.
    assert "gpt-image-1" not in client.MODELS
    assert "gpt-image-1.5" not in client.MODELS
    assert all("dall-e" not in m for m in client.MODELS)


def test_friendly_error_maps_403_and_429():
    assert "verif" in client.friendly_error(Exception("Error code: 403 - org not verified")).lower()
    assert "rate" in client.friendly_error(Exception("Error code: 429 - too many requests")).lower()


def test_malformed_config_returns_none(monkeypatch, tmp_path, caplog):
    import logging
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text("{bad json")
    monkeypatch.setattr(client, "_CONFIG_PATH", cfg)
    with caplog.at_level(logging.WARNING, logger="imagent"):
        assert client.resolve_api_key() is None
    assert "could not read" in caplog.text


def test_env_placeholder_is_ignored(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "your_openai_api_key_here")
    monkeypatch.setattr(client, "_CONFIG_PATH", tmp_path / "nope.json")
    assert client.resolve_api_key() is None


def test_friendly_error_uses_status_code():
    class FakeAPIError(Exception):
        status_code = 403

    class FakeRateError(Exception):
        status_code = 429

    assert "verif" in client.friendly_error(FakeAPIError("denied")).lower()
    assert "rate" in client.friendly_error(FakeRateError("slow down")).lower()
