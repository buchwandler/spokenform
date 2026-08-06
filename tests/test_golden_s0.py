import json
from pathlib import Path

from spokenform import prepare

GOLDEN_PATH = Path(__file__).parent / "data" / "golden_s0.json"


def test_s0_golden_corpus() -> None:
    cases = json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    for case in cases:
        options = {
            key: case[key]
            for key in ("expand_abbreviations", "expand_numbers", "normalize_whitespace")
            if key in case
        }
        result = prepare(case["input"], language=case["language"], **options)
        if "spoken_text" in case:
            assert result.spoken_text == case["spoken_text"], case["name"]
        for expected in case.get("spoken_text_contains", []):
            assert expected in result.spoken_text, case["name"]
