import argparse
import sys
import logging
from pathlib import Path
import anthropic
from models import PosterState
from editor import interpret_and_apply
from renderer import render
from config import EDITS_ROOT, BACKGROUNDS_INDEX

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def next_edit_dir(state: PosterState) -> Path:
    # Use state.user so this works whether the input dir is a generation dir or a prior edit dir.
    user_edits_dir = EDITS_ROOT / state.user
    user_edits_dir.mkdir(parents=True, exist_ok=True)

    existing_edit_nums = []

    for child in user_edits_dir.iterdir():
        if child.is_dir() and child.name.startswith("edit"):
            suffix = child.name.removeprefix("edit")
            if suffix.isdigit():
                existing_edit_nums.append(int(suffix))

    next_num = max(existing_edit_nums, default=0) + 1
    edit_dir = user_edits_dir / f"edit{next_num}"
    edit_dir.mkdir(parents=True, exist_ok=False)

    return edit_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Edit a Ditto poster via natural language.")
    parser.add_argument("output_dir", type=Path, help="e.g. outputs/user_01/")
    parser.add_argument("instruction", type=str, help="Natural language edit instruction")
    args = parser.parse_args()

    state_path = args.output_dir / "poster_state.json"
    if not state_path.exists():
        print(f"Error: {state_path} not found — run generate.py first", file=sys.stderr)
        return 1

    state = PosterState.model_validate_json(state_path.read_text(encoding="utf-8"))
    backgrounds_json = BACKGROUNDS_INDEX.read_text(encoding="utf-8")

    print(f"Interpreting: \"{args.instruction}\"")

    client = anthropic.Anthropic()
    try:
        updated = interpret_and_apply(state, args.instruction, backgrounds_json, client)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    edit_dir = next_edit_dir(updated)

    poster = render(updated)
    poster.save(str(edit_dir / "poster.png"))
    (edit_dir / "poster_state.json").write_text(updated.model_dump_json(indent=2), encoding="utf-8")

    print(f"Updated → {edit_dir}/poster.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())