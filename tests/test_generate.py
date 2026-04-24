import subprocess
import sys
from pathlib import Path
import pytest

USERS = [f"user_{i:02d}" for i in range(1, 11)]


@pytest.mark.parametrize("user_id", USERS)
def test_generate(user_id):
    user_dir = Path("assets/users") / user_id
    result = subprocess.run(
        [sys.executable, "src/generate.py", str(user_dir)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"{user_id} failed:\n{result.stderr}"

    out_dir = Path("outputs/generations") / user_id
    assert (out_dir / "poster.png").exists(), f"poster.png missing for {user_id}"
    assert (out_dir / "poster_state.json").exists(), f"poster_state.json missing for {user_id}"
