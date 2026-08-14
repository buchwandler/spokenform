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
    assert completed.stdout.isascii()
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


def test_cli_exposes_structured_toggle() -> None:
    args = _parser().parse_args(["--no-structured", "2 kg"])
    assert args.no_structured is True


def test_cli_exposes_output_policies() -> None:
    args = _parser().parse_args(
        [
            "--symbol-mode",
            "keep",
            "--keep-symbols",
            ":;,()-,.",
            "--generic-acronyms",
            "spell-unknown",
            "--generic-acronym-case",
            "lower",
            "ABC, test!",
        ]
    )
    assert args.symbol_mode == "keep"
    assert args.keep_symbols == ":;,()-,."
    assert args.generic_acronym_mode == "spell-unknown"
    assert args.generic_acronym_case == "lower"


def test_cli_exposes_registered_acronym_policy() -> None:
    args = _parser().parse_args(["--registered-acronyms", "spell", "CEO"])
    assert args.registered_acronyms == "spell"


def test_cli_exposes_conservative_generic_acronym_policy() -> None:
    args = _parser().parse_args(["--generic-acronyms", "conservative-unknown"])
    assert args.generic_acronym_mode == "conservative-unknown"


def test_cli_output_policies_work_end_to_end() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "spokenform",
            "--no-numbers",
            "--symbol-mode",
            "keep",
            "--keep-symbols",
            ":;,()-,.",
            "--generic-acronyms",
            "spell-unknown",
            "--generic-acronym-case",
            "lower",
            "ABC, test!",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "A B C, test"
