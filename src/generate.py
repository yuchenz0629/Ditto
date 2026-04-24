import argparse
import sys
import logging
from pathlib import Path
from metadata_parser import parse_metadata
from analyzer import analyze
from renderer import render

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

GENERATIONS_ROOT = Path("outputs/generations")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a Ditto poster.")
    parser.add_argument("user_dir", type=Path, help="e.g. assets/users/user_01/")
    args = parser.parse_args()

    user_dir = Path(args.user_dir)
    if not user_dir.exists():
        print(f"Error: {user_dir} does not exist", file=sys.stderr)
        return 1

    print(f"Parsing {user_dir.name}...")
    parsed = parse_metadata(user_dir)

    print(f"Analyzing {len(parsed.image_paths)} photos...")
    state = analyze(parsed)
    print(f"  Selected {len(state.selected_images)} images | background: {state.background}")

    print("Rendering...")
    poster = render(state)

    out_dir = GENERATIONS_ROOT / user_dir.name
    out_dir.mkdir(parents=True, exist_ok=True)

    poster.save(str(out_dir / "poster.png"))
    (out_dir / "poster_state.json").write_text(state.model_dump_json(indent=2))

    print(f"Done → {out_dir}/poster.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())