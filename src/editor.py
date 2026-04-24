import json
import logging
import re
from pathlib import Path
from pydantic import TypeAdapter
from models import (
    PosterState, EditCommand,
    SwapImageCommand, RemoveImageCommand, ChangeBackgroundCommand, AdjustLayoutCommand,
    ResizePhotoCommand,
    SelectedImage, AvailableImage,
)
import anthropic
from anthropic.types import Message, TextBlock
from typing import Literal

LayoutName = Literal[
    "1-image", "2-image", "3-image", "4-image",
    "2-image-v2", "3-image-v2", "4-image-v2",
]

_LAYOUT_BY_COUNT: dict[int, LayoutName] = {
    1: "1-image",
    2: "2-image",
    3: "3-image",
    4: "4-image",
}

log = logging.getLogger(__name__)
MODEL = "claude-sonnet-4-6"
_adapter = TypeAdapter(EditCommand)

SYSTEM = """\
You are a poster editing assistant for a dating app. Interpret the instruction and return a
single structured edit command. Output ONLY valid JSON. No commentary, no markdown fences.

Supported actions:
  swap_image        → replace the photo at target_position with any other photo by index.
                      new_image_index may be from available_images OR from selected_images
                      (swapping two already-placed photos exchanges their positions and importance).
  remove_image      → remove a photo (layout count decreases by 1)
  change_background → switch background
  adjust_layout     → change layout variant (count or arrangement)
  resize_photo      → scale the hero photo up or down

Ambiguity rules:
  "main photo" / "hero" / "front" / "bottom" → highest position number in selected_images
  "top photo" / "small photo" / "back"        → position 1 (lowest importance)
  "brighter background"                        → background with warm or light color_tone
  "darker background"                          → background with dark color_tone
  "more chill" / "nature"                      → Forest Green or similar vibe
  "too many photos" / "remove the weakest"     → remove_image at position 1
  "main photo isn't great" / "swap the hero"   → swap_image targeting highest position;
      use first index from available_images if any, otherwise use the selected image at position 1
  "make bigger" / "enlarge" / "increase size"  → resize_photo, scale=1.1
  "make smaller" / "downsize" / "shrink"       → resize_photo, scale=0.9
  "change arrangement" / "different layout" /
  "rearrange" / "rearrange photos"             → adjust_layout using the "-v2" variant of the
      current photo count (e.g. "3-image" → "3-image-v2"; "3-image-v2" → "3-image" to toggle back).
      Note: "1-image" has no v2 variant — respond with a no-op adjust_layout to "1-image" and
      explain in reason.
  If still unclear: make the most reasonable choice and explain in reason.\
"""

USER_TEMPLATE = """\
Current poster state:
{state_json}

Available backgrounds:
{backgrounds_json}

Instruction: "{instruction}"

Return exactly ONE of these JSON shapes:
{{"action": "swap_image",        "target_position": int, "new_image_index": int, "reason": string}}
{{"action": "remove_image",      "target_position": int,                         "reason": string}}
{{"action": "change_background", "new_background": string,                       "reason": string}}
{{"action": "adjust_layout",     "new_layout": "1-image|2-image|3-image|4-image|2-image-v2|3-image-v2|4-image-v2", "reason": string}}
{{"action": "resize_photo",      "scale": float,                                 "reason": string}}\
"""


def _extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        return fenced.group(1).strip()
    obj = re.search(r"\{[\s\S]*\}", text)
    if obj:
        return obj.group().strip()
    return text.strip()


def interpret_and_apply(state: PosterState, instruction: str,
                        backgrounds_json: str) -> PosterState:
    """Parse NL instruction → edit command → updated state."""
    command = _interpret(state, instruction, backgrounds_json)
    return _apply(state, command)

def _response_text(resp: Message) -> str:

    return "\n".join(

        block.text

        for block in resp.content

        if isinstance(block, TextBlock)

    )
def _interpret(state: PosterState, instruction: str, backgrounds_json: str) -> EditCommand:
    client = anthropic.Anthropic()

    user_msg = USER_TEMPLATE.format(
        state_json=state.model_dump_json(indent=2),
        backgrounds_json=backgrounds_json,
        instruction=instruction,
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=512,
        temperature=0,
        system=SYSTEM,
        messages=[{"role": "user", "content": user_msg}],
    )
    raw = _response_text(resp)
    extracted = _extract_json(raw)

    if not extracted:
        log.warning("Editor LLM returned empty response: %r", raw[:200])

    return _adapter.validate_json(extracted)


def _layout_for_count(count: int) -> LayoutName:
    try:
        return _LAYOUT_BY_COUNT[count]
    except KeyError:
        raise ValueError(f"Unsupported image count for layout: {count}")
    

"""
This method applies a structured edit command to state and raise ValueError for invalid operations
1. If it is a swap, then find among the other available images. After swap, exchange roles as well.
2. Removed images goes into the available image.
3. During adjust layout, ff the new layout needs more images, it pulls images from available_images, inserts them 
at the lowest position, and shifts existing selected images upward; if it needs fewer images, 
it removes the lowest-position selected images and moves them back to available. 
Afterward, it re-sorts selected images, reassigns positions starting from 1, and updates state.layout to the requested layout.
4. During resize, make sure the photo never goes beyond the 0.7-1.3 expand factors range.
"""
def _apply(state: PosterState, command: EditCommand) -> PosterState:
    state = state.model_copy(deep=True)

    if isinstance(command, SwapImageCommand):
        old = next((img for img in state.selected_images
                    if img.position == command.target_position), None)
        if old is None:
            raise ValueError(f"No image at position {command.target_position}")

        new_avail = next((img for img in state.available_images
                          if img.index == command.new_image_index), None)
        new_sel = next((img for img in state.selected_images
                        if img.index == command.new_image_index), None)

        if new_avail is not None:
            state.selected_images.remove(old)
            state.available_images.remove(new_avail)
            state.selected_images.append(SelectedImage(
                index=new_avail.index, filename=new_avail.filename,
                role=old.role, position=old.position,
            ))
            state.available_images.append(AvailableImage(index=old.index, filename=old.filename))
        elif new_sel is not None and new_sel is not old:
            old.position, new_sel.position = new_sel.position, old.position
            old.role,     new_sel.role     = new_sel.role,     old.role
        elif new_sel is old:
            pass
        else:
            raise ValueError(
                f"Image index {command.new_image_index} not found in available or selected images"
            )
        state.selected_images.sort(key=lambda x: x.position)

    elif isinstance(command, RemoveImageCommand):
        if len(state.selected_images) <= 1:
            raise ValueError("Cannot remove the last image from the poster")
        removed = next((img for img in state.selected_images
                        if img.position == command.target_position), None)
        if removed is None:
            raise ValueError(f"No image at position {command.target_position}")
        state.selected_images.remove(removed)
        state.available_images.append(AvailableImage(index=removed.index, filename=removed.filename))
        state.selected_images.sort(key=lambda x: x.position)
        for i, img in enumerate(state.selected_images, start=1):
            img.position = i
        state.layout = _layout_for_count(len(state.selected_images))

    elif isinstance(command, ChangeBackgroundCommand):
        state.background = command.new_background

    elif isinstance(command, AdjustLayoutCommand):
        new_count = int(command.new_layout.split("-")[0])
        current_count = len(state.selected_images)
        if new_count > current_count:
            to_add = state.available_images[:new_count - current_count]
            if len(to_add) < new_count - current_count:
                raise ValueError("Not enough available images to expand layout")
            for avail in to_add:
                state.available_images.remove(avail)
                for img in state.selected_images:
                    img.position += 1
                state.selected_images.insert(0, SelectedImage(
                    index=avail.index, filename=avail.filename,
                    role="lifestyle", position=1,
                ))
        elif new_count < current_count:
            state.selected_images.sort(key=lambda x: x.position)
            to_remove = state.selected_images[:current_count - new_count]
            for img in to_remove:
                state.selected_images.remove(img)
                state.available_images.append(AvailableImage(index=img.index, filename=img.filename))
        state.selected_images.sort(key=lambda x: x.position)
        for i, img in enumerate(state.selected_images, start=1):
            img.position = i
        state.layout = command.new_layout

    elif isinstance(command, ResizePhotoCommand):
        new_scale = state.hero_scale * command.scale
        state.hero_scale = max(0.7, min(1.3, new_scale))

    return state
