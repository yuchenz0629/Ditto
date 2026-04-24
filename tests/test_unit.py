import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from llm_utils import extract_json
from models import (
    PosterState, SelectedImage, AvailableImage, RejectedImage,
    SwapImageCommand, RemoveImageCommand, ChangeBackgroundCommand,
    AdjustLayoutCommand, ResizePhotoCommand,
)
from editor import _apply
from metadata_parser import _extract_field


def _make_state(**overrides) -> PosterState:
    defaults: dict = dict(
        user="test",
        user_dir="/tmp",
        name="Test User",
        gender="female",
        selected_images=[
            SelectedImage(index=0, filename="a.jpg", role="lifestyle", position=1),
            SelectedImage(index=1, filename="b.jpg", role="hero", position=2),
        ],
        available_images=[
            AvailableImage(index=2, filename="c.jpg"),
        ],
        rejected_images=[],
        background="Forest Green",
        layout="2-image",
    )
    defaults.update(overrides)
    return PosterState(**defaults)


def test_extract_json_fenced():
    text = '```json\n{"key": "value"}\n```'
    assert extract_json(text) == '{"key": "value"}'


def test_extract_json_bare():
    text = 'Some preamble {"key": "value"} some suffix'
    assert extract_json(text) == '{"key": "value"}'


def test_apply_swap_with_available():
    state = _make_state()
    cmd = SwapImageCommand(action="swap_image", target_position=1, new_image_index=2, reason="test")
    result = _apply(state, cmd)
    indices = {img.index for img in result.selected_images}
    assert 2 in indices
    assert 0 not in indices
    assert any(img.index == 2 and img.position == 1 for img in result.selected_images)
    assert any(img.index == 0 for img in result.available_images)


def test_apply_swap_between_selected():
    # target_position=1 (index 0) swapped with index 1 (currently at position 2) → exchange positions
    state = _make_state()
    cmd = SwapImageCommand(action="swap_image", target_position=1, new_image_index=1, reason="test")
    result = _apply(state, cmd)
    assert any(img.index == 1 and img.position == 1 for img in result.selected_images)
    assert any(img.index == 0 and img.position == 2 for img in result.selected_images)


def test_apply_swap_self_is_noop():
    state = _make_state()
    cmd = SwapImageCommand(action="swap_image", target_position=1, new_image_index=0, reason="test")
    result = _apply(state, cmd)
    assert any(img.index == 0 and img.position == 1 for img in result.selected_images)


def test_apply_remove_last_image_raises():
    state = _make_state(
        selected_images=[SelectedImage(index=0, filename="a.jpg", role="hero", position=1)],
        available_images=[],
        layout="1-image",
    )
    cmd = RemoveImageCommand(action="remove_image", target_position=1, reason="test")
    with pytest.raises(ValueError, match="last image"):
        _apply(state, cmd)


def test_apply_remove_moves_to_available():
    state = _make_state()
    cmd = RemoveImageCommand(action="remove_image", target_position=1, reason="test")
    result = _apply(state, cmd)
    assert len(result.selected_images) == 1
    assert result.layout == "1-image"
    assert any(img.index == 0 for img in result.available_images)


def test_apply_change_background():
    state = _make_state()
    cmd = ChangeBackgroundCommand(action="change_background", new_background="Serene Blue", reason="test")
    result = _apply(state, cmd)
    assert result.background == "Serene Blue"


def test_apply_resize_clamped_upper():
    state = _make_state()
    cmd = ResizePhotoCommand(action="resize_photo", scale=2.0, reason="test")
    result = _apply(state, cmd)
    assert result.hero_scale == 1.3


def test_apply_resize_clamped_lower():
    state = _make_state()
    cmd = ResizePhotoCommand(action="resize_photo", scale=0.1, reason="test")
    result = _apply(state, cmd)
    assert result.hero_scale == 0.7


def test_apply_resize_within_range():
    state = _make_state()
    cmd = ResizePhotoCommand(action="resize_photo", scale=1.1, reason="test")
    result = _apply(state, cmd)
    assert abs(result.hero_scale - 1.1) < 1e-9


def test_extract_field_present():
    text = "name\nAlice\ngender\nfemale\n"
    assert _extract_field(text, "name") == "Alice"
    assert _extract_field(text, "gender") == "female"


def test_extract_field_missing():
    text = "name\nAlice\ngender\n"
    assert _extract_field(text, "gender") == ""


def test_extract_field_nonexistent():
    text = "name\nAlice\n"
    assert _extract_field(text, "ethnicity") == ""
