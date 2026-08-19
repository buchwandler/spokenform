from __future__ import annotations

from benchmarks.proteno_report import render_report


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
        "benchmark": "Proteno",
        "generated_at": "2026-08-18T00:00:00Z",
        "dataset_commit": "commit",
        "profile": "default",
        "cases": 1,
        "normalization_cases": 1,
        "identity_cases": 0,
        "speech_exact_count": 0,
        "speech_exact_rate": 0.0,
        "speech_exact_equivalent_count": 0,
        "speech_exact_equivalent_rate": 0.0,
        "semantic_failure_count": 1,
        "excluded_count": 0,
        "mean_speech_wer": 0.5,
        "normalization_success_count": 0,
        "normalization_success_rate": 0.0,
        "normalization_unchanged_miss_count": 0,
        "identity_preserved_count": 0,
        "identity_preservation_rate": 0.0,
        "identity_mutation_count": 0,
        "by_language": {"en": _metrics()},
        "by_language_case_kind": {"en": {"normalization": _metrics()}},
        "gate_metrics": {"owned": {"cases": 1}},
        "diagnostic_aggregates": {"by_outcome": {"semantic-mismatch": 1}},
        "outcome_counts": {"semantic-mismatch": 1},
        "risk_tier_counts": {"low": 1},
        "excluded_by_reason": {},
        "excluded_by_reason_code": {},
        "source_file_git_blobs": {"en": {"norm_list": "sha"}},
        "source_file_sizes": {"en": {"norm_list": 1}},
        "environment": {"configuration": {"profile": "default"}},
        "identity": {"config_hash": "hash"},
        "failure_reports": {"index": "failures.md"},
        "candidate_oracle": {
            "schema_version": 2,
            "enabled": True,
            "cases": 1,
            "eligible_cases": 1,
            "eligible_semantic_failure_count": 1,
            "scorable_cases": 1,
            "selection_gap_count": 0,
            "selection_gap_rate": 0.0,
            "fully_recoverable_selection_gap_count": 0,
            "fully_recoverable_selection_gap_rate": 0.0,
            "selector_regret_mean": 0.0,
            "candidate_recall_for_exact_target": 1.0,
        },
    }
    rows = [
        {
            "id": "en:00001",
            "proteno_language": "en",
            "split": "train",
            "case_kind": "normalization",
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
            "projection_notes": [],
            "had_lang_span": False,
            "had_error_span": False,
            "source_rules": ["en.cardinal"],
            "changed_stages": ["structured"],
            "literal_exact": False,
            "speech_exact": False,
            "error": None,
        }
    ]
    return summary, rows


def test_proteno_report_renders_all_required_sections(tmp_path):
    summary, rows = fixture()
    text = render_report(summary, rows, tmp_path / "report.html").read_text(encoding="utf-8")
    assert "Proteno benchmark" in text
    assert "Normalization / identity view" in text
    assert "Language × case-kind view" in text
    assert "Failure explorer" in text
    assert "Optional oracle view" in text
    assert "Selection gap rate is selection gaps divided by eligible semantic failures." in text
    assert "selection_gap_rate" in text
    assert "fully_recoverable_selection_gap_rate" in text


def test_proteno_report_escapes_source_text(tmp_path):
    summary, rows = fixture()
    rows[0]["original_text"] = "</script><script>alert(1)</script>"
    text = render_report(summary, rows, tmp_path / "report.html").read_text(encoding="utf-8")
    assert "</script><script>alert(1)</script>" not in text
    assert "&lt;/script&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in text
