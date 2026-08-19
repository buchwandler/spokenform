from __future__ import annotations

from spokenform.diagnostics import trace_structured_candidates


def test_year_trace_records_emitted_and_rejected_candidates() -> None:
    emitted = trace_structured_candidates("in 1989.", language="en")
    assert any(record.status == "emitted" and record.rule == "sequence.year" for record in emitted)
    assert not any(record.status == "rejected" for record in emitted)

    rejected = trace_structured_candidates("version 2024.1", language="en")
    assert any(
        record.status == "rejected"
        and record.rule == "sequence.year"
        and record.reject_reason == "invalid-boundary"
        for record in rejected
    )


def test_year_trace_distinguishes_missing_context() -> None:
    records = trace_structured_candidates("1989", language="en")
    assert any(
        record.status == "rejected" and record.reject_reason == "missing-context"
        for record in records
    )


def test_trace_marks_shadowed_candidates_without_changing_candidates() -> None:
    records = trace_structured_candidates("2 kg", language="fr")
    assert any(record.status == "emitted" for record in records)
    assert any(record.status == "shadowed" for record in records)
