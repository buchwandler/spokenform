import subprocess
import sys
from pathlib import Path

EXAMPLES = Path(__file__).parents[1] / "examples"


def test_examples_compile() -> None:
    for path in EXAMPLES.glob("*.py"):
        subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            check=True,
            capture_output=True,
            text=True,
        )


def test_german_example_help() -> None:
    completed = subprocess.run(
        [sys.executable, str(EXAMPLES / "german.py"), "--help"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--spacy-model" in completed.stdout
