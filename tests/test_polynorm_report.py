from __future__ import annotations

from benchmarks.polynorm_report import render_report


def _metrics(cases: int = 1) -> dict[str, object]:
    return {
        "cases": cases,
        "literal_exact_count": 0,
        "literal_exact_rate": 0.0,
        "speech_exact_count": 0,
        "speech_exact_rate": 0.0,
        "speech_exact_equivalent_count": 0,
        "speech_exact_equivalent_rate": 0.0,
        "presentation_only_count": 0,
        "semantic_failure_count": 1,
        "mean_speech_wer": 0.5,
        "median_speech_wer": 0.5,
        "unchanged_count": 0,
        "error_count": 0,
        "failure_family_count": 1,
    }


def fixture():
    summary = {
        "benchmark": "PolyNorm-Bench",
        "repository": "apple/ml-speech-polynorm-bench",
        "dataset_commit": "commit",
        "generated_at": "2026-08-18T00:00:00Z",
        "locales": ["en-US"],
        "spokenform_languages": ["en_US"],
        "environment": {"configuration": {"profile": "default"}},
        "identity": {"config_hash": "hash"},
        "profile": "default",
        "cases": 1,
        "speech_exact_count": 0,
        "speech_exact_rate": 0.0,
        "speech_exact_equivalent_count": 0,
        "speech_exact_equivalent_rate": 0.0,
        "semantic_failure_count": 1,
        "presentation_only_count": 0,
        "mean_speech_wer": 0.5,
        "quarantine_count": 0,
        "by_locale": {"en-US": _metrics()},
        "by_canonical_category": {"Cardinal": _metrics()},
        "by_locale_category": {"en-US": {"Cardinal": _metrics()}},
        "gate_metrics": {"owned": {"cases": 1}},
        "diagnostic_aggregates": {"by_outcome": {"semantic-mismatch": 1}},
        "outcome_counts": {"semantic-mismatch": 1},
        "risk_tier_counts": {"low": 1},
        "quarantine_reason_codes": {},
        "numeric_gate": {"reviewed_cases": 1, "failure_count": 1, "failure_case_ids": ["en-US:1"]},
        "candidate_oracle": {
            "schema_version": 1,
            "enabled": True,
            "cases": 1,
            "eligible_cases": 1,
            "scorable_cases": 1,
            "selection_gap_count": 0,
            "fully_recoverable_selection_gap_count": 0,
            "selector_regret_mean": 0.0,
            "candidate_recall_for_exact_target": 1.0,
        },
    }
    rows = [
        {
            "id": "en-US:1",
            "polynorm_locale": "en-US",
            "category": "Cardinal",
            "canonical_category": "Cardinal",
            "original_text": "2",
            "expected": "two",
            "actual": "wrong",
            "outcome": "semantic-mismatch",
            "speech_wer": 1.0,
            "failure_family": "wrong-transform",
            "ownership": "owned",
            "risk_tier": "low",
            "primary_rule": "en.cardinal",
            "failure_phase": "structured_rendering",
            "render_mode": "cardinal",
            "winning_span": {"source": "2"},
            "structured_claimed": True,
            "claim_owner": "owned",
            "protected_reason": None,
            "quarantine": None,
            "source_rules": ["en.cardinal"],
            "changed_stages": ["structured"],
            "literal_exact": False,
            "speech_exact": False,
            "error": None,
        }
    ]
    return summary, rows


def test_polynorm_report_renders_all_required_sections(tmp_path):
    summary, rows = fixture()
    text = render_report(summary, rows, tmp_path / "report.html").read_text(encoding="utf-8")
    assert "PolyNorm diagnostic benchmark" in text
    assert "Canonical-category table" in text
    assert "Locale × category view" in text
    assert "Failure explorer" in text
    assert "Optional oracle view" in text


def test_polynorm_report_escapes_source_text(tmp_path):
    summary, rows = fixture()
    rows[0]["original_text"] = "</script><script>alert(1)</script>"
    text = render_report(summary, rows, tmp_path / "report.html").read_text(encoding="utf-8")
    assert "</script><script>alert(1)</script>" not in text
    assert "&lt;/script&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in text
