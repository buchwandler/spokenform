import json
import subprocess
import sys


def test_module_cli_json() -> None:
    completed = subprocess.run(
        [sys.executable, "-m", "spokenform", "--lang", "de", "--json", "2 kg"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["language"] == "de"
    assert "zwei Kilogramm" in payload["spoken_text"]
