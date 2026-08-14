from __future__ import annotations

import json

from benchmarks.compare_common import compare_runs


def _write_run(root, rows, summary):
    root.mkdir()
    (root / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    (root / "rows.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


def test_compare_reports_outcome_class_and_stable_id_deltas(tmp_path) -> None:
    before = tmp_path / "before"
    after = tmp_path / "after"
    before_rows = [
        {"id": "en:099:000001", "speech_exact": False, "presentation_only": False},
        {"record_type": "span", "semiotic_class": "DATE", "normalization_outcome": "wrong-transform"},
    ]
    after_rows = [
        {"id": "en:099:000001", "speech_exact": True, "presentation_only": False},
        {"record_type": "span", "semiotic_class": "DATE", "normalization_outcome": "correct-transform"},
    ]
    _write_run(before, before_rows, {"evaluated": 1, "speech_exact": 0, "transform_miss_count": 0, "wrong_transform_count": 1, "identity_mutation_count": 0})
    _write_run(after, after_rows, {"evaluated": 1, "speech_exact": 1, "transform_miss_count": 0, "wrong_transform_count": 0, "identity_mutation_count": 0})
    result = compare_runs(before, after)
    assert result["resolved_ids"] == ["en:099:000001"]
    assert result["new_failure_ids"] == []
    assert result["outcome_delta"] == {"correct-transform": 1, "wrong-transform": -1}
    assert result["aggregate_delta"]["speech_exact"] == 1
