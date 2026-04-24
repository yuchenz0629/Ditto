import functools
import json
import os
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from models import PosterState
from layouts import LAYOUTS
from cropper import prepare_photo
from config import BACKGROUNDS_DIR, BACKGROUNDS_INDEX, LOGO_PATH


@functools.lru_cache(maxsize=1)
def _bg_filenames() -> dict[str, str]:
    data = json.loads(BACKGROUNDS_INDEX.read_text(encoding="utf-8"))
    return {b["name"]: b["file"] for b in data["backgrounds"]}

_FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",                              # macOS
    "C:/Windows/Fonts/arial.ttf",                                       # Windows
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",                  # Linux
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",  # Linux
]


def render(state: PosterState) -> Image.Image:
    """Compose and return the poster as an RGB image."""
    bg_filename = _bg_filenames().get(state.background)
    if bg_filename is None:
        raise ValueError(f"Unknown background '{state.background}' — not in index.json")
    bg_file = BACKGROUNDS_DIR / bg_filename
    if not bg_file.exists():
        raise FileNotFoundError(f"Background image not found: {bg_file}")
    base = Image.open(bg_file).convert("RGBA")
    bg_w, bg_h = base.size

    layout = LAYOUTS[state.layout]
    slots = sorted(layout["slots"], key=lambda s: s["z"])
    max_z = max(s["z"] for s in slots)
    pos_to_img = {img.position: img for img in state.selected_images}

    for slot in slots:
        img_meta = pos_to_img[slot["pos"]]
        slot_w = int(slot["w"] * bg_w)
        slot_h = int(slot["h"] * bg_h)
        if slot["z"] == max_z:
            slot_w = int(slot_w * state.hero_scale)
            slot_h = int(slot_h * state.hero_scale)
        cx_px  = int(slot["cx"] * bg_w)
        cy_px  = int(slot["cy"] * bg_h)

        photo_path = Path(state.user_dir) / img_meta.filename
        photo = prepare_photo(photo_path, slot_w, slot_h, slot["angle"])

        paste_x = cx_px - photo.width  // 2
        paste_y = cy_px - photo.height // 2

        # Clamp so rotated bounding box never exits the background.
        paste_x = max(0, min(paste_x, bg_w - photo.width))
        paste_y = max(0, min(paste_y, bg_h - photo.height))

        base.paste(photo, (paste_x, paste_y), mask=photo)

    _draw_text(base, state.name, layout["text_anchor"], bg_w, bg_h)
    _draw_logo(base, bg_w, bg_h)

    return base.convert("RGB")


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _draw_text(base: Image.Image, name: str, anchor: dict[str, float], bg_w: int, bg_h: int) -> None:
    draw = ImageDraw.Draw(base)
    x = int(anchor["x"] * bg_w)
    y = int(anchor["y"] * bg_h)

    subtitle_size = max(18, int(bg_h * 0.022))
    name_size     = max(36, int(bg_h * 0.058))
    subtitle_font = _load_font(subtitle_size)
    name_font     = _load_font(name_size)

    # Text shadow for legibility over busy backgrounds
    shadow = (0, 0, 0, 160)
    white  = (255, 255, 255, 255)
    for dx, dy in ((2, 2), (0, 0)):
        fill = shadow if dx else white
        draw.text((x + dx, y + dy), "Your date with", font=subtitle_font, fill=fill)

    name_y = y + subtitle_size + 4
    for dx, dy in ((2, 2), (0, 0)):
        fill = shadow if dx else white
        draw.text((x + dx, name_y + dy), name, font=name_font, fill=fill)


def _draw_logo(base: Image.Image, bg_w: int, bg_h: int) -> None:
    if not LOGO_PATH.exists():
        return
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo_w = int(bg_w * 0.18)
    logo = logo.resize(
        (logo_w, int(logo.height * logo_w / logo.width)), Image.Resampling.LANCZOS
    )
    x = bg_w  - logo.width  - int(bg_w  * 0.04)
    y = bg_h  - logo.height - int(bg_h  * 0.02)
    base.paste(logo, (x, y), mask=logo)
