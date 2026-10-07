import json

import pytest

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


# ---------------------------------------------------------------------------
# Base URL resolution + client construction
# ---------------------------------------------------------------------------


def test_base_url_env_takes_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://from-env.example/v1")
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"OPENAI_BASE_URL": "https://from-file.example/v1"}))
    monkeypatch.setattr(client, "_CONFIG_PATH", cfg)
    assert client.resolve_base_url() == "https://from-env.example/v1"


def test_base_url_config_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps({"OPENAI_BASE_URL": "https://from-file.example/v1"}))
    monkeypatch.setattr(client, "_CONFIG_PATH", cfg)
    assert client.resolve_base_url() == "https://from-file.example/v1"


@pytest.mark.parametrize("value", ["", "   ", "your_base_url_here", "https://your-endpoint/v1"])
def test_base_url_blank_or_placeholder_is_none(monkeypatch, tmp_path, value):
    monkeypatch.setenv("OPENAI_BASE_URL", value)
    monkeypatch.setattr(client, "_CONFIG_PATH", tmp_path / "nope.json")
    assert client.resolve_base_url() is None


def test_get_client_defaults_to_the_openai_endpoint(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setattr(client, "_CONFIG_PATH", tmp_path / "nope.json")
    assert str(client.get_client().base_url).rstrip("/") == "https://api.openai.com/v1"


def test_get_client_uses_env_base_url_then_node_override(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://from-env.example/v1")
    monkeypatch.setattr(client, "_CONFIG_PATH", tmp_path / "nope.json")
    assert str(client.get_client().base_url).rstrip("/") == "https://from-env.example/v1"
    overridden = client.get_client(base_url="https://from-node.example/v1")
    assert str(overridden.base_url).rstrip("/") == "https://from-node.example/v1"


def test_get_client_node_key_overrides_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    monkeypatch.setattr(client, "_CONFIG_PATH", tmp_path / "nope.json")
    assert client.get_client(api_key="sk-node").api_key == "sk-node"


def test_get_client_blank_override_falls_back_to_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    monkeypatch.setattr(client, "_CONFIG_PATH", tmp_path / "nope.json")
    assert client.get_client(api_key="", base_url="").api_key == "sk-env"


def test_get_client_without_any_key_is_none(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(client, "_CONFIG_PATH", tmp_path / "nope.json")
    assert client.get_client() is None
    assert client.get_client(api_key="sk-...") is None   # still a placeholder


def test_non_object_config_is_ignored(monkeypatch, tmp_path):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = tmp_path / "config.json"
    cfg.write_text(json.dumps(["not", "an", "object"]))
    monkeypatch.setattr(client, "_CONFIG_PATH", cfg)
    assert client.resolve_api_key() is None
    assert client.resolve_base_url() is None
