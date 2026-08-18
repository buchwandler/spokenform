from __future__ import annotations

from benchmarks.async_tn_report import DEFAULT_MIN_UNITS, render_report


def fixture():
    summary = {
        "benchmark": "async_tn",
        "run_id": "run-1",
        "profile": "default",
        "dataset_commit": "commit",
        "source": {"files": {"data/sentences.json": {"sha256": "hash"}}},
        "environment": {
            "spokenform_version": "test",
            "spokenform_source_commit": "source",
            "config_hash": "config",
            "configuration": {"suite": "all"},
        },
        "counts": {
            "units_total": 31,
            "units_scorable": 30,
            "units_quarantined": 1,
            "runtime_error_cases": 0,
        },
        "sentence_metrics": {"speech_equivalent": 1, "total": 1},
        "unit_metrics": {"accuracy": 1.0, "mean_speech_wer": 0.0},
        "categories": {
            "date": {"units_total": 31, "units_scorable": 30, "accuracy": 1.0},
            "future_category": {"units_total": 1, "units_scorable": 1, "accuracy": 0.0},
        },
        "languages": {"en": {}},
        "language_categories": {
            "en": {"date": {"units_total": 31, "units_scorable": 30, "accuracy": 1.0}}
        },
    }
    reference = {
        "source_commit": "commit",
        "english": {
            "categories": {
                "min_units": 30,
                "model_order": [{"model_id": "async", "display_name": "Async Flash"}],
                "categories": [{"category": "date", "models": {"async": {"accuracy": 0.9}}}],
            }
        },
        "multilingual": {
            "categories": {
                "model_order": [{"model_id": "en", "display_name": "English"}],
                "categories": [{"category": "date", "models": {"en": {"accuracy": 0.8}}}],
            }
        },
    }
    rows = [{"case_id": "english:1", "original_text": "date", "expected": "date", "actual": "date"}]
    units = [
        {
            "unit_id": "english:1:unit:0",
            "suite": "english",
            "source_language": "en",
            "category": "date",
            "source_text": "5",
            "expected": "five",
            "actual": "five",
            "outcome": "correct-transform",
            "failure_family": "",
            "ownership": "owned",
            "risk_tier": "low",
            "expected_mapping_ambiguous": False,
            "actual_mapping_ambiguous": False,
        }
    ]
    return summary, rows, units, reference


def test_report_is_self_contained_with_all_views(tmp_path):
    summary, rows, units, reference = fixture()
    path = render_report(summary, rows, units, reference, tmp_path / "report.html")
    text = path.read_text(encoding="utf-8")
    assert "English Benchmark" in text
    assert "Multilingual" in text
    assert "Failures" in text
    assert "Run Metadata" in text
    assert "https://" not in text
    assert "cdn" not in text.lower()
    assert "Async Flash" in text
    assert "90.00%" in text
    assert "not a like-for-like model ranking" in text
    assert "winner" not in text.lower()


def test_report_uses_default_threshold_and_show_all_control(tmp_path):
    summary, rows, units, reference = fixture()
    text = render_report(summary, rows, units, reference, tmp_path / "report.html").read_text()
    assert DEFAULT_MIN_UNITS == 30
    assert 'id="show-all"' in text
    assert 'data-units="1"' in text
    assert "selected>30</option>" in text
    assert "future_category" in text


def test_report_escapes_untrusted_dataset_text(tmp_path):
    summary, rows, units, reference = fixture()
    units[0]["source_text"] = "</script><script>alert(1)</script>"
    units[0]["expected"] = 'a & b < c "quoted"'
    units[0]["outcome"] = "wrong-transform"
    text = render_report(summary, rows, units, reference, tmp_path / "report.html").read_text()
    assert "</script><script>alert(1)</script>" not in text
    assert "&lt;/script&gt;&lt;script&gt;alert(1)&lt;/script&gt;" in text
    assert "a &amp; b &lt; c &quot;quoted&quot;" in text


def test_report_values_are_taken_from_summary_and_reference(tmp_path):
    summary, rows, units, reference = fixture()
    summary["categories"]["date"]["accuracy"] = 0.75
    reference["english"]["categories"]["categories"][0]["models"]["async"]["accuracy"] = 0.65
    text = render_report(summary, rows, units, reference, tmp_path / "report.html").read_text()
    assert "75.00%" in text
    assert "65.00%" in text
