from __future__ import annotations

import json

import pytest

from benchmarks.async_tn_compare import compare_runs


def _write_run(root, *, profile="default", file_hash="hash", failed=False, suite="all"):
    root.mkdir()
    summary = {
        "benchmark": "async_tn",
        "profile": profile,
        "dataset_commit": "commit",
        "source": {"source_repo": "repo", "files": {"data/sentences.json": {"sha256": file_hash}}},
        "environment": {
            "dataset_repository": "repo",
            "dataset_commit": "commit",
            "locale_mapping": {"en": "en_US"},
            "configuration": {"suite": suite, "profile": profile, "normalize_literals": profile == "extended"},
        },
        "sentence_metrics": {"speech_equivalent": 0 if failed else 1},
        "unit_metrics": {"units_correct": 0 if failed else 1, "units_scorable": 1},
    }
    rows = [{
        "record_type": "sentence", "id": "english:1", "speech_equivalent": not failed,
        "error": None, "expected": "five", "actual": "wrong" if failed else "five",
    }]
    units = [{
        "record_type": "unit", "unit_id": "english:1:unit:0", "speech_equivalent": not failed,
        "scorable": True, "source_language": "en", "category": "cardinal",
        "expected": "five", "actual": "wrong" if failed else "five",
    }]
    (root / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (root / "rows.jsonl").write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")
    (root / "units.jsonl").write_text("\n".join(json.dumps(row) for row in units) + "\n", encoding="utf-8")


def test_compatible_runs_compare_stable_ids_and_deltas(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    _write_run(before, failed=True)
    _write_run(after, failed=False)
    result = compare_runs(before, after)
    assert result["identity"]["compatible"]
    assert result["case_delta"]["resolved"] == ["english:1"]
    assert result["unit_delta"]["resolved"] == ["english:1:unit:0"]
    assert result["category_delta"]["cardinal"]["correct"] == 1


@pytest.mark.parametrize(
    ("before_kwargs", "after_kwargs", "field"),
    [
        ({"file_hash": "a"}, {"file_hash": "b"}, "dataset_files"),
        ({"profile": "default"}, {"profile": "extended"}, "profile"),
        ({"suite": "english"}, {"suite": "multilingual"}, "suite"),
    ],
)
def test_incompatible_identity_is_rejected(tmp_path, before_kwargs, after_kwargs, field):
    before = tmp_path / "before"
    after = tmp_path / "after"
    _write_run(before, **before_kwargs)
    _write_run(after, **after_kwargs)
    with pytest.raises(ValueError, match="incompatible Async TN runs"):
        compare_runs(before, after)


def test_incompatible_override_is_explicit(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    _write_run(before, file_hash="a")
    _write_run(after, file_hash="b")
    result = compare_runs(before, after, allow_incompatible=True)
    assert result["identity"]["overridden"]
    assert "dataset_files" in result["identity"]["mismatches"]


def test_new_failures_and_quarantines_are_reported(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    _write_run(before, failed=False)
    _write_run(after, failed=True)
    result = compare_runs(before, after)
    assert result["case_delta"]["new_failures"] == ["english:1"]
    assert result["unit_delta"]["new_failures"] == ["english:1:unit:0"]
