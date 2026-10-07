"""API key / base URL resolution, model catalog, and client construction.

Public entry points: resolve_api_key(), resolve_base_url(), get_client(),
friendly_error(); plus the MODELS list and DEFAULT_MODEL constant.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openai import OpenAI

log = logging.getLogger("imagent")

# config.json lives at the repo root, next to this package directory.
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"

# Current OpenAI image models, verified 2026-09-13. Dated snapshots, -mini and
# models with an announced shutdown date are intentionally omitted.
MODELS = [
    "gpt-image-2.5-flare",
    "gpt-image-2.5-sunburst",
    "gpt-image-2",
]
DEFAULT_MODEL = "gpt-image-2.5-flare"

_PLACEHOLDERS = {"", "sk-...", "your_openai_api_key_here"}

# Base URLs that mean "no custom endpoint": unset falls through to the OpenAI
# default, https://api.openai.com/v1.
_BASE_URL_PLACEHOLDERS = {"", "your_base_url_here", "https://your-endpoint/v1"}


def _load_config() -> dict:
    """Return config.json as a dict; {} when missing, unreadable, or not an object."""
    try:
        if _CONFIG_PATH.exists():
            cfg = json.loads(_CONFIG_PATH.read_text())
            if isinstance(cfg, dict):
                return cfg
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("imagent: could not read %s: %s", _CONFIG_PATH, exc)
    return {}


def _setting(env_var: str, config_key: str, placeholders: set[str]) -> str | None:
    """Resolve one setting from the env var (preferred) or config.json, else None."""
    env_value = (os.environ.get(env_var) or "").strip()
    if env_value and env_value not in placeholders:
        return env_value
    file_value = _load_config().get(config_key, "")
    if isinstance(file_value, str):
        file_value = file_value.strip()
        if file_value and file_value not in placeholders:
            return file_value
    return None


def resolve_api_key() -> str | None:
    """Return the API key from env (preferred) or config.json, else None."""
    return _setting("OPENAI_API_KEY", "OPENAI_API_KEY", _PLACEHOLDERS)


def resolve_base_url() -> str | None:
    """Return the API base URL from env (preferred) or config.json, else None.

    None means "use the OpenAI default"; set OPENAI_BASE_URL (env or config.json)
    to aim the nodes at any OpenAI-compatible endpoint.
    """
    return _setting("OPENAI_BASE_URL", "OPENAI_BASE_URL", _BASE_URL_PLACEHOLDERS)


def _override(value: str, placeholders: set[str]) -> str | None:
    """Normalize a node-level override; None when blank or still a placeholder."""
    value = (value or "").strip()
    return value if value and value not in placeholders else None


def get_client(api_key: str = "", base_url: str = "") -> "OpenAI | None":
    """Construct an OpenAI client, or None if no key is available.

    A non-empty *api_key* / *base_url* (node-level overrides) wins over the env
    var and config.json. base_url is passed only when one resolved, so the SDK
    keeps its default endpoint otherwise.
    """
    key = _override(api_key, _PLACEHOLDERS) or resolve_api_key()
    if not key:
        return None
    url = _override(base_url, _BASE_URL_PLACEHOLDERS) or resolve_base_url()
    from openai import OpenAI
    return OpenAI(api_key=key, **({"base_url": url} if url else {}))


def friendly_error(exc: Exception) -> str:
    """Turn an OpenAI exception into an actionable message.

    Prefers the exception's HTTP status_code (OpenAI APIError exposes it) and
    falls back to anchored substrings, so unrelated text containing 'verif' or
    '429' is not misclassified.
    """
    msg = str(exc)
    lower = msg.lower()
    status = getattr(exc, "status_code", None)
    is_verif = "organization verification" in lower or "must be verified" in lower
    if status == 403 or "error code: 403" in lower or is_verif:
        return ("Error: 403 — your OpenAI org may need API Organization "
                "Verification before gpt-image models can be used. Details: " + msg)
    if status == 429 or "error code: 429" in lower:
        return "Error: 429 — rate limit / quota exceeded. Details: " + msg
    return f"Error: {msg}"
