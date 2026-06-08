"""Pure request-building / dispatch logic for the two nodes.

This module deliberately imports nothing from ComfyUI (`comfy_api`), so the whole
behavior — model gating, kwargs assembly, error handling — is unit-testable
without a running ComfyUI. The IO node wrappers in node_generate.py /
node_edit.py only marshal widget values into these functions.

Public entry points: run_generate(), run_edit().
"""
from __future__ import annotations

import io
import logging

from PIL import Image

from . import client as client_mod
from . import image_io
from . import params as params_mod

log = logging.getLogger("imagent")

_NO_KEY = "Error: OPENAI_API_KEY not found (set the env var or config.json)."
_NO_IMAGES = "Error: API returned no images."


def _named_png(pil_image: Image.Image, name: str) -> io.BytesIO:
    buf = io.BytesIO(image_io.pil_to_png_bytes(pil_image))
    buf.name = name           # OpenAI SDK infers content-type from the filename
    return buf


def run_generate(*, prompt, model, size, quality, background, output_format, n,
                 moderation="auto", custom_width=1024, custom_height=1024,
                 output_compression=100):
    """Text-to-image via images.generate.

    Returns (image_tensor, info_string). Never raises: a failed call yields an
    empty image plus a friendly error so a bad call can't crash the queue.
    """
    oai = client_mod.get_client()
    if oai is None:
        log.warning("imagent: %s", _NO_KEY)
        return (image_io.empty_image(), _NO_KEY)
    try:
        resolved_size = params_mod.resolve_size(size, custom_width, custom_height, model)
        resolved_background = params_mod.resolve_background(background, model)
        kwargs = {
            "model": model, "prompt": prompt, "n": n,
            "size": resolved_size, "quality": quality,
            "background": resolved_background, "output_format": output_format,
        }
        if output_format in ("jpeg", "webp"):
            kwargs["output_compression"] = output_compression
        if moderation != "auto":
            kwargs["moderation"] = moderation
        resp = oai.images.generate(**kwargs)
        if not resp.data:
            return (image_io.empty_image(), _NO_IMAGES)
        info = getattr(resp.data[0], "revised_prompt", None) \
            or f"Generated {len(resp.data)} image(s) with {model}."
        return (image_io.batch_from_response_data(resp.data), info)
    except Exception as exc:  # noqa: BLE001 - node must not crash the queue
        log.exception("imagent: image generation failed")
        return (image_io.empty_image(), client_mod.friendly_error(exc))


def run_edit(*, prompt, model, size, quality, background, output_format, n,
             images, mask=None, input_fidelity="high", moderation="auto",
             custom_width=1024, custom_height=1024):
    """Image edit / inpaint / multi-reference via images.edit.

    `images` is an iterable of IMAGE tensors (None entries are ignored).
    Returns (image_tensor, info_string); never raises (see run_generate).
    """
    oai = client_mod.get_client()
    if oai is None:
        log.warning("imagent: %s", _NO_KEY)
        return (image_io.empty_image(), _NO_KEY)

    refs = [t for t in (images or []) if t is not None]
    if not refs:
        msg = "Error: OpenAIImageEdit requires at least one reference image."
        log.warning("imagent: %s", msg)
        return (image_io.empty_image(), msg)

    if mask is not None and len(refs) > 1:
        msg = ("Error: mask inpainting requires a single reference image "
               "(connect only one image).")
        log.warning("imagent: %s", msg)
        return (image_io.empty_image(), msg)

    try:
        resolved_size = params_mod.resolve_size(size, custom_width, custom_height, model)
        resolved_background = params_mod.resolve_background(background, model)
        caps = params_mod.capabilities_for(model)
        # Downscale oversized references to fit the API's input pixel budget.
        ref_pils = [image_io.downscale_pil_to_pixel_limit(image_io.tensor_to_pil(t)[0])
                    for t in refs]

        kwargs = {
            "model": model, "prompt": prompt,
            "image": [_named_png(p, f"ref_{i}.png") for i, p in enumerate(ref_pils)],
            "n": n, "size": resolved_size, "quality": quality,
            "background": resolved_background, "output_format": output_format,
        }
        if mask is not None:
            kwargs["mask"] = image_io.mask_to_named_png(ref_pils[0], mask, "mask.png")
        if caps["input_fidelity"]:
            kwargs["input_fidelity"] = input_fidelity
        if moderation != "auto":
            kwargs["moderation"] = moderation
        resp = oai.images.edit(**kwargs)
        if not resp.data:
            return (image_io.empty_image(), _NO_IMAGES)
        info = getattr(resp.data[0], "revised_prompt", None) \
            or f"Edited image with {model}."
        return (image_io.batch_from_response_data(resp.data), info)
    except Exception as exc:  # noqa: BLE001 - node must not crash the queue
        log.exception("imagent: image edit failed")
        return (image_io.empty_image(), client_mod.friendly_error(exc))
