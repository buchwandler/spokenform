import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from benchmarks.polynorm import _parser
from benchmarks.polynorm_compare import compare_runs
from benchmarks.polynorm_data import PolyNormCase
from benchmarks.polynorm_eval import (
    NUMBER_RELATED_CATEGORIES,
    POLYNORM_DATASET_COMMIT,
    POLYNORM_QUARANTINE,
    _filter_failures_by_speech_wer,
    environment_fingerprint,
    evaluate_and_write,
    evaluate_cases,
    literal_key,
    numeric_category_failures,
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
    stored = [
        json.loads(line)["id"] for line in (output_dir / "failures.jsonl").read_text().splitlines()
    ]
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
    assert quantity["risk_tier"] == "low"
    assert quantity["claim_owner"] == "owned"
    assert quantity["winning_span"]["source"] == "42 kg"
    assert quantity["failure_phase"] == "structured_rendering"
    assert quantity["render_mode"] == "quantity"
    assert set(summary["gate_metrics"]) == {
        "safety",
        "owned",
        "dependency-abbr2words",
        "extended",
        "protected",
        "downstream",
        "unsupported",
        "external-language",
        "questionable-target",
        "quarantine",
        "locale",
    }
    assert summary["gate_metrics"]["protected"]["cases"] == 1
    assert summary["gate_metrics"]["safety"]["protected_unchanged_rate"] == 1.0


def test_category_ownership_separates_dependency_and_extended_families() -> None:
    cases = (
        PolyNormCase("en-US", "initialism", "Initialism or Acronym", "NASA", "nasa"),
        PolyNormCase("en-US", "fraction", "Fractions", "3/4", "three fourths"),
        PolyNormCase("en-US", "unknown", "Unlisted Category", "x", "x"),
    )

    summary, failures = evaluate_cases(cases)

    assert summary["by_ownership"]["dependency-abbr2words"]["cases"] == 1
    assert summary["by_ownership"]["extended-candidate"]["cases"] == 1
    assert summary["by_ownership"]["unsupported"]["cases"] == 1
    assert summary["risk_tier_counts"]["high"] == 1
    initialism = next(row for row in failures if row["id"] == "en-US:initialism")
    assert initialism["ownership"] == "dependency-abbr2words"
    assert initialism["risk_tier"] == "high"


def test_version_provenance_names_separator_role() -> None:
    case = PolyNormCase("en-US", "version", "Version Numbers", "Python 3.9.7", "spoken")
    summary, failures = evaluate_cases((case,))
    assert summary["cases"] == 1
    assert failures[0]["separator"] == "."
    assert failures[0]["separator_role"] == "version"


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
    assert fingerprint["config_hash"] == fingerprint["configuration"]["config_hash"]


def test_summary_and_markdown_expose_outcome_buckets_and_identity(tmp_path) -> None:
    cases = (PolyNormCase("en-US", "1", "Initialism or Acronym", "NASA", "nasa spoken"),)

    output_dir, summary = evaluate_and_write(cases, output_root=tmp_path)

    assert "outcome_counts" in summary
    assert "dependency-mismatch" in summary["outcome_counts"]
    assert "risk_tier_counts" in summary
    markdown = (output_dir / "failures.md").read_text(encoding="utf-8")
    assert "## Run identity" in markdown
    assert "abbr2words_version" in markdown
    assert "Risk tier" in markdown


def test_extended_profile_is_explicit_and_promotes_literals() -> None:
    case = PolyNormCase("en-US", "profile", "URL or Email", "https://example.org", "spoken")
    calls: list[dict[str, object]] = []

    def fake_prepare(text: str, **kwargs: object):
        calls.append(kwargs)
        return prepare(text, **kwargs)

    summary, _ = evaluate_cases((case,), prepare_fn=fake_prepare, profile="extended")
    assert summary["profile"] == "extended"
    assert summary["normalize_literals"] is True
    assert calls[0]["normalize_literals"] is True


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
    assert comparison["regression_delta"] == {
        "resolved_count": 2,
        "new_failure_count": 1,
        "remaining_count": 1,
    }


def test_compare_runs_refuses_incompatible_profiles_unless_overridden(tmp_path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    base = {
        "benchmark": "PolyNorm-Bench",
        "dataset_commit": "dataset-1",
        "profile": "default",
        "environment": {
            "dataset_repository": "repo",
            "dataset_commit": "dataset-1",
            "locale_mapping": {"en-US": {"spokenform": "en_US"}},
            "configuration": {"profile": "default", "config_hash": "hash-default"},
            "config_hash": "hash-default",
        },
        "semantic_failure_count": 0,
        "speech_exact_equivalent_count": 0,
        "literal_exact_count": 0,
    }
    other = {
        **base,
        "profile": "extended",
        "environment": {
            **base["environment"],
            "configuration": {"profile": "extended", "config_hash": "hash-extended"},
            "config_hash": "hash-extended",
        },
    }
    (before / "summary.json").write_text(json.dumps(base), encoding="utf-8")
    (after / "summary.json").write_text(json.dumps(other), encoding="utf-8")
    (before / "failures.jsonl").write_text("", encoding="utf-8")
    (after / "failures.jsonl").write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="incompatible benchmark runs"):
        compare_runs(before, after)
    comparison = compare_runs(before, after, allow_incompatible=True)
    assert comparison["identity"]["overridden"] is True


def test_failure_family_and_quarantine_reason_codes_are_reported() -> None:
    cases = (
        PolyNormCase("es-MX", "86", "Decimal", "1,2", "one point two"),
        PolyNormCase("en-US", "1", "Sports Score", "5:3", "five to three"),
    )
    summary, failures = evaluate_cases(cases)
    assert summary["quarantine_reason_codes"] == {"questionable-target": 1}
    assert failures[0]["quarantine_reason_code"] == "questionable-target"
    assert failures[0]["failure_family"] == "dataset-quarantine"


def test_quarantine_entries_are_evidence_backed_and_do_not_hide_normal_failures() -> None:
    assert set(POLYNORM_QUARANTINE) == {
        "es-MX:86",
        "es-MX:249",
        "es-MX:274",
        "fr-FR:208",
        "fr-FR:310",
        "fr-FR:316",
    }
    assert all(
        entry["dataset"] == "PolyNorm-Bench"
        and entry["dataset_commit"] == POLYNORM_DATASET_COMMIT
        and entry["case_id"] == case_id
        and entry["evidence"]
        for case_id, entry in POLYNORM_QUARANTINE.items()
    )


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


def test_numeric_category_gate_ignores_quarantine_and_protected_rows() -> None:
    rows = (
        {
            "canonical_category": "Decimal",
            "quarantine": None,
            "ownership": "owned",
            "error": None,
            "semantic_failure": True,
            "residual_symbols": {"digits": 0},
            "id": "es-MX:1",
        },
        {
            "canonical_category": "Decimal",
            "quarantine": {"reason_code": "questionable-target"},
            "ownership": "owned",
            "error": None,
            "semantic_failure": True,
            "residual_symbols": {"digits": 0},
            "id": "es-MX:86",
        },
        {
            "canonical_category": "Version Numbers",
            "quarantine": None,
            "ownership": "protected",
            "error": None,
            "semantic_failure": True,
            "residual_symbols": {"digits": 3},
            "id": "en-US:1",
        },
    )
    assert "Decimal" in NUMBER_RELATED_CATEGORIES
    assert [row["id"] for row in numeric_category_failures(rows)] == ["es-MX:1"]
