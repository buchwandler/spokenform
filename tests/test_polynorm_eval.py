import json
from pathlib import Path
from types import SimpleNamespace

from benchmarks.polynorm_compare import compare_runs
from benchmarks.polynorm_data import PolyNormCase
from benchmarks.polynorm import _parser
from benchmarks.polynorm_eval import (
    _filter_failures_by_speech_wer,
    environment_fingerprint,
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


def test_speech_wer_threshold_is_strict_and_optional() -> None:
    failures = tuple(
        {"id": case_id, "speech_wer": wer}
        for case_id, wer in (("low", 0.25), ("equal", 0.5), ("high", 0.75))
    )

    assert [item["id"] for item in _filter_failures_by_speech_wer(failures, 0.5)] == ["high"]
    assert _filter_failures_by_speech_wer(failures, None) == failures
    assert _parser().parse_args(["--speech-wer-threshold", "0.5"]).speech_wer_threshold == 0.5


def test_speech_wer_threshold_keeps_polynorm_summary_metrics(tmp_path, monkeypatch):
    failures = tuple(
        {
            "id": case_id,
            "polynorm_locale": "en-US",
            "category": "Cardinal",
            "original_text": "source",
            "expected": "expected",
            "actual": "actual",
            "speech_wer": wer,
            "error": None,
        }
        for case_id, wer in (("low", 0.25), ("equal", 0.5), ("high", 0.75))
    )
    monkeypatch.setattr(
        "benchmarks.polynorm_eval.evaluate_cases",
        lambda cases: ({"cases": 3, "error_count": 0}, failures),
    )

    output_dir, summary = evaluate_and_write((), output_root=tmp_path, speech_wer_threshold=0.5)

    assert summary["cases"] == 3
    assert summary["speech_wer_threshold"] == 0.5
    assert summary["stored_failure_count"] == 1
    stored = [json.loads(line)["id"] for line in (output_dir / "failures.jsonl").read_text().splitlines()]
    assert stored == ["high"]
    report = (output_dir / "failures.md").read_text()
    assert "#### high" in report
    assert "#### equal" not in report
    assert "#### low" not in report


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
    assert failures[0]["render_mode"] == "unchanged"
    assert failures[0]["numeric_policy"]["decimal_word"] == "punto"


def test_evaluation_reports_claim_provenance_and_gate_views() -> None:
    cases = (
        PolyNormCase("de-DE", "1", "Unit", "42 kg", "wrong"),
        PolyNormCase("en-US", "2", "URL or Email", "https://example.org", "spoken"),
    )

    summary, failures = evaluate_cases(cases)

    quantity = next(item for item in failures if item["id"] == "de-DE:1")
    assert quantity["primary_rule"] == "de.quantity"
    assert quantity["claim_owner"] == "owned"
    assert quantity["winning_span"]["source"] == "42 kg"
    assert quantity["failure_phase"] == "structured_rendering"
    assert quantity["render_mode"] == "quantity"
    assert set(summary["gate_metrics"]) == {"safety", "owned", "extended", "protected", "locale"}
    assert summary["gate_metrics"]["protected"]["cases"] == 1
    assert summary["gate_metrics"]["safety"]["protected_unchanged_rate"] == 1.0


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


def test_environment_fingerprint_records_source_commit() -> None:
    fingerprint = environment_fingerprint(("en-US",))
    assert fingerprint["spokenform_source_commit"]


def test_compare_runs_reports_case_id_and_aggregate_deltas(tmp_path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    summaries = (
        {"semantic_failure_count": 3, "speech_exact_equivalent_count": 7, "literal_exact_count": 4},
        {"semantic_failure_count": 2, "speech_exact_equivalent_count": 8, "literal_exact_count": 5},
    )
    for directory, summary, failures in (
        (before, summaries[0], ("en-US:1", "en-US:2", "en-US:3")),
        (after, summaries[1], ("en-US:2", "en-US:4")),
    ):
        (directory / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (directory / "failures.jsonl").write_text(
            "".join(json.dumps({"id": failure}) + "\n" for failure in failures),
            encoding="utf-8",
        )

    comparison = compare_runs(before, after)

    assert comparison["summary_delta"] == {
        "semantic_failure_count": -1,
        "speech_exact_equivalent_count": 1,
        "literal_exact_count": 1,
    }
    assert comparison["case_delta"] == {
        "resolved": ["en-US:1", "en-US:3"],
        "new_failures": ["en-US:4"],
        "remaining": ["en-US:2"],
    }


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
