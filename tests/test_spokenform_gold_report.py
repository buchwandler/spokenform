from __future__ import annotations

from pathlib import Path

from benchmarks.spokenform_gold_report import render_report


def test_report_contains_sections_and_exact_failure_values(tmp_path: Path) -> None:
    summary = {
        "run_id": "run-1",
        "timestamp_utc": "now",
        "spokenform_version": "0.1.0",
        "spokenform_commit": "spokenform-commit",
        "spokenform_gold_version": "0.1.0-exp",
        "gold_manifest_hash": "manifest",
        "split": "test",
        "record_count": 2,
        "profile_name": "gold-v1",
        "profile_config": {"name": "gold-v1"},
        "mode": "canonical",
        "summary": {
            "records_total": 2,
            "records_scorable": 2,
            "primary_accuracy": 0.5,
            "sentence_canonical_accuracy": 0.5,
            "accepted_variant_accuracy": 1.0,
            "no_change_accuracy": 1.0,
            "false_positive_normalization_rate": 0.0,
            "per_category": {"time": {"records": 2, "canonical_matches": 1, "accepted_matches": 2}},
            "per_language": {"en": {"records": 2, "canonical_matches": 1, "accepted_matches": 2}},
            "per_locale": {"en-US": {"records": 2, "canonical_matches": 1, "accepted_matches": 2}},
            "per_status": {"gold": {"records": 2, "canonical_matches": 1, "accepted_matches": 2}},
            "ambiguous_count": 0,
            "quarantine_count": 0,
            "excluded_count": 0,
        },
        "adapter": {"repository": "repo", "dataset_commit": "commit", "source_mode": "auto-cache"},
        "identity": {"configuration_hash": "config"},
    }
    rows = [
        {
            "id": "first",
            "language": "en",
            "locale": "en-US",
            "status": "gold",
            "categories": ["time"],
            "family_id": "one",
            "input": "First",
            "expected": "First expected",
            "accepted_variants": ["First expected"],
            "actual": "First actual",
            "primary_match": True,
        },
        {
            "id": "second",
            "language": "en",
            "locale": "en-US",
            "status": "gold",
            "categories": ["time"],
            "family_id": "two",
            "input": "Second original",
            "expected": "Second expected",
            "accepted_variants": ["Second expected", "Second accepted"],
            "actual": "Second actual",
            "primary_match": False,
        },
    ]
    output = render_report(summary, rows, tmp_path / "report.html")
    html = output.read_text(encoding="utf-8")
    assert "Spokenform Gold" in html
    for label in (
        "Primary accuracy",
        "Canonical accuracy",
        "Accepted accuracy",
        "False-positive",
        "Categories",
        "Failures",
        "Metadata",
    ):
        assert label in html
    assert "Second original" in html
    assert "Second expected" in html
    assert "Second actual" in html
    assert "First actual" not in html


def test_report_is_self_contained(tmp_path: Path) -> None:
    output = render_report(
        {"summary": {}, "adapter": {}, "record_count": 0, "mode": "canonical"},
        [],
        tmp_path / "report.html",
    )
    html = output.read_text(encoding="utf-8")
    assert "<style>" in html
    assert "<script>" in html
    assert "https://" not in html
