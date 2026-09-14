"""Conversions between ComfyUI tensors, PIL images, masks, and base64 payloads.

Public helpers: pil_to_tensor, pil_to_image_and_mask, tensor_to_pil, empty_image,
empty_mask, pil_to_png_bytes, mask_to_alpha_png_bytes, mask_to_named_png,
downscale_pil_to_pixel_limit, response_item_to_pil, batch_from_response_data.
"""
from __future__ import annotations

import base64
import io

import numpy as np
import torch
from PIL import Image


def pil_to_tensor(pil_image: Image.Image) -> torch.Tensor:
    """PIL image -> ComfyUI IMAGE tensor [1, H, W, 3] float32 in 0..1 (RGB)."""
    img = pil_image.convert("RGB")
    arr = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr)[None, ]


def tensor_to_pil(image_tensor: torch.Tensor) -> list[Image.Image]:
    """ComfyUI IMAGE tensor [B, H, W, C] -> list of PIL images (one per batch item)."""
    arr = image_tensor.detach().cpu().numpy()
    out: list[Image.Image] = []
    for i in range(arr.shape[0]):
        a = (np.clip(arr[i], 0.0, 1.0) * 255).astype(np.uint8)
        mode = "RGBA" if a.shape[-1] == 4 else "RGB"
        out.append(Image.fromarray(a, mode))
    return out


def pil_to_image_and_mask(pil_image: Image.Image) -> tuple[torch.Tensor, torch.Tensor]:
    """PIL image -> (IMAGE [1, H, W, 3], MASK [1, H, W]).

    Alpha is carried out as a MASK because ComfyUI IMAGE is RGB-only: following
    the LoadImage convention, mask = 1 - alpha, so a transparent region reads as
    selected (1.0). Images without an alpha channel yield an all-zero mask.
    """
    if "A" in pil_image.getbands():
        alpha = np.array(pil_image.getchannel("A")).astype(np.float32) / 255.0
        mask = 1.0 - torch.from_numpy(alpha)[None, ]
    else:
        mask = empty_mask(pil_image.height, pil_image.width)
    return pil_to_tensor(pil_image), mask


def empty_image(height: int = 512, width: int = 512) -> torch.Tensor:
    """Black RGB placeholder tensor for error returns."""
    return torch.zeros((1, height, width, 3), dtype=torch.float32)


def empty_mask(height: int = 512, width: int = 512) -> torch.Tensor:
    """All-zero (fully opaque) MASK tensor."""
    return torch.zeros((1, height, width), dtype=torch.float32)


def pil_to_png_bytes(pil_image: Image.Image) -> bytes:
    """PIL image -> PNG bytes."""
    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    return buf.getvalue()


def mask_to_alpha_png_bytes(source_pil: Image.Image, mask_tensor: torch.Tensor) -> bytes:
    """Build an RGBA PNG where the mask-selected region is transparent.

    ComfyUI MASK convention: 1.0 = selected. OpenAI edits the *transparent*
    region, so selected (1.0) maps to alpha 0. The mask is resized to the
    source image dimensions.
    """
    m = mask_tensor
    if m.dim() == 3:
        m = m[0]
    m_np = np.clip(m.detach().cpu().numpy(), 0.0, 1.0)
    mask_pil = Image.fromarray((m_np * 255).astype(np.uint8), "L").resize(source_pil.size)
    mask_resized = np.array(mask_pil).astype(np.float32) / 255.0
    alpha = ((1.0 - mask_resized) * 255).astype(np.uint8)   # selected -> 0 (editable)
    rgba = source_pil.convert("RGBA")
    rgba.putalpha(Image.fromarray(alpha, "L"))
    return pil_to_png_bytes(rgba)


def mask_to_named_png(source_pil: Image.Image, mask_tensor: torch.Tensor, name: str) -> io.BytesIO:
    """mask_to_alpha_png_bytes wrapped as a named BytesIO for the OpenAI SDK."""
    buf = io.BytesIO(mask_to_alpha_png_bytes(source_pil, mask_tensor))
    buf.name = name
    return buf


# Default budget for downscaling reference images before upload (2048*2048).
MAX_INPUT_PIXELS = 4_194_304


def downscale_pil_to_pixel_limit(pil_image: Image.Image,
                                 max_pixels: int = MAX_INPUT_PIXELS) -> Image.Image:
    """Downscale a PIL image so total pixels <= max_pixels, preserving aspect ratio.

    Returns the original image unchanged when it already fits. Mirrors the
    built-in ComfyUI node's downscale_image_tensor robustness.
    """
    w, h = pil_image.size
    if w * h <= max_pixels:
        return pil_image
    scale = (max_pixels / float(w * h)) ** 0.5
    return pil_image.resize((max(1, int(w * scale)), max(1, int(h * scale))))


def response_item_to_pil(item) -> Image.Image:
    """Decode an OpenAI image response item (b64_json or url) to a PIL image."""
    b64 = getattr(item, "b64_json", None)
    if b64:
        return Image.open(io.BytesIO(base64.b64decode(b64)))
    url = getattr(item, "url", None)
    if url:
        import urllib.request
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 - caller owns URL provenance
            return Image.open(io.BytesIO(resp.read()))
    raise ValueError("response item has neither b64_json nor url")


def batch_from_response_data(data: list) -> tuple[torch.Tensor, torch.Tensor]:
    """OpenAI response `.data` list -> ([B, H, W, 3] IMAGE, [B, H, W] MASK) batches."""
    if not data:
        raise ValueError("data must contain at least one response item")
    pairs = [pil_to_image_and_mask(response_item_to_pil(d)) for d in data]
    return (torch.cat([img for img, _ in pairs], dim=0),
            torch.cat([mask for _, mask in pairs], dim=0))
