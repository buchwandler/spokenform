import json
import subprocess
import sys

import pytest

from spokenform.cli import _parser


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


def test_cli_selects_an_installed_spacy_model_without_detection_flag() -> None:
    args = _parser().parse_args(["--spacy-model", "en_core_web_sm", "2 tests"])
    assert args.spacy_model == "en_core_web_sm"
    with pytest.raises(SystemExit):
        _parser().parse_args(["--detect-language", "2 tests"])



def test_cli_exposes_strict_mode() -> None:
    args = _parser().parse_args(["--strict", "2 tests"])
    assert args.strict is True
