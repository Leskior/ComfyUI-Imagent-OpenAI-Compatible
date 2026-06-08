"""ComfyUI-Imagent: OpenAI gpt-image generation and editing nodes.

The nodes use the comfy_api IO schema (DynamicCombo for per-model widgets), so we
register them via the V3 `comfy_entrypoint`/ComfyExtension path. Requires
ComfyUI >= 0.23.0 (for IO.DynamicCombo).
"""
import os
import sys

# ComfyUI loads this __init__.py via importlib.util.spec_from_file_location,
# which does NOT add the custom-node directory to sys.path. Add it so that
# `import imagent.*` resolves whether installed editable or bind-mounted.
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

# The nodes use the comfy_api IO schema, which only exists inside ComfyUI. Guard
# the import so the package root still imports cleanly without ComfyUI (e.g. the
# dev venv / test collection); ComfyUI itself always provides comfy_api.
try:
    from comfy_api.latest import ComfyExtension, IO  # noqa: E402
except ModuleNotFoundError:
    ComfyExtension = None
else:
    from imagent.node_edit import OpenAIImageEdit  # noqa: E402
    from imagent.node_generate import OpenAIImageGenerate  # noqa: E402

    class ImagentExtension(ComfyExtension):
        async def get_node_list(self) -> list[type[IO.ComfyNode]]:
            return [OpenAIImageGenerate, OpenAIImageEdit]

    async def comfy_entrypoint() -> ImagentExtension:
        return ImagentExtension()
