import json
from pathlib import Path
from types import SimpleNamespace

from benchmarks.polynorm_data import PolyNormCase
from benchmarks.polynorm_eval import (
    evaluate_and_write,
    evaluate_cases,
    literal_key,
    speech_key,
    speech_key_equivalent,
    word_error_rate,
)
from spokenform import prepare


def test_comparison_normalization_keeps_semantic_symbols() -> None:
    assert literal_key("  A\n  B  ") == "A B"
    assert speech_key("Pay $5.") != speech_key("Pay five.")
    assert speech_key("Hello, world!") == speech_key("Hello world")
    assert word_error_rate(("one", "two"), ("one", "three")) == 0.5
    assert speech_key_equivalent("i ese be ene", language="es") == ("i", "s", "b", "n")


def test_evaluation_separates_raw_presentation_and_semantic_diagnostics() -> None:
    case = PolyNormCase("es-MX", "1", "Initialism or Acronym", "ISBN", "I S B N")

    def prepare_case(text: str, **kwargs):
        return SimpleNamespace(spoken_text="i ese be ene", warnings=(), stages=(), mapped_edits=())

    summary, failures = evaluate_cases((case,), prepare_fn=prepare_case)
    assert summary["speech_exact_rate"] == 0.0
    assert summary["speech_exact_equivalent_rate"] == 1.0
    assert summary["presentation_only_count"] == 1
    assert summary["semantic_failure_count"] == 0
    assert failures[0]["speech_exact_raw"] is False
    assert failures[0]["speech_exact_equivalent"] is True


def test_evaluation_aggregates_and_continues_after_exception() -> None:
    cases = (
        PolyNormCase("en-US", "1", "Cardinal", "2", "two"),
        PolyNormCase("en-US", "2", "Date", "bad", "expected"),
        PolyNormCase("de-DE", "1", "Cardinal", "2", "drei"),
    )

    def prepare_case(text: str, **kwargs):
        if text == "bad":
            raise RuntimeError("synthetic failure")
        return prepare(text, **kwargs)

    summary, failures = evaluate_cases(cases, prepare_fn=prepare_case)

    assert summary["cases"] == 3
    assert summary["error_count"] == 1
    assert summary["by_locale"]["en-US"]["cases"] == 2
    assert summary["by_category"]["Date"]["error_count"] == 1
    assert summary["by_locale_category"]["en-US"]["Date"]["error_count"] == 1
    assert "digits" in summary["residual_symbols_by_category"]["Cardinal"]
    assert [failure["id"] for failure in failures] == ["en-US:2", "de-DE:1"]
    assert failures[1]["changed_stages"]
    assert "source_rules" in failures[1]
    assert failures[1]["structured_claimed"] is False


def test_evaluate_and_write_separates_metrics_from_text_reports(tmp_path) -> None:
    cases = (PolyNormCase("en-US", "1", "Cardinal", "2", "two"),)

    output_dir, summary = evaluate_and_write(cases, output_root=tmp_path)

    assert summary["cases"] == 1
    summary_json = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert "original_text" not in json.dumps(summary_json)
    assert (output_dir / "failures.jsonl").read_text(encoding="utf-8") == ""
    assert "PolyNorm failures" in (output_dir / "failures.md").read_text(encoding="utf-8")


def test_reduction_fixture_covers_multiple_failure_families() -> None:
    fixture = json.loads(
        (Path(__file__).parent / "data" / "polynorm_reduction.json").read_text(encoding="utf-8")
    )

    assert {item["category"] for item in fixture} == {
        "Unit",
        "Time",
        "ISBN",
        "Chemical Formula",
        "Phone Number",
    }
