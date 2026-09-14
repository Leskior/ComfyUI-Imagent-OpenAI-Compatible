"""OpenAI API key resolution, model catalog, and client construction.

Public entry points: resolve_api_key(), get_client(), friendly_error(); plus the
MODELS list and DEFAULT_MODEL constant.
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


def resolve_api_key() -> str | None:
    """Return the API key from env (preferred) or config.json, else None."""
    env_key = os.environ.get("OPENAI_API_KEY")
    if env_key and env_key not in _PLACEHOLDERS:
        return env_key
    try:
        if _CONFIG_PATH.exists():
            cfg = json.loads(_CONFIG_PATH.read_text())
            file_key = cfg.get("OPENAI_API_KEY", "")
            if isinstance(file_key, str) and file_key and file_key not in _PLACEHOLDERS:
                return file_key
    except (json.JSONDecodeError, OSError) as exc:
        log.warning("imagent: could not read %s: %s", _CONFIG_PATH, exc)
    return None


def get_client() -> "OpenAI | None":
    """Construct an OpenAI client, or None if no key is available."""
    key = resolve_api_key()
    if not key:
        return None
    from openai import OpenAI
    return OpenAI(api_key=key)


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
