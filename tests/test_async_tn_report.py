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
        "sentence_metrics": {"speech_equivalent": 1, "total": 2},
        "unit_metrics": {"accuracy": 0.5, "mean_speech_wer": 0.25},
        "categories": {
            "date": {"units_total": 31, "units_scorable": 30, "accuracy": 1.0},
            "future_category": {"units_total": 1, "units_scorable": 1, "accuracy": 0.0},
        },
        "languages": {"en": {}, "de": {}},
        "language_categories": {
            "en": {"date": {"units_total": 31, "units_scorable": 30, "accuracy": 1.0}},
            "de": {"date": {"units_total": 2, "units_scorable": 2, "accuracy": 0.5}},
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
    rows = [
        {
            "case_id": "english:1",
            "suite": "english",
            "source_language": "en",
            "categories": ["date"],
            "original_text": "Pay 5.",
            "expected": "Pay five.",
            "actual": "Pay wrong.",
            "outcome": "semantic-failure",
            "speech_equivalent": False,
            "speech_wer": 0.5,
            "failure_family": "wrong-transform",
            "ownership": "owned",
            "risk_tier": "low",
            "source_rules": ["en.cardinal"],
            "changed_stages": ["structured"],
            "error": None,
        },
        {
            "case_id": "english:2",
            "suite": "english",
            "source_language": "en",
            "categories": ["time"],
            "original_text": "7 AM",
            "expected": "seven A M",
            "actual": "seven A M",
            "outcome": "correct",
            "speech_equivalent": True,
            "speech_wer": 0.0,
            "failure_family": "",
            "ownership": "owned",
            "risk_tier": "low",
            "source_rules": ["en.cardinal"],
            "changed_stages": ["structured"],
            "error": None,
        },
    ]
    units = [
        {
            "unit_id": "english:1:unit:0",
            "case_id": "english:1",
            "suite": "english",
            "source_language": "en",
            "category": "date",
            "source_text": "5",
            "expected": "five",
            "actual": "wrong",
            "outcome": "wrong-transform",
            "speech_wer": 1.0,
            "failure_family": "wrong-transform",
            "ownership": "owned",
            "risk_tier": "low",
            "expected_mapping_ambiguous": False,
            "actual_mapping_ambiguous": False,
            "source_rules": ["en.cardinal"],
            "changed_stages": ["structured"],
            "error": None,
        },
        {
            "unit_id": "english:2:unit:0",
            "case_id": "english:2",
            "suite": "english",
            "source_language": "en",
            "category": "time",
            "source_text": "AM",
            "expected": "A M",
            "actual": "seven A M",
            "outcome": "mapping-ambiguous",
            "speech_wer": 1.0,
            "failure_family": "mapping-ambiguous",
            "ownership": "owned",
            "risk_tier": "low",
            "expected_mapping_ambiguous": False,
            "actual_mapping_ambiguous": True,
            "source_rules": ["en.clock-period"],
            "changed_stages": ["structured"],
            "error": None,
        },
    ]
    return summary, rows, units, reference


def test_report_is_self_contained_with_all_views(tmp_path):
    summary, rows, units, reference = fixture()
    path = render_report(summary, rows, units, reference, tmp_path / "report.html")
    text = path.read_text(encoding="utf-8")
    assert "English Benchmark" in text
    assert "Multilingual" in text
    assert "Failure explorer" in text
    assert "Sentence failures" in text
    assert "Unit diagnostics" in text
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
    rows[0]["original_text"] = "</script><script>alert(1)</script>"
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


def test_report_labels_sentence_and_projection_values_separately(tmp_path):
    summary, rows, units, reference = fixture()
    text = render_report(summary, rows, units, reference, tmp_path / "report.html").read_text()
    assert "Sentence expected" in text
    assert "Sentence actual" in text
    assert "Projected expected" in text
    assert "Projected actual" in text
    assert "Ambiguous cross-unit projection" in text
    assert "Projected actual is available in Details as diagnostic text only." in text
    assert "seven A M" in text
