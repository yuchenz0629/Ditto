import subprocess
import sys
import time
import logging
from pathlib import Path
import pytest

log = logging.getLogger(__name__)

USERS = [f"user_{i:02d}" for i in range(1, 11)]
TIMEOUT = 30  # seconds per generation attempt


def _run(user_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "src/generate.py", str(user_dir)],
        capture_output=True,
        text=True,
        timeout=TIMEOUT,
    )


def _emit(stdout: str, stderr: str) -> None:
    for line in stdout.splitlines():
        if line.strip():
            log.info(line)
    for line in stderr.splitlines():
        if line.strip():
            log.info(line)


@pytest.mark.parametrize("user_id", USERS)
def test_generate(user_id):
    user_dir = Path("assets/users") / user_id
    start = time.monotonic()

    try:
        result = _run(user_dir)
    except subprocess.TimeoutExpired:
        log.warning("[%s] timed out after %ds — retrying once", user_id, TIMEOUT)
        try:
            result = _run(user_dir)
        except subprocess.TimeoutExpired:
            elapsed = time.monotonic() - start
            pytest.fail(
                f"{user_id} timed out twice (2×{TIMEOUT}s, {elapsed:.0f}s total) — pipeline is stuck"
            )

    elapsed = time.monotonic() - start
    _emit(result.stdout, result.stderr)

    assert result.returncode == 0, f"{user_id} failed in {elapsed:.1f}s:\n{result.stderr}"

    out_dir = Path("outputs/generations") / user_id
    assert (out_dir / "poster.png").exists(), f"poster.png missing for {user_id}"
    assert (out_dir / "poster_state.json").exists(), f"poster_state.json missing for {user_id}"
