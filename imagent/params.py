"""Parameter constants, per-model capabilities, and size validation.

Public entry points: capabilities_for(), validate_custom_dimensions(), resolve_size(),
resolve_quality(), resolve_background(); plus the SIZE_PRESETS / QUALITIES /
BACKGROUNDS / FORMATS / MODERATIONS lists and the CUSTOM_DIM_* widget bounds.
"""
from __future__ import annotations

import logging

log = logging.getLogger("imagent")

# Size presets, all supported by every model in the catalog.
_BASE_SIZES = ["auto", "1024x1024", "1024x1536", "1536x1024"]
_GPT2_SIZES = ["2048x2048", "2048x1152", "1152x2048", "3840x2160", "2160x3840"]
SIZE_PRESETS = [*_BASE_SIZES, *_GPT2_SIZES, "custom"]

# Size option list for the IO DynamicCombo (what each model can pick).
SIZES_GPT2 = [*_BASE_SIZES, *_GPT2_SIZES, "custom"]         # gpt-image-2 / 2.5

# custom_width / custom_height INT-widget bounds (mirror the official node).
CUSTOM_DIM_MIN, CUSTOM_DIM_MAX, CUSTOM_DIM_STEP = 1024, 3840, 16

# Per-model background option lists (gpt-image-2 cannot do transparent).
BACKGROUNDS = ["auto", "opaque", "transparent"]
BACKGROUNDS_GPT2 = ["auto", "opaque"]

# 'xhigh' and 'max' exist only on gpt-image-2.5 (gated in resolve_quality).
_EXTENDED_QUALITIES = {"xhigh", "max"}
QUALITIES = ["auto", "low", "medium", "high", "xhigh", "max"]
FORMATS = ["png", "jpeg", "webp"]
MODERATIONS = ["auto", "low"]

# Widget bounds shared by both nodes' IO schemas.
N_MIN, N_MAX = 1, 8

# Per-model capability flags. Keys (all default False for unknown models):
#   transparent_background - background="transparent" (NOT gpt-image-2, which errors)
#   extended_quality       - quality="xhigh" / "max" (gpt-image-2.5 only)
_DEFAULT_CAPS = {"transparent_background": False, "extended_quality": False}

CAPABILITIES: dict[str, dict[str, bool]] = {
    "gpt-image-2.5-sunburst": {"transparent_background": True,  "extended_quality": True},
    "gpt-image-2.5-flare":    {"transparent_background": True,  "extended_quality": True},
    "gpt-image-2":            {"transparent_background": False, "extended_quality": False},
}

# Custom-resolution constraints, shared by gpt-image-2 and gpt-image-2.5.
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


def resolve_size(size: str, custom_width: int, custom_height: int) -> str:
    """Resolve the size parameter, validating 'custom' against the WxH rules."""
    if size == "custom":
        return validate_custom_dimensions(custom_width, custom_height)
    return size


def resolve_quality(quality: str, model: str) -> str:
    """Drop an unsupported extended quality tier to 'high'.

    'xhigh' and 'max' are gpt-image-2.5 only; older models error on them, so they
    fall back to 'high' when the model is switched.
    """
    if quality in _EXTENDED_QUALITIES and not capabilities_for(model)["extended_quality"]:
        log.info("imagent: %s does not support quality '%s'; using 'high'.", model, quality)
        return "high"
    return quality


def resolve_background(background: str, model: str) -> str:
    """Drop an unsupported transparent background to 'auto'.

    gpt-image-2 errors on background='transparent'; gpt-image-2.5 supports it.
    Falling back to 'auto' keeps the node compatible across model switches.
    """
    if background == "transparent" and not capabilities_for(model)["transparent_background"]:
        log.info("imagent: %s does not support a transparent background; using 'auto'.", model)
        return "auto"
    return background
