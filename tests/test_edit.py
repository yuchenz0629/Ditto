import subprocess
import sys
import time
import logging
from pathlib import Path
import pytest

log = logging.getLogger(__name__)

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

TIMEOUT = 30  # seconds per edit attempt


def _run(gen_dir: Path, instruction: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "src/edit.py", str(gen_dir), instruction],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )


@pytest.mark.parametrize("user_id", EDIT_SEQUENCES.keys())
def test_edit(user_id):
    gen_dir = Path("outputs/generations") / user_id
    instructions = EDIT_SEQUENCES[user_id]
    total_start = time.monotonic()

    log.info("[%s] Starting %d edits", user_id, len(instructions))

    for i, instruction in enumerate(instructions, start=1):
        log.info("[%s] edit %d/%d: \"%s\"", user_id, i, len(instructions), instruction)

        try:
            result = _run(gen_dir, instruction)
        except subprocess.TimeoutExpired:
            log.warning("[%s] edit %d timed out after %ds — retrying once", user_id, i, TIMEOUT)
            try:
                result = _run(gen_dir, instruction)
            except subprocess.TimeoutExpired:
                elapsed = time.monotonic() - total_start
                pytest.fail(
                    f"{user_id} edit {i} '{instruction}' timed out twice ({elapsed:.0f}s total)"
                )

        for line in result.stderr.splitlines():
            if line.strip():
                log.info(line)

        if result.returncode != 0:
            for line in result.stdout.splitlines():
                if line.strip():
                    log.info(line)
            assert result.returncode == 0, (
                f"{user_id} edit {i} '{instruction}' failed:\n{result.stderr}"
            )

    elapsed = time.monotonic() - total_start
    log.info("[%s] All %d edits done [%.1fs]", user_id, len(instructions), elapsed)
