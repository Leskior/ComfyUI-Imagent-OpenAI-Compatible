"""Every node input (including per-model DynamicCombo sub-inputs) carries a tooltip.

The nodes are declared with the comfy_api IO schema, so this test needs ComfyUI
present; it is skipped when comfy_api is unavailable (e.g. the bare dev venv) and
runs inside the ComfyUI container during smoke testing.
"""
from __future__ import annotations

import pytest

pytest.importorskip("comfy_api")

from imagent.node_edit import OpenAIImageEdit  # noqa: E402
from imagent.node_generate import OpenAIImageGenerate  # noqa: E402


def _walk(inp, where):
    """Assert this input has a tooltip, recursing into (nested) DynamicCombo options."""
    assert getattr(inp, "tooltip", None) and inp.tooltip.strip(), f"{where}.{inp.id} has no tooltip"
    opts = getattr(inp, "options", None)
    if opts and hasattr(opts[0], "inputs"):              # DynamicCombo (possibly nested)
        for opt in opts:
            for sub in opt.inputs:
                _walk(sub, f"{where}.{inp.id}[{opt.key}]")


@pytest.mark.parametrize("node", [OpenAIImageGenerate, OpenAIImageEdit])
def test_every_input_has_a_tooltip(node):
    for inp in node.define_schema().inputs:
        _walk(inp, node.__name__)
