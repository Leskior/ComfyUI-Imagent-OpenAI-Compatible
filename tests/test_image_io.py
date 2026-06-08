from __future__ import annotations

import base64
import io
import types
import numpy as np
import torch
from PIL import Image
from imagent import image_io


def _png_b64(color=(10, 20, 30), size=(32, 48)):
    img = Image.new("RGB", size, color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def test_pil_to_tensor_shape_and_range():
    t = image_io.pil_to_tensor(Image.new("RGB", (8, 4), (255, 0, 0)))
    assert t.shape == (1, 4, 8, 3)        # [B, H, W, C]
    assert t.dtype == torch.float32
    assert 0.0 <= float(t.min()) and float(t.max()) <= 1.0
    assert abs(float(t[0, 0, 0, 0]) - 1.0) < 1e-6   # red channel


def test_b64_to_tensor_roundtrip():
    t = image_io.b64_to_tensor(_png_b64(size=(32, 48)))
    assert t.shape == (1, 48, 32, 3)


def test_empty_image_is_black_rgb():
    e = image_io.empty_image(64, 80)
    assert e.shape == (1, 64, 80, 3)
    assert float(e.abs().sum()) == 0.0


def test_tensor_to_pil_returns_one_per_batch():
    t = torch.zeros((2, 4, 8, 3), dtype=torch.float32)
    pils = image_io.tensor_to_pil(t)
    assert len(pils) == 2
    assert pils[0].size == (8, 4)         # PIL size is (W, H)
    mid = image_io.tensor_to_pil(torch.full((1, 2, 2, 3), 0.5, dtype=torch.float32))[0]
    assert int(np.array(mid)[0, 0, 0]) == 127      # 0.5 * 255 -> 127


def test_mask_selected_region_becomes_transparent():
    source = Image.new("RGB", (4, 4), (255, 255, 255))
    mask = torch.zeros((4, 4), dtype=torch.float32)
    mask[0:2, 0:2] = 1.0
    png_bytes = image_io.mask_to_alpha_png_bytes(source, mask)
    out = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    alpha = np.array(out)[:, :, 3]
    assert alpha[0, 0] == 0               # selected -> transparent (editable)
    assert alpha[3, 3] == 255             # unselected -> opaque (preserved)


def test_downscale_pil_to_pixel_limit_shrinks_large_image():
    big = Image.new("RGB", (4000, 4000), (5, 5, 5))
    out = image_io.downscale_pil_to_pixel_limit(big, max_pixels=1_000_000)
    w, h = out.size
    assert w * h <= 1_000_000
    assert abs((w / h) - 1.0) < 0.05          # aspect ratio preserved


def test_downscale_pil_to_pixel_limit_keeps_small_image():
    small = Image.new("RGB", (64, 48), (5, 5, 5))
    out = image_io.downscale_pil_to_pixel_limit(small, max_pixels=1_000_000)
    assert out.size == (64, 48)               # unchanged


def test_response_item_to_tensor_handles_b64():
    item = types.SimpleNamespace(b64_json=_png_b64(size=(20, 10)), url=None)
    t = image_io.response_item_to_tensor(item)
    assert t.shape == (1, 10, 20, 3)


def test_response_item_to_tensor_handles_url(monkeypatch):
    png = base64.b64decode(_png_b64(size=(12, 6)))

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return png

    monkeypatch.setattr("urllib.request.urlopen", lambda url, **kw: _FakeResp())
    item = types.SimpleNamespace(b64_json=None, url="http://example/x.png")
    t = image_io.response_item_to_tensor(item)
    assert t.shape == (1, 6, 12, 3)


def test_batch_from_response_data_concatenates_b64_items():
    data = [types.SimpleNamespace(b64_json=_png_b64(), url=None) for _ in range(3)]
    batch = image_io.batch_from_response_data(data)
    assert batch.shape[0] == 3


def test_response_item_to_tensor_raises_without_payload():
    import pytest
    item = types.SimpleNamespace(b64_json=None, url=None)
    with pytest.raises(ValueError):
        image_io.response_item_to_tensor(item)


def test_mask_3d_shape_is_handled():
    source = Image.new("RGB", (4, 4), (255, 255, 255))
    mask = torch.zeros((1, 4, 4), dtype=torch.float32)   # leading batch dim
    mask[0, 0:2, 0:2] = 1.0
    png_bytes = image_io.mask_to_alpha_png_bytes(source, mask)
    out = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    alpha = np.array(out)[:, :, 3]
    assert alpha[0, 0] == 0
    assert alpha[3, 3] == 255


def test_batch_from_response_data_rejects_empty():
    import pytest
    with pytest.raises(ValueError):
        image_io.batch_from_response_data([])


def test_mask_to_named_png_returns_named_filelike():
    src = Image.new("RGB", (8, 8), (200, 200, 200))
    mask = torch.zeros((8, 8), dtype=torch.float32)
    mask[0:4, :] = 1.0
    f = image_io.mask_to_named_png(src, mask, "mask.png")
    assert f.name == "mask.png"
    out = Image.open(f).convert("RGBA")
    assert out.size == (8, 8)
