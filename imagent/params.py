"""Parameter constants, per-model capabilities, and size validation.

Public entry points: capabilities_for(), validate_custom_dimensions(), resolve_size(),
resolve_background(); plus the SIZE_PRESETS / QUALITIES / BACKGROUNDS / FORMATS /
INPUT_FIDELITIES / MODERATIONS lists and the CUSTOM_DIM_* widget bounds.
"""
from __future__ import annotations

import logging

log = logging.getLogger("imagent")

# Size presets. The base sizes work on every gpt-image model; the high-res presets
# and 'custom' are gpt-image-2 only (gated in resolve_size to stay cross-model safe).
_BASE_SIZES = ["auto", "1024x1024", "1024x1536", "1536x1024"]
_GPT2_SIZES = ["2048x2048", "2048x1152", "1152x2048", "3840x2160", "2160x3840"]
_GPT2_ONLY_SIZES = set(_GPT2_SIZES)
SIZE_PRESETS = [*_BASE_SIZES, *_GPT2_SIZES, "custom"]

# Per-model size option lists for the IO DynamicCombo (what each model can pick).
SIZES_BASE = list(_BASE_SIZES)                              # gpt-image-1 / 1.5
SIZES_GPT2 = [*_BASE_SIZES, *_GPT2_SIZES, "custom"]         # gpt-image-2

# custom_width / custom_height INT-widget bounds (mirror the official node).
CUSTOM_DIM_MIN, CUSTOM_DIM_MAX, CUSTOM_DIM_STEP = 1024, 3840, 16

# Per-model background option lists (gpt-image-2 cannot do transparent).
BACKGROUNDS = ["auto", "opaque", "transparent"]
BACKGROUNDS_GPT2 = ["auto", "opaque"]

QUALITIES = ["auto", "low", "medium", "high"]
FORMATS = ["png", "jpeg", "webp"]
INPUT_FIDELITIES = ["high", "low"]
MODERATIONS = ["auto", "low"]

# Widget bounds shared by both nodes' IO schemas.
N_MIN, N_MAX = 1, 8

# Per-model capability flags. Keys (all default False for unknown models):
#   custom_size            - arbitrary WxH sizes (gpt-image-2 only)
#   input_fidelity         - edit input_fidelity param (gpt-image-1.x)
#   transparent_background - background="transparent" (NOT gpt-image-2, which errors)
_DEFAULT_CAPS = {
    "custom_size": False, "input_fidelity": False, "transparent_background": False,
}

CAPABILITIES: dict[str, dict[str, bool]] = {
    "gpt-image-2":   {"custom_size": True,  "input_fidelity": False, "transparent_background": False},
    "gpt-image-1.5": {"custom_size": False, "input_fidelity": True,  "transparent_background": True},
    "gpt-image-1":   {"custom_size": False, "input_fidelity": True,  "transparent_background": True},
}

# gpt-image-2 custom-resolution constraints (mirror the official node, 2026-06-08).
_MAX_EDGE = 3840
_MIN_TOTAL_PX = 655_360
_MAX_TOTAL_PX = 8_294_400


def capabilities_for(model: str) -> dict[str, bool]:
    """Return a copy of the capability flags for *model*, defaulting to all-False."""
    return dict(CAPABILITIES.get(model, _DEFAULT_CAPS))


def validate_custom_dimensions(width: int, height: int) -> str:
    """Validate gpt-image-2 custom WxH dimensions; return the normalized 'WxH'.

    Rules match the official node: multiples of 16, max edge 3840, aspect <= 3:1,
    and total pixels between 655,360 and 8,294,400.
    """
    try:
        w, h = int(width), int(height)
    except (TypeError, ValueError):
        raise ValueError(f"custom dimensions must be integers, got {width!r}x{height!r}") from None
    if w <= 0 or h <= 0:
        raise ValueError(f"custom dimensions must be positive, got {w}x{h}")
    if w % 16 or h % 16:
        raise ValueError(f"custom width and height must be multiples of 16, got {w}x{h}")
    if max(w, h) > _MAX_EDGE:
        raise ValueError(f"custom max edge must be <= {_MAX_EDGE}, got {w}x{h}")
    if max(w, h) / min(w, h) > 3:
        raise ValueError(f"custom aspect ratio must not exceed 3:1, got {w}x{h}")
    total = w * h
    if not (_MIN_TOTAL_PX <= total <= _MAX_TOTAL_PX):
        raise ValueError(
            f"custom total pixels must be between {_MIN_TOTAL_PX} and {_MAX_TOTAL_PX}, got {total}")
    return f"{w}x{h}"


def resolve_size(size: str, custom_width: int, custom_height: int, model: str) -> str:
    """Resolve the size parameter to a value the selected model accepts.

    'custom' and the high-res presets are gpt-image-2 only; for other models they
    fall back to 'auto' so switching models never sends an unsupported size.
    """
    caps = capabilities_for(model)
    if size == "custom":
        if not caps["custom_size"]:
            log.info("imagent: %s does not support custom sizes; using 'auto'.", model)
            return "auto"
        return validate_custom_dimensions(custom_width, custom_height)
    if size in _GPT2_ONLY_SIZES and not caps["custom_size"]:
        log.info("imagent: size %s is gpt-image-2 only; using 'auto' for %s.", size, model)
        return "auto"
    return size


def resolve_background(background: str, model: str) -> str:
    """Drop an unsupported transparent background to 'auto'.

    gpt-image-2 errors on background='transparent'; only gpt-image-1.x supports
    it. Falling back to 'auto' keeps the node compatible across model switches.
    """
    if background == "transparent" and not capabilities_for(model)["transparent_background"]:
        log.info("imagent: %s does not support a transparent background; using 'auto'.", model)
        return "auto"
    return background
