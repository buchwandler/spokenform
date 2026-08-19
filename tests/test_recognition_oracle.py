from __future__ import annotations

from benchmarks.recognition_oracle import (
    analysis_fields,
    analyze_recognition_oracle,
    oracle_aggregates,
)
from spokenform.diagnostics import trace_structured_candidates


def test_recognition_oracle_distinguishes_rejection_and_missing_recognition() -> None:
    rejected_traces = trace_structured_candidates("version 2024.1", language="en")
    rejected = analyze_recognition_oracle("version 2024.1", rejected_traces)
    assert rejected.gap_type == "rejection-gap"
    assert "invalid-boundary" in rejected.rejection_reasons

    missing_traces = trace_structured_candidates("1989", language="en")
    missing = analyze_recognition_oracle("1989", missing_traces)
    assert missing.gap_type == "rejection-gap"
    assert analysis_fields(missing)["recognition_rejected_count"] == 1


def test_recognition_oracle_aggregates_reason_codes() -> None:
    rows = [
        {
            **analysis_fields(
                analyze_recognition_oracle(
                    "version 2024.1",
                    trace_structured_candidates("version 2024.1", language="en"),
                )
            ),
        },
    ]

    summary = oracle_aggregates(rows)

    assert summary["cases"] == 1
    assert summary["recognition_gap_counts"] == {"rejection-gap": 1}
    assert summary["rejection_reason_counts"] == {"invalid-boundary": 1}
