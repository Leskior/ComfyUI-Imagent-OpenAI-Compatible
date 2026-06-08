"""Conversions between ComfyUI tensors, PIL images, masks, and base64 payloads.

Public helpers: pil_to_tensor, tensor_to_pil, b64_to_tensor, empty_image,
pil_to_png_bytes, mask_to_alpha_png_bytes, mask_to_named_png,
downscale_pil_to_pixel_limit, url_to_tensor, response_item_to_tensor,
batch_from_response_data.
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


def b64_to_tensor(b64_str: str) -> torch.Tensor:
    """Base64 PNG/JPEG/WebP -> [1, H, W, 3] float32 tensor."""
    data = base64.b64decode(b64_str)
    pil = Image.open(io.BytesIO(data))
    return pil_to_tensor(pil)


def empty_image(height: int = 512, width: int = 512) -> torch.Tensor:
    """Black RGB placeholder tensor for error returns."""
    return torch.zeros((1, height, width, 3), dtype=torch.float32)


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


def url_to_tensor(url: str) -> torch.Tensor:
    """Download an image URL and convert it to a [1, H, W, 3] tensor."""
    import urllib.request
    with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310 - caller owns URL provenance
        data = resp.read()
    return pil_to_tensor(Image.open(io.BytesIO(data)))


def response_item_to_tensor(item) -> torch.Tensor:
    """Convert an OpenAI image response item (b64_json or url) to a tensor."""
    b64 = getattr(item, "b64_json", None)
    if b64:
        return b64_to_tensor(b64)
    url = getattr(item, "url", None)
    if url:
        return url_to_tensor(url)
    raise ValueError("response item has neither b64_json nor url")


def batch_from_response_data(data: list) -> torch.Tensor:
    """OpenAI response `.data` list -> [B, H, W, 3] batch tensor (b64 or url items)."""
    if not data:
        raise ValueError("data must contain at least one response item")
    return torch.cat([response_item_to_tensor(d) for d in data], dim=0)
