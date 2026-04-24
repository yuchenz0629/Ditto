import base64
import io
import json
import logging
import re
from pathlib import Path
from typing import Literal
from pydantic import BaseModel
from PIL import Image as _PILImage
from models import (
    ParsedInput, 
    PosterState,
    SelectedImage, 
    RejectedImage, 
    AvailableImage,
)
import anthropic
from anthropic.types import Message, TextBlock

_MAX_SIDE = 800
log = logging.getLogger(__name__)
MODEL = "claude-sonnet-4-6"

LayoutName = Literal[
    "1-image", 
    "2-image", 
    "3-image", 
    "4-image",
    "2-image-v2", 
    "3-image-v2", 
    "4-image-v2",
]

_LAYOUT_BY_COUNT: dict[int, LayoutName] = {
    1: "1-image",
    2: "2-image",
    3: "3-image",
    4: "4-image",
}

# Raw model output models intentionally do not include filenames; filenames are
# reattached after parsing by looking up the selected/rejected indices.
class _RawSelectedImage(BaseModel):
    index: int
    role: Literal["hero", "body", "lifestyle", "group"]
    position: int


class _RawRejectedImage(BaseModel):
    index: int
    reason: str


class _RawAnalysisResult(BaseModel):
    selected_images: list[_RawSelectedImage]
    rejected_images: list[_RawRejectedImage]
    background: str
    layout: str



SYSTEM = (
    "You are an image selection engine for a dating app poster generator. "
    "Follow the four steps below exactly. "
    "Output ONLY valid JSON. No commentary, no markdown fences."
)

USER_TEMPLATE = """\
Gender: {gender}
Ethnicity: {ethnicity}
Available backgrounds:
{backgrounds_json}

## Step 1 — Per-image assessment
For each photo (zero-indexed) assess: subject (single/group/none), \
framing (close-up/upper-body/full-body/wide), face_clarity (clear/partial/none), \
technical_quality (good/acceptable/poor), scene (e.g. beach, gym, bar, outdoors), \
dominant_tone (warm/cool/neutral/dark).

## Step 2 — De-duplication
If two images share the same scene, outfit, framing, and add no new visual information, \
select only the strongest one. Leave the weaker duplicate UNSELECTED (do not reject it) — \
it will remain available for the user to swap in manually. \
Only reject a duplicate if it is also technically unusable (extreme blur, no subject).

## Step 3 — Selection and ranking
Select 1-4 images from the set. Assign roles in priority order:
  hero      → best portrait, face clear, upper/half body — ALWAYS the last element
  body      → full figure or physique shot
  lifestyle → hobby, activity, or context
  group     → user with other people
Rules:
- Do not force-fill. 1-2 images is acceptable if quality is low.
- Prefer images where the subject is clearly visible, but do not reject an image just
  because a better one exists — leave it available for user swapping.
- Only add an image to rejected_images if it is truly unusable: no person visible
  (empty landscape, object-only shot), extreme blur making subject unrecognisable,
  or so dark the subject cannot be seen.
- Do NOT select images where the subject is very small (appears to occupy less than
  ~15 percent of the frame height) AND the shot is also blurry, or the subject is at the
  bottom of the frame — leave such images as available for manual swap instead.
  This typically covers: far-away crowd shots where the subject is barely visible,
  gym-mirror shots where the subject's reflection is at the bottom, or any photo
  where technical quality is poor AND the subject is distant.
- Strongly prefer images with people.
- When two images show the same person, prefer the one with higher apparent resolution
  and sharpness (i.e., avoid selecting a blurry or low-resolution version if a
  clearer one exists).
- position starts at 1 (lowest importance) and increments. Hero = highest position number.

## Step 4 — Background selection
Filter by gender compatibility first (see gender field in each background). \
Then use the detailed guide below to match by photo content, scene, and vibe — \
paying close attention to the "When to Use" conditions for each background. \
Use color_tone as a tiebreaker when conditions are inconclusive. \
If no background is a clear match, pick the one \
whose color_tone best complements the dominant_tone of the selected photos. \
or fall back to the safest option discussed in the background_guide.

{background_guide}

Return exactly this JSON (no other text):
{{
  "selected_images": [{{"index": int, "role": "group|lifestyle|body|hero", "position": int}}],
  "rejected_images": [{{"index": int, "reason": string}}],
  "background": string,
  "layout": "N-image"
}}
layout must equal len(selected_images) formatted as "N-image" (e.g. "3-image").\
"""

# Claude expects images as base64 content blocks. Resize first to reduce payload
# size while preserving enough visual detail for selection/cropping decisions.
def _encode_image(path: str) -> dict:
    img = _PILImage.open(path)
    if max(img.width, img.height) > _MAX_SIDE:
        img.thumbnail((_MAX_SIDE, _MAX_SIDE), _PILImage.Resampling.LANCZOS)
    buf = io.BytesIO()
    fmt = "JPEG" if Path(path).suffix.lower() in {".jpg", ".jpeg"} else "PNG"
    img.convert("RGB").save(buf, format=fmt, quality=85)
    data = buf.getvalue()
    media = "image/jpeg" if fmt == "JPEG" else "image/png"
    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": media,
            "data": base64.standard_b64encode(data).decode(),
        },
    }


# This keeps parsing tolerant without weakening the downstream Pydantic validation
def _extract_json(text: str) -> str:
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fenced:
        return fenced.group(1).strip()
    obj = re.search(r"\{[\s\S]*\}", text)
    if obj:
        return obj.group().strip()
    return text.strip()


def _response_text(resp: Message) -> str:
    texts: list[str] = []

    for block in resp.content:
        if isinstance(block, TextBlock):
            texts.append(block.text)

    return "\n".join(texts)

# All LLM interaction is isolated here so other tasks remain easy to test independently
def _call(client: anthropic.Anthropic, content: list) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        temperature=0,
        system=SYSTEM,
        messages=[{"role": "user", "content": content}],
    )

    raw = _response_text(resp)
    extracted = _extract_json(raw)

    if not extracted:
        log.warning("Model returned an empty or unparseable response: %r", raw[:200])

    return extracted


_BACKGROUND_GUIDE_PATH = Path("assets/backgrounds/Background_Guide.md")


def _build_content(parsed: ParsedInput) -> list:
    content: list = []
    for i, path in enumerate(parsed.image_paths):
        content.append({"type": "text", "text": f"Image {i}:"})
        content.append(_encode_image(path))
    content.append({
        "type": "text",
        "text": USER_TEMPLATE.format(
            gender=parsed.gender,
            ethnicity=parsed.ethnicity,
            backgrounds_json=json.dumps(
                [b.model_dump() for b in parsed.backgrounds], indent=2
            ),
            background_guide=_BACKGROUND_GUIDE_PATH.read_text(encoding="utf-8"),
        ),
    })
    return content

# Normalize common filename variants, then fall back to a safe default
def _normalize_background(bg_value: str, parsed: ParsedInput) -> str:
    """Return a background name that matches parsed.backgrounds[*].name.

    The LLM sometimes returns the file field (e.g. 'Sunset_Glow.jpg') instead
    of the name field (e.g. 'Sunset Glow').  Try exact match first, then
    match by stripping extension and converting underscores to spaces.
    Default to 'Sunset Glow' when no match is found.
    """
    valid_names = {b.name for b in parsed.backgrounds}
    if bg_value in valid_names:
        return bg_value
    candidate = bg_value.replace("_", " ").removesuffix(".jpg").removesuffix(".png")
    if candidate in valid_names:
        return candidate
    fallback = "Forest Green" if parsed.gender == "female" else "Serene Blue"
    log.warning("Unknown background %r — defaulting to '%s'", bg_value, fallback)
    return fallback


# The selected/rejected lists are index-based, so include that in the poster state
# Then derive the layout from the number of images selected
def _parse(raw: str, parsed: ParsedInput) -> PosterState:
    data = json.loads(raw)
    analysis = _RawAnalysisResult(**data)

    """
    log.info("Model ranking (position → index, role):")
    for img in sorted(analysis.selected_images, key=lambda x: x.position):
        log.info("  pos=%d  idx=%d  role=%s", img.position, img.index, img.role)
    if analysis.rejected_images:
        log.info("Model rejections:")
        for img in analysis.rejected_images:
            log.info("  idx=%d  reason=%s", img.index, img.reason)
    log.info("Model background choice: %s", analysis.background)
    """

    if not analysis.selected_images:
        # Force-select the first image rather than producing an empty poster
        log.warning("LLM selected no images — force-selecting index 0")
        analysis.selected_images = [
            _RawSelectedImage(index=0, role="hero", position=1)
        ]
        analysis.layout = "1-image"

    all_indices = set(range(len(parsed.image_paths)))
    selected_indices = {img.index for img in analysis.selected_images}
    rejected_indices = {img.index for img in analysis.rejected_images}
    available_indices = all_indices - selected_indices - rejected_indices

    selected = [
        SelectedImage(
            index=img.index,
            filename=Path(parsed.image_paths[img.index]).name,
            role=img.role,
            position=img.position,
        )
        for img in sorted(analysis.selected_images, key=lambda x: x.position)
    ]
    rejected = [
        RejectedImage(
            index=img.index,
            filename=Path(parsed.image_paths[img.index]).name,
            reason=img.reason,
        )
        for img in analysis.rejected_images
    ]
    available = [
        AvailableImage(index=i, filename=Path(parsed.image_paths[i]).name)
        for i in sorted(available_indices)
    ]

    derived_layout = _LAYOUT_BY_COUNT.get(len(selected))
    if derived_layout is None:
        raise ValueError(f"Unsupported selected image count: {len(selected)}")

    return PosterState(
        user=parsed.user_id,
        user_dir=parsed.user_dir,
        name=parsed.name,
        gender=parsed.gender,
        selected_images=selected,
        available_images=available,
        rejected_images=rejected,
        background=_normalize_background(analysis.background, parsed),
        layout=derived_layout,
    )


def analyze(parsed: ParsedInput) -> PosterState:
    """Send all images to Claude, return initial PosterState."""
    client = anthropic.Anthropic()
    content = _build_content(parsed)
    log.info("Sending %d images to Claude for analysis...", len(parsed.image_paths))
    raw = _call(client, content)
    try:
        return _parse(raw, parsed)
    except Exception as e:
        log.warning("First parse failed (%s) — raw: %r — retrying...", e, raw[:300])
        raw = _call(client, content)
        return _parse(raw, parsed)
