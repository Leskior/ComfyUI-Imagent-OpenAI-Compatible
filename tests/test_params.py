import pytest
from imagent import params


def test_constants():
    assert params.SIZE_PRESETS[0] == "auto"
    assert "custom" in params.SIZE_PRESETS
    assert params.SIZE_PRESETS[-1] == "custom"
    for base in ("1024x1024", "1024x1536", "1536x1024"):
        assert base in params.SIZE_PRESETS
    for hires in ("2048x2048", "3840x2160", "2160x3840"):
        assert hires in params.SIZE_PRESETS
    assert (params.CUSTOM_DIM_MIN, params.CUSTOM_DIM_MAX, params.CUSTOM_DIM_STEP) == (1024, 3840, 16)
    assert params.QUALITIES == ["auto", "low", "medium", "high"]
    assert params.BACKGROUNDS == ["auto", "opaque", "transparent"]
    assert params.FORMATS == ["png", "jpeg", "webp"]
    assert params.MODERATIONS == ["auto", "low"]


def test_capabilities_for_known_and_unknown():
    assert params.capabilities_for("gpt-image-2")["custom_size"] is True
    assert params.capabilities_for("gpt-image-2")["input_fidelity"] is False
    assert params.capabilities_for("gpt-image-2")["transparent_background"] is False
    assert params.capabilities_for("gpt-image-1")["input_fidelity"] is True
    assert params.capabilities_for("gpt-image-1")["custom_size"] is False
    assert params.capabilities_for("gpt-image-1")["transparent_background"] is True
    assert params.capabilities_for("gpt-image-1.5")["transparent_background"] is True
    assert params.capabilities_for("mystery") == {
        "custom_size": False, "input_fidelity": False, "transparent_background": False}


def test_resolve_background_drops_transparent_for_gpt_image_2():
    assert params.resolve_background("transparent", "gpt-image-2") == "auto"
    assert params.resolve_background("opaque", "gpt-image-2") == "opaque"
    assert params.resolve_background("auto", "gpt-image-2") == "auto"


def test_resolve_background_keeps_transparent_for_gpt_image_1x():
    assert params.resolve_background("transparent", "gpt-image-1") == "transparent"
    assert params.resolve_background("transparent", "gpt-image-1.5") == "transparent"


def test_validate_custom_dimensions_ok():
    assert params.validate_custom_dimensions(1536, 864) == "1536x864"
    assert params.validate_custom_dimensions(2048, 1152) == "2048x1152"


@pytest.mark.parametrize("w,h", [
    (1000, 1000),   # not multiples of 16
    (100, 100),     # not multiples of 16 (and too small)
    (-16, -16),     # negative
    (1024, 0),      # zero
    (1024, 512),    # total 524,288 < 655,360 minimum
    (3840, 2176),   # total 8,355,840 > 8,294,400 maximum
    (3840, 1024),   # aspect 3.75:1 > 3:1
    (4096, 2160),   # max edge 4096 > 3840
])
def test_validate_custom_dimensions_rejects(w, h):
    with pytest.raises(ValueError):
        params.validate_custom_dimensions(w, h)


def test_resolve_size_passthrough_for_base_presets():
    assert params.resolve_size("1024x1024", 1024, 1024, "gpt-image-2") == "1024x1024"
    assert params.resolve_size("auto", 1024, 1024, "gpt-image-1") == "auto"


def test_resolve_size_custom_requires_capability():
    assert params.resolve_size("custom", 1536, 864, "gpt-image-2") == "1536x864"
    assert params.resolve_size("custom", 1536, 864, "gpt-image-1") == "auto"


def test_resolve_size_hires_presets_gated_to_gpt_image_2():
    assert params.resolve_size("2048x2048", 1024, 1024, "gpt-image-2") == "2048x2048"
    assert params.resolve_size("3840x2160", 1024, 1024, "gpt-image-2") == "3840x2160"
    assert params.resolve_size("2048x2048", 1024, 1024, "gpt-image-1") == "auto"
    assert params.resolve_size("3840x2160", 1024, 1024, "gpt-image-1.5") == "auto"
