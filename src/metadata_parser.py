import json
from pathlib import Path
from models import ParsedInput, BackgroundMeta

BACKGROUNDS_DIR = Path("assets/backgrounds")

IMAGE_SUFFIXES = {".jpeg", ".jpg", ".png"}

def parse_metadata(user_dir: Path) -> ParsedInput:
    user_dir = Path(user_dir)
    text = (user_dir / "metadata.md").read_text(encoding="utf-8")

    name = _extract_field(text, "name")
    gender = _extract_field(text, "gender").lower()
    ethnicity = _extract_field(text, "ethnicity")

    image_paths = sorted(
        str(p) for p in user_dir.iterdir()
        if p.suffix.lower() in IMAGE_SUFFIXES
    )

    raw = json.loads((BACKGROUNDS_DIR / "index.json").read_text(encoding="utf-8"))
    backgrounds = [BackgroundMeta(**b) for b in raw["backgrounds"]]

    return ParsedInput(
        user_id=user_dir.name,
        user_dir=str(user_dir),
        name=name,
        gender=gender,
        ethnicity=ethnicity,
        image_paths=image_paths,
        backgrounds=backgrounds,
    )


def _extract_field(text: str, field_name: str) -> str:
    """Return value on the line immediately after the matching field label."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower() == field_name.lower() and i + 1 < len(lines):
            value = lines[i + 1].strip()
            if value:
                return value
    return ""
