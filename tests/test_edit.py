import subprocess
import sys
from pathlib import Path
import pytest

EDIT_SEQUENCES = {
    "user_01": [
        "use a darker background",
        "make the hero photo bigger",
    ],
    "user_02": [
        "remove the weakest photo",
        "use a brighter background",
        "change the arrangement",
    ],
    "user_03": [
        "swap the main photo",
        "use a nature background",
        "make the hero photo smaller",
    ],
    "user_04": [
        "use a darker background",
        "make the hero photo smaller",
    ],
    "user_05": [
        "swap the main photo",
        "use a warmer background",
    ],
    "user_06": [
        "use a luxury background",
        "make the hero photo bigger",
        "change the arrangement",
    ],
    "user_07": [
        "use a brighter background",
        "remove the weakest photo",
    ],
    "user_08": [
        "use a pink background",
        "make the hero photo smaller",
        "swap the hero photo",
    ],
    "user_09": [
        "use a nightlife background",
        "change the arrangement",
    ],
    "user_10": [
        "use a fresh background",
        "remove the weakest photo",
        "make the hero photo bigger",
    ],
}


@pytest.mark.parametrize("user_id", EDIT_SEQUENCES.keys())
def test_edit(user_id):
    gen_dir = Path("outputs/generations") / user_id
    instructions = EDIT_SEQUENCES[user_id]
    for i, instruction in enumerate(instructions, start=1):
        result = subprocess.run(
            [sys.executable, "src/edit.py", str(gen_dir), instruction],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"{user_id} edit '{instruction}' failed:\n{result.stderr}"
        )
        print(f"  [{user_id}] edit {i}/{len(instructions)} done: '{instruction}'")
