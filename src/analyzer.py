import base64
import io
import json
import logging
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
from config import MODEL, BACKGROUND_GUIDE_PATH, MAX_TOKENS, TEMPERATURE, GENDER_FALLBACK_BACKGROUND
from llm_utils import LAYOUT_BY_COUNT, extract_json, response_text

_MAX_SIDE = 800
log = logging.getLogger(__name__)

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
dominant_tone (warm/cool/neutral/dark), \
subject_prominence (dominant/medium/small/minimal — how much of the frame the \
subject fills and how visually central they are; penalise subjects partially hidden \
behind foreground objects or dwarfed by a large background).

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
- Do NOT select images where the subject is too distant or too obscured to look good
  at poster scale — leave them as available for manual swap instead. Any one of the
  following is sufficient to disqualify from selection (sharpness does not override this):
    • subject_prominence rated small or minimal in Step 1
    • subject appears to occupy less than ~25% of the frame height
    • a foreground object (equipment rack, car, crowd, furniture) substantially
      blocks the view of the subject's body
    • subject is a small figure against a large or dominant background (wide cityscape,
      open landscape, stadium) and facial features are not clearly legible at a glance
    • mirror/reflection shots where the subject's image is distant, back-facing,
      or partially hidden behind objects in the foreground
  These images crop and scale poorly at poster dimensions regardless of sharpness.
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
Do not treat any background as a universal default — ignore any default or fallback \
suggestions within the guide itself. If no background is a clear match, pick the one \
whose color_tone best complements the dominant_tone of the selected photos.

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
    try:
        img = _PILImage.open(path)
    except Exception as e:
        raise RuntimeError(f"Failed to open image {path}: {e}") from e
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


# All LLM interaction is isolated here so other tasks remain easy to test independently
def _call(client: anthropic.Anthropic, content: list) -> str:
    resp = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=SYSTEM,
        messages=[{"role": "user", "content": content}],
    )

    raw = response_text(resp)
    extracted = extract_json(raw)

    if not extracted:
        log.warning("Model returned an empty or unparseable response: %r", raw[:200])

    return extracted


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
            background_guide=BACKGROUND_GUIDE_PATH.read_text(encoding="utf-8"),
        ),
    })
    return content


# Normalize common filename variants, then fall back to a gender-appropriate default
def _normalize_background(bg_value: str, parsed: ParsedInput) -> str:
    valid_names = {b.name for b in parsed.backgrounds}
    if bg_value in valid_names:
        return bg_value
    candidate = (
        bg_value.replace("_", " ")
        .removesuffix(".jpg")
        .removesuffix(".jpeg")
        .removesuffix(".png")
    )
    if candidate in valid_names:
        return candidate
    fallback = GENDER_FALLBACK_BACKGROUND.get(parsed.gender, GENDER_FALLBACK_BACKGROUND["default"])
    log.warning("Unknown background %r — defaulting to '%s'", bg_value, fallback)
    return fallback


# The selected/rejected lists are index-based, so include that in the poster state
# Then derive the layout from the number of images selected
def _parse(raw: str, parsed: ParsedInput) -> PosterState:
    data = json.loads(raw)
    analysis = _RawAnalysisResult(**data)

    log.info("Model ranking (position → index, role):")
    for img in sorted(analysis.selected_images, key=lambda x: x.position):
        log.info("  pos=%d  idx=%d  role=%s", img.position, img.index, img.role)
    if analysis.rejected_images:
        log.info("Model rejections:")
        for img in analysis.rejected_images:
            log.info("  idx=%d  reason=%s", img.index, img.reason)
    log.info("Model background choice: %s", analysis.background)

    if not analysis.selected_images:
        # Force-select the first image rather than producing an empty poster
        log.warning("LLM selected no images — force-selecting index 0")
        analysis.selected_images = [
            _RawSelectedImage(index=0, role="hero", position=1)
        ]
        analysis.layout = "1-image"

    n = len(parsed.image_paths)
    for img in analysis.selected_images:
        if img.index >= n:
            raise ValueError(
                f"LLM returned out-of-range index {img.index} (only {n} images)"
            )

    all_indices = set(range(n))
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

    derived_layout = LAYOUT_BY_COUNT.get(len(selected))
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


def analyze(parsed: ParsedInput, client: anthropic.Anthropic) -> PosterState:
    """Send all images to Claude, return initial PosterState."""
    content = _build_content(parsed)
    log.info("Sending %d images to Claude for analysis...", len(parsed.image_paths))
    raw = _call(client, content)
    try:
        return _parse(raw, parsed)
    except Exception as e:
        log.warning("First parse failed (%s) — raw: %r — retrying...", e, raw[:300])
        raw = _call(client, content)
        return _parse(raw, parsed)
