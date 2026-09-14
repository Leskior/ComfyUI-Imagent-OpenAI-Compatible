"""ComfyUI node: image edit / inpaint via OpenAI images.edit.

Like node_generate, `model` is a DynamicCombo with a nested size combo. Reference
images use an auto-growing input (up to 16). Behavior lives in build.run_edit().
"""
from __future__ import annotations

from comfy_api.latest import IO

from . import build
from . import params as params_mod
from .node_generate import _gpt_image_2_inputs, _gpt_image_25_inputs, unpack_size

_MAX_REFS = 16


class OpenAIImageEdit(IO.ComfyNode):
    @classmethod
    def define_schema(cls):
        return IO.Schema(
            node_id="ImagentOpenAIImageEdit",
            display_name="🤖 Imagent: OpenAI Image Edit",
            category="Imagent",
            description="BYOK image edit / inpaint / multi-reference compose via OpenAI "
                        "gpt-image models (direct API, no proxy).",
            inputs=[
                IO.String.Input("prompt", multiline=True, default="",
                                placeholder="Describe the edit to apply…",
                                tooltip="Describe the edit to apply to the reference image(s)."),
                IO.DynamicCombo.Input(
                    "model",
                    tooltip="OpenAI gpt-image model. Switching this changes the options below.",
                    options=[
                        IO.DynamicCombo.Option("gpt-image-2.5-flare", _gpt_image_25_inputs()),
                        IO.DynamicCombo.Option("gpt-image-2.5-sunburst", _gpt_image_25_inputs()),
                        IO.DynamicCombo.Option("gpt-image-2", _gpt_image_2_inputs()),
                    ],
                ),
                IO.Autogrow.Input(
                    "images",
                    template=IO.Autogrow.TemplateNames(
                        IO.Image.Input("image"),
                        names=[f"image_{i}" for i in range(1, _MAX_REFS + 1)],
                        min=1),
                    tooltip=f"Reference image(s) to edit; grows up to {_MAX_REFS}. A mask "
                    "(if used) applies to the first image and requires exactly one image."),
                IO.Combo.Input("quality", options=params_mod.QUALITIES, default="auto",
                               tooltip="Rendering quality. 'auto' lets the model decide; "
                               "higher quality costs more. 'xhigh' and 'max' need "
                               "gpt-image-2.5 and fall back to 'high' elsewhere."),
                IO.Combo.Input("output_format", options=params_mod.FORMATS, default="png",
                               tooltip="Image file format returned by the API."),
                IO.Combo.Input("moderation", options=params_mod.MODERATIONS, default="auto",
                               tooltip="Content moderation strictness. 'auto' (default) or "
                               "'low'. Sent only when not 'auto'."),
                IO.Int.Input("n", default=1, min=params_mod.N_MIN, max=params_mod.N_MAX, step=1,
                             tooltip="How many images to generate (1-8)."),
                IO.Mask.Input("mask", optional=True,
                              tooltip="Inpaint mask: white marks the region to edit. Requires a "
                              "single reference image."),
            ],
            outputs=[IO.Image.Output(display_name="image"),
                     IO.Mask.Output(display_name="mask")],
        )

    @classmethod
    def execute(cls, prompt, model, images, quality, output_format, moderation, n,
                mask=None) -> IO.NodeOutput:
        size, custom_width, custom_height = unpack_size(model)
        ref_tensors = [t for t in (images or {}).values() if t is not None]
        img, out_mask, _info = build.run_edit(
            prompt=prompt, model=model["model"], size=size, quality=quality,
            background=model["background"], output_format=output_format, n=n,
            images=ref_tensors, mask=mask, moderation=moderation,
            custom_width=custom_width, custom_height=custom_height)
        return IO.NodeOutput(img, out_mask)
