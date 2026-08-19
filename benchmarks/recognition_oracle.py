"""Benchmark-side aggregation of Spokenform candidate recognition traces."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from spokenform.diagnostics import CandidateTrace


@dataclass(frozen=True, slots=True)
class RecognitionOracleAnalysis:
    """One row's recognition and rejection evidence."""

    enabled: bool
    trace_count: int
    emitted_count: int
    rejected_count: int
    protected_count: int
    shadowed_count: int
    gap_type: str
    rejection_reasons: tuple[str, ...]
    matched_failure_span: tuple[int, int] | None


def analyze_recognition_oracle(
    source: str,
    traces: tuple[CandidateTrace, ...],
    *,
    failure_span: tuple[int, int] | None = None,
) -> RecognitionOracleAnalysis:
    """Classify missing and rejected candidates without modifying runtime output."""
    relevant = tuple(
        trace
        for trace in traces
        if failure_span is None or trace.start < failure_span[1] and failure_span[0] < trace.end
    )
    emitted = sum(trace.status == "emitted" for trace in relevant)
    rejected = sum(trace.status == "rejected" for trace in relevant)
    protected = sum(trace.status == "protected" for trace in relevant)
    shadowed = sum(trace.status == "shadowed" for trace in relevant)
    reasons = tuple(
        sorted({trace.reject_reason for trace in relevant if trace.reject_reason is not None})
    )
    if protected:
        gap_type = "protected-gap"
    elif rejected:
        gap_type = "rejection-gap"
    elif emitted or shadowed:
        gap_type = "candidate-present"
    else:
        gap_type = "recognition-gap"
    return RecognitionOracleAnalysis(
        enabled=True,
        trace_count=len(relevant),
        emitted_count=emitted,
        rejected_count=rejected,
        protected_count=protected,
        shadowed_count=shadowed,
        gap_type=gap_type,
        rejection_reasons=reasons,
        matched_failure_span=failure_span,
    )


def analysis_fields(analysis: RecognitionOracleAnalysis) -> dict[str, Any]:
    """Flatten recognition evidence for benchmark rows."""
    return {
        "recognition_oracle_enabled": analysis.enabled,
        "recognition_trace_count": analysis.trace_count,
        "recognition_emitted_count": analysis.emitted_count,
        "recognition_rejected_count": analysis.rejected_count,
        "recognition_protected_count": analysis.protected_count,
        "recognition_shadowed_count": analysis.shadowed_count,
        "recognition_gap_type": analysis.gap_type,
        "recognition_rejection_reasons": list(analysis.rejection_reasons),
        "recognition_failure_span": list(analysis.matched_failure_span)
        if analysis.matched_failure_span is not None
        else None,
    }


def oracle_aggregates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate recognition, rejection, protection, and shadowing evidence."""
    enabled = [row for row in rows if row.get("recognition_oracle_enabled")]
    gap_counts = Counter(str(row.get("recognition_gap_type")) for row in enabled)
    reasons = Counter(
        reason for row in enabled for reason in row.get("recognition_rejection_reasons", ())
    )
    return {
        "schema_version": 1,
        "enabled": bool(enabled),
        "cases": len(enabled),
        "recognition_gap_counts": dict(sorted(gap_counts.items())),
        "rejection_reason_counts": dict(sorted(reasons.items())),
        "trace_count": sum(int(row.get("recognition_trace_count", 0)) for row in enabled),
        "emitted_count": sum(int(row.get("recognition_emitted_count", 0)) for row in enabled),
        "rejected_count": sum(int(row.get("recognition_rejected_count", 0)) for row in enabled),
        "protected_count": sum(int(row.get("recognition_protected_count", 0)) for row in enabled),
        "shadowed_count": sum(int(row.get("recognition_shadowed_count", 0)) for row in enabled),
    }


__all__ = [
    "RecognitionOracleAnalysis",
    "analysis_fields",
    "analyze_recognition_oracle",
    "oracle_aggregates",
    "trace_source_fields",
]


def trace_source_fields(
    source: str,
    *,
    language: str,
    protected_ranges: tuple[tuple[int, int], ...] = (),
    failure_span: tuple[int, int] | None = None,
) -> dict[str, Any]:
    """Trace one source string through the diagnostics-only runtime entrypoint."""
    from spokenform.diagnostics import trace_structured_candidates

    traces = trace_structured_candidates(
        source,
        language=language,
        protected_ranges=protected_ranges,
    )
    return analysis_fields(analyze_recognition_oracle(source, traces, failure_span=failure_span))
