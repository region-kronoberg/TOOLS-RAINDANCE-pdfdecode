"""Lint-test: säkerställ att koden är ren enligt Ruff."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent


def test_ruff_clean():
    """Projektet ska vara fritt från Ruff-varningar."""
    try:
        subprocess.run(
            [sys.executable, "-m", "ruff", "--version"],
            check=True,
            capture_output=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("ruff är inte installerat")

    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "src", "tests"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        pytest.fail(f"Ruff hittade problem:\n{result.stdout}\n{result.stderr}")
