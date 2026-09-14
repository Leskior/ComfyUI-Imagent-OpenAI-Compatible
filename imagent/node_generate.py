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
            description="BYOK text-to-image via OpenAI gpt-image models (direct API, no proxy).",
            inputs=[
                IO.String.Input("prompt", multiline=True, default="",
                                placeholder="Describe the image to generate…",
                                tooltip="Text description of the image to generate."),
                IO.DynamicCombo.Input(
                    "model",
                    tooltip="OpenAI gpt-image model. Switching this changes the options below.",
                    options=[
                        IO.DynamicCombo.Option("gpt-image-2.5-flare", _gpt_image_25_inputs()),
                        IO.DynamicCombo.Option("gpt-image-2.5-sunburst", _gpt_image_25_inputs()),
                        IO.DynamicCombo.Option("gpt-image-2", _gpt_image_2_inputs()),
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
            ],
            outputs=[IO.Image.Output(display_name="image")],
        )

    @classmethod
    def execute(cls, prompt, model, quality, output_format, output_compression,
                moderation, n) -> IO.NodeOutput:
        size, custom_width, custom_height = unpack_size(model)
        img, _info = build.run_generate(
            prompt=prompt, model=model["model"], size=size, quality=quality,
            background=model["background"], output_format=output_format, n=n,
            moderation=moderation, custom_width=custom_width, custom_height=custom_height,
            output_compression=output_compression)
        return IO.NodeOutput(img)
