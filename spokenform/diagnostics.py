"""Internal diagnostics for structured candidate generation."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from .config import GenericAcronymCase, GenericAcronymMode
from .mapping import Replacement

TraceStatus = Literal["emitted", "rejected", "protected", "shadowed"]


@dataclass(frozen=True, slots=True)
class CandidateTrace:
    """Stable diagnostics record for one structured candidate decision."""

    rule: str
    family: str
    start: int
    end: int
    source: str
    status: TraceStatus
    reject_reason: str | None = None
    rendered_text: str | None = None
    priority: int | None = None


class TraceCollector:
    """Mutable sink used only by diagnostics-enabled structured scans."""

    def __init__(self) -> None:
        self._records: list[CandidateTrace] = []

    @property
    def records(self) -> tuple[CandidateTrace, ...]:
        return tuple(self._records)

    def record_emitted(self, text: str, candidate: Replacement) -> None:
        self._records.append(
            CandidateTrace(
                rule=candidate.rule or "unknown",
                family=_family_for_rule(candidate.rule),
                start=candidate.start,
                end=candidate.end,
                source=text[candidate.start : candidate.end],
                status="emitted",
                rendered_text=candidate.text,
                priority=candidate.specificity,
            )
        )

    def record_rejected(
        self,
        *,
        rule: str,
        family: str,
        start: int,
        end: int,
        source: str,
        reason: str,
        status: TraceStatus = "rejected",
    ) -> None:
        self._records.append(
            CandidateTrace(
                rule=rule,
                family=family,
                start=start,
                end=end,
                source=source,
                status=status,
                reject_reason=reason,
            )
        )

    def mark_shadowed(self, resolved: tuple[Replacement, ...]) -> None:
        selected = {(item.start, item.end, item.rule, item.text) for item in resolved}
        updated: list[CandidateTrace] = []
        for record in self._records:
            key = (record.start, record.end, record.rule, record.rendered_text)
            if record.status == "emitted" and key not in selected:
                updated.append(replace(record, status="shadowed", reject_reason="overlap"))
            else:
                updated.append(record)
        self._records = updated


def _family_for_rule(rule: str | None) -> str:
    value = (rule or "").casefold()
    if "year" in value or "range" in value:
        return "year/range"
    if ".date" in value:
        return "date"
    return value.split(".", 1)[0] if value else "unknown"


def trace_structured_candidates(
    text: str,
    *,
    language: str,
    protected_ranges: tuple[tuple[int, int], ...] = (),
    promote_literals: bool = False,
    generic_acronym_mode: GenericAcronymMode = "known_only",
    generic_acronym_case: GenericAcronymCase = "upper",
) -> tuple[CandidateTrace, ...]:
    """Collect candidate, rejection, protection, and shadowing evidence."""
    from .structured import iter_structured_candidates, resolve_structured_candidates

    collector = TraceCollector()
    candidates = iter_structured_candidates(
        text,
        language=language,
        protected_ranges=protected_ranges,
        promote_literals=promote_literals,
        generic_acronym_mode=generic_acronym_mode,
        generic_acronym_case=generic_acronym_case,
        trace=collector,
    )
    resolved = resolve_structured_candidates(text, candidates, language=language)
    collector.mark_shadowed(resolved)
    return collector.records


__all__ = [
    "CandidateTrace",
    "TraceCollector",
    "TraceStatus",
    "trace_structured_candidates",
]
