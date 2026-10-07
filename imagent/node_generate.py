"""ComfyUI node: text-to-image via OpenAI images.generate.

Declared with the comfy_api IO schema. `model` is a DynamicCombo (switching the
model swaps the size/background widgets). Within gpt-image-2, `size` is itself a
nested DynamicCombo so custom_width/height appear only under size='custom'. All
behavior lives in the import-clean build.run_generate(); this file is a thin
schema + marshaling wrapper (so it requires ComfyUI to import).
"""
from __future__ import annotations

from comfy_api.latest import IO

from . import build
from . import params as params_mod


def _custom_dim(name: str, axis: str):
    return IO.Int.Input(name, default=1024, min=params_mod.CUSTOM_DIM_MIN,
                        max=params_mod.CUSTOM_DIM_MAX, step=params_mod.CUSTOM_DIM_STEP,
                        tooltip=f"Used when size = custom. Multiple of 16; with {axis}: "
                        "aspect <= 3:1 and total pixels 655,360-8,294,400.")


def _size_combo_gpt2():
    """gpt-image-2 size as a nested DynamicCombo: width/height appear only for 'custom'."""
    options = [IO.DynamicCombo.Option(s, []) for s in params_mod.SIZES_GPT2 if s != "custom"]
    options.append(IO.DynamicCombo.Option(
        "custom", [_custom_dim("custom_width", "height"), _custom_dim("custom_height", "width")]))
    return IO.DynamicCombo.Input(
        "size", tooltip="Output size. Choose 'custom' to set an exact width and height.",
        options=options)


def _gpt_image_2_inputs():
    """Per-model widgets for gpt-image-2: hi-res/custom sizes, opaque/auto background."""
    return [
        _size_combo_gpt2(),
        IO.Combo.Input("background", options=params_mod.BACKGROUNDS_GPT2, default="auto",
                       tooltip="Background handling. gpt-image-2 does not support transparent."),
    ]


def _gpt_image_25_inputs():
    """Per-model widgets for gpt-image-2.5: hi-res/custom sizes, transparent allowed."""
    return [
        _size_combo_gpt2(),
        IO.Combo.Input("background", options=params_mod.BACKGROUNDS, default="auto",
                       tooltip="Background handling. 'transparent' needs png or webp output."),
    ]


def _custom_model_inputs():
    """Widgets for the 'custom' selector: a free-form model id plus the usual controls.

    An endpoint's capabilities are unknown, so quality/background are not narrowed
    and the request goes out as configured. `size` keeps the gpt-image list and
    WxH rules, because the widget still has to offer something.
    """
    return [
        IO.String.Input("model_name", default="",
                        tooltip="Model id sent to the endpoint, e.g. 'flux-1.1-pro'. "
                                "Required when model = custom."),
        _size_combo_gpt2(),
        IO.Combo.Input("background", options=params_mod.BACKGROUNDS, default="auto",
                       tooltip="Background handling, sent as-is for a custom model. "
                               "'transparent' only works if the endpoint supports it."),
    ]


def _base_url_input():
    return IO.String.Input(
        "base_url", default="", optional=True,
        tooltip="Optional. Overrides OPENAI_BASE_URL / config.json for this node. Set it to "
                "any OpenAI-compatible endpoint, e.g. https://host/v1. Blank falls back to "
                "the env var, then config.json, then https://api.openai.com/v1.")


def _api_key_input():
    return IO.String.Input(
        "api_key", default="", optional=True,
        tooltip="Optional. Overrides OPENAI_API_KEY / config.json for this node. Prefer the "
                "env var or config.json — a key typed here is saved in the workflow file, "
                "so it travels with any workflow you share.")


def unpack_size(model: dict):
    """Pull (size, custom_width, custom_height) from a model dict.

    `size` is itself a nested DynamicCombo, so it arrives as a dict.
    """
    sz = model["size"]
    return sz["size"], sz.get("custom_width", 1024), sz.get("custom_height", 1024)


class OpenAIImageGenerate(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="ImagentOpenAIImage",
            display_name="🤖 Imagent: OpenAI Image",
            category="Imagent",
            description="BYOK text-to-image via OpenAI gpt-image models or any "
                        "OpenAI-compatible endpoint (direct API, no proxy).",
            inputs=[
                IO.String.Input("prompt", multiline=True, default="",
                                placeholder="Describe the image to generate…",
                                tooltip="Text description of the image to generate."),
                IO.DynamicCombo.Input(
                    "model",
                    tooltip="OpenAI gpt-image model, or 'custom' to send any model id to an "
                            "OpenAI-compatible endpoint. Switching this changes the options "
                            "below.",
                    options=[
                        IO.DynamicCombo.Option("gpt-image-2.5-flare", _gpt_image_25_inputs()),
                        IO.DynamicCombo.Option("gpt-image-2.5-sunburst", _gpt_image_25_inputs()),
                        IO.DynamicCombo.Option("gpt-image-2", _gpt_image_2_inputs()),
                        IO.DynamicCombo.Option(params_mod.CUSTOM_MODEL, _custom_model_inputs()),
                    ],
                ),
                IO.Combo.Input("quality", options=params_mod.QUALITIES, default="auto",
                               tooltip="Rendering quality. 'auto' lets the model decide; "
                               "higher quality costs more. 'xhigh' and 'max' need "
                               "gpt-image-2.5 and fall back to 'high' elsewhere."),
                IO.Combo.Input("output_format", options=params_mod.FORMATS, default="png",
                               tooltip="Image file format returned by the API."),
                IO.Int.Input("output_compression", default=100, min=0, max=100,
                             tooltip="Compression 0-100. Applies only to jpeg and webp output."),
                IO.Combo.Input("moderation", options=params_mod.MODERATIONS, default="auto",
                               tooltip="Content moderation strictness. 'auto' (default) or "
                               "'low' (less restrictive). Sent only when not 'auto'."),
                IO.Int.Input("n", default=1, min=params_mod.N_MIN, max=params_mod.N_MAX, step=1,
                             tooltip="How many images to generate (1-8)."),
                _base_url_input(),
                _api_key_input(),
            ],
            outputs=[IO.Image.Output(display_name="image"),
                     IO.Mask.Output(display_name="mask")],
        )

    @classmethod
    def execute(cls, prompt, model, quality, output_format, output_compression,
                moderation, n, base_url="", api_key="") -> IO.NodeOutput:
        size, custom_width, custom_height = unpack_size(model)
        img, mask, _info = build.run_generate(
            prompt=prompt, model=model["model"], model_name=model.get("model_name", ""),
            size=size, quality=quality,
            background=model["background"], output_format=output_format, n=n,
            moderation=moderation, custom_width=custom_width, custom_height=custom_height,
            output_compression=output_compression, api_key=api_key, base_url=base_url)
        return IO.NodeOutput(img, mask)
