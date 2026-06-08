import base64
import io
import types
from pathlib import Path

from PIL import Image

import imagent.client as client
from imagent.build import run_generate, run_edit


def _b64(color=(1, 2, 3), size=(16, 16)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


class FakeImages:
    def __init__(self, recorder):
        self._rec = recorder

    def generate(self, **kwargs):
        self._rec["generate"] = kwargs
        item = types.SimpleNamespace(b64_json=_b64(), revised_prompt="a revised prompt")
        return types.SimpleNamespace(data=[item for _ in range(kwargs.get("n", 1))])

    def edit(self, **kwargs):
        self._rec["edit"] = kwargs
        item = types.SimpleNamespace(b64_json=_b64(), revised_prompt=None)
        return types.SimpleNamespace(data=[item for _ in range(kwargs.get("n", 1))])


class FakeClient:
    def __init__(self, recorder):
        self.images = FakeImages(recorder)


def test_generate_missing_key_returns_empty(monkeypatch):
    monkeypatch.setattr(client, "get_client", lambda: None)
    img, info = run_generate(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1)
    assert img.shape == (1, 512, 512, 3)
    assert info.startswith("Error")


def test_generate_sends_expected_params_and_decodes(monkeypatch):
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    img, info = run_generate(
        prompt="a cat", model="gpt-image-2", size="1024x1024", quality="high",
        background="opaque", output_format="png", n=2)
    sent = rec["generate"]
    assert sent["model"] == "gpt-image-2"
    assert sent["prompt"] == "a cat"
    assert sent["n"] == 2
    assert sent["size"] == "1024x1024"
    assert sent["quality"] == "high"
    assert sent["background"] == "opaque"
    assert img.shape[0] == 2
    assert info == "a revised prompt"


def test_generate_drops_transparent_background_for_gpt_image_2(monkeypatch):
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    run_generate(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="transparent", output_format="png", n=1)
    assert rec["generate"]["background"] == "auto"   # gpt-image-2 can't do transparent


def test_generate_keeps_transparent_background_for_gpt_image_1(monkeypatch):
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    run_generate(
        prompt="x", model="gpt-image-1", size="auto", quality="auto",
        background="transparent", output_format="png", n=1)
    assert rec["generate"]["background"] == "transparent"


def test_generate_adds_compression_only_for_jpeg(monkeypatch):
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    run_generate(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="jpeg", n=1, output_compression=80)
    assert rec["generate"]["output_compression"] == 80
    rec.clear()
    run_generate(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1, output_compression=80)
    assert "output_compression" not in rec["generate"]


def test_generate_moderation_only_when_not_auto(monkeypatch):
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    run_generate(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1, moderation="low")
    assert rec["generate"]["moderation"] == "low"
    rec.clear()
    run_generate(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1, moderation="auto")
    assert "moderation" not in rec["generate"]


def test_n_max_is_8():
    from imagent import params
    assert params.N_MAX == 8


def test_generate_api_error_returns_empty(monkeypatch):
    monkeypatch.setattr(client, "get_client", lambda: FakeClient({}))
    monkeypatch.setattr(
        FakeImages, "generate",
        lambda self, **kw: (_ for _ in ()).throw(RuntimeError("network error")))
    img, info = run_generate(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1)
    assert img.shape == (1, 512, 512, 3)
    assert info.startswith("Error")


def test_generate_invalid_custom_size_returns_error(monkeypatch):
    monkeypatch.setattr(client, "get_client", lambda: FakeClient({}))
    img, info = run_generate(
        prompt="x", model="gpt-image-2", size="custom", quality="auto",
        background="auto", output_format="png", n=1,
        custom_width=1000, custom_height=1000)   # 1000 is not a multiple of 16
    assert img.shape == (1, 512, 512, 3)
    assert info.startswith("Error")


def test_generate_custom_dimensions_for_gpt_image_2(monkeypatch):
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    run_generate(
        prompt="x", model="gpt-image-2", size="custom", quality="auto",
        background="auto", output_format="png", n=1,
        custom_width=2048, custom_height=1152)
    assert rec["generate"]["size"] == "2048x1152"


def test_generate_hires_preset_gated_to_gpt_image_2(monkeypatch):
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    run_generate(
        prompt="x", model="gpt-image-1", size="2048x2048", quality="auto",
        background="auto", output_format="png", n=1)
    assert rec["generate"]["size"] == "auto"          # gpt-image-1 can't do hi-res
    rec.clear()
    run_generate(
        prompt="x", model="gpt-image-2", size="2048x2048", quality="auto",
        background="auto", output_format="png", n=1)
    assert rec["generate"]["size"] == "2048x2048"


# ---------------------------------------------------------------------------
# OpenAIImageEdit tests
# ---------------------------------------------------------------------------
import torch


def _img_tensor(h=16, w=16):
    return torch.full((1, h, w, 3), 0.5, dtype=torch.float32)


def test_edit_sends_image_list_and_decodes(monkeypatch):
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    img, info = run_edit(
        prompt="make it snowy", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1,
        images=[_img_tensor(), _img_tensor()])
    sent = rec["edit"]
    assert sent["model"] == "gpt-image-2"
    assert isinstance(sent["image"], list) and len(sent["image"]) == 2
    assert "mask" not in sent
    assert img.shape[0] == 1


def test_edit_includes_mask_when_provided(monkeypatch):
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    mask = torch.zeros((16, 16), dtype=torch.float32)
    mask[0:8, 0:8] = 1.0
    run_edit(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1,
        images=[_img_tensor()], mask=mask)
    assert "mask" in rec["edit"]


def test_edit_input_fidelity_only_for_1x(monkeypatch):
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    run_edit(
        prompt="x", model="gpt-image-1", size="auto", quality="auto",
        background="auto", output_format="png", n=1,
        images=[_img_tensor()], input_fidelity="high")
    assert rec["edit"]["input_fidelity"] == "high"
    rec.clear()
    run_edit(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1,
        images=[_img_tensor()], input_fidelity="high")
    assert "input_fidelity" not in rec["edit"]


def test_edit_moderation_only_when_not_auto(monkeypatch):
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    run_edit(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1,
        images=[_img_tensor()], moderation="low")
    assert rec["edit"]["moderation"] == "low"
    rec.clear()
    run_edit(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1,
        images=[_img_tensor()], moderation="auto")
    assert "moderation" not in rec["edit"]


def test_edit_downscales_large_reference(monkeypatch):
    from imagent import image_io
    rec = {}
    monkeypatch.setattr(client, "get_client", lambda: FakeClient(rec))
    big = torch.full((1, 2100, 2100, 3), 0.5, dtype=torch.float32)
    run_edit(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1, images=[big])
    sent_img = rec["edit"]["image"][0]
    w, h = Image.open(sent_img).size
    assert w * h <= image_io.MAX_INPUT_PIXELS


def test_edit_missing_image_returns_error(monkeypatch):
    monkeypatch.setattr(client, "get_client", lambda: FakeClient({}))
    img, info = run_edit(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1, images=[])
    assert info.startswith("Error")
    assert img.shape == (1, 512, 512, 3)


def test_edit_api_error_returns_empty(monkeypatch):
    monkeypatch.setattr(client, "get_client", lambda: FakeClient({}))
    monkeypatch.setattr(
        FakeImages, "edit",
        lambda self, **kw: (_ for _ in ()).throw(RuntimeError("network error")))
    img, info = run_edit(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1, images=[_img_tensor()])
    assert img.shape == (1, 512, 512, 3)
    assert info.startswith("Error")


def test_edit_mask_with_multiple_refs_returns_error(monkeypatch):
    monkeypatch.setattr(client, "get_client", lambda: FakeClient({}))
    mask = torch.zeros((16, 16), dtype=torch.float32)
    img, info = run_edit(
        prompt="x", model="gpt-image-2", size="auto", quality="auto",
        background="auto", output_format="png", n=1,
        images=[_img_tensor(), _img_tensor()], mask=mask)
    assert img.shape == (1, 512, 512, 3)
    assert info.startswith("Error")


def test_extension_registers_both_nodes():
    # Registration uses the comfy_api V3 entrypoint, so this needs ComfyUI present.
    import pytest
    pytest.importorskip("comfy_api")
    import asyncio
    import importlib.util
    root = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location("imagent_root_init", root / "__init__.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    nodes = asyncio.run(mod.ImagentExtension().get_node_list())
    schemas = {n.define_schema().node_id: n.define_schema().display_name for n in nodes}
    assert set(schemas) == {"ImagentOpenAIImage", "ImagentOpenAIImageEdit"}
    assert schemas["ImagentOpenAIImage"] == "🤖 Imagent: OpenAI Image"
    assert schemas["ImagentOpenAIImageEdit"] == "🤖 Imagent: OpenAI Image Edit"
