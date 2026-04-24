import argparse
import sys
import logging
import time
from pathlib import Path
import anthropic
from metadata_parser import parse_metadata
from analyzer import analyze
from renderer import render
from config import GENERATIONS_ROOT

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

"""
All images are sent to Claude in a single API call, returns a JSON covering the entire image set
If the JSON is malformed or there is a pydantic validation failure like a wrong type of field, retry is fired
Empty selection is handled separately, where we force an image to be selected
"""
def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Ditto poster.")
    parser.add_argument("user_dir", type=Path, help="e.g. assets/users/user_01/")
    args = parser.parse_args()

    user_dir = Path(args.user_dir)
    if not user_dir.exists():
        print(f"Error: {user_dir} does not exist", file=sys.stderr)
        return 1

    t0 = time.monotonic()

    print(f"[{user_dir.name}] Parsing metadata...")
    parsed = parse_metadata(user_dir)
    t1 = time.monotonic()
    print(f"[{user_dir.name}] Found {len(parsed.image_paths)} photos [{t1 - t0:.1f}s]")

    client = anthropic.Anthropic()
    print(f"[{user_dir.name}] Analyzing photos (Claude)...")
    state = analyze(parsed, client)
    t2 = time.monotonic()

    selected_summary = ", ".join(
        f"{img.filename}({img.role})" for img in state.selected_images
    )
    print(f"[{user_dir.name}] Selected [{t2 - t1:.1f}s]: {selected_summary}")
    print(f"[{user_dir.name}] Background: {state.background} | Layout: {state.layout}")
    if state.rejected_images:
        rejected_names = ", ".join(img.filename for img in state.rejected_images)
        print(f"[{user_dir.name}] Rejected: {rejected_names}")
    print(f"[{user_dir.name}] Available for swap: {len(state.available_images)} image(s)")

    print(f"[{user_dir.name}] Rendering...")
    poster = render(state)
    t3 = time.monotonic()
    print(f"[{user_dir.name}] Rendered [{t3 - t2:.1f}s]")

    out_dir = GENERATIONS_ROOT / user_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)

    poster.save(str(out_dir / "poster.png"))
    (out_dir / "poster_state.json").write_text(state.model_dump_json(indent=2), encoding="utf-8")

    print(f"[{user_dir.name}] Done → {out_dir}/poster.png [{t3 - t0:.1f}s total]")
    return 0


if __name__ == "__main__":
    sys.exit(main())