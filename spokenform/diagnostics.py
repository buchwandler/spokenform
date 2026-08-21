"""Supported diagnostics for structured and residual sequence decisions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal

from .config import (
    GenericAcronymCase,
    GenericAcronymMode,
    InterpretationMode,
    RecognitionDomain,
    SequenceFallbackMode,
)
from .evidence import EvidenceSession, LexicalEvidenceProvider, validate_provider
from .fallback import SequenceFallbackTrace, trace_sequence_fallback
from .mapping import Replacement

TraceStatus = Literal["emitted", "rejected", "protected", "shadowed", "suppressed"]


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
    domain: str | None = None
    evidence: str | None = None
    evidence_source: str | None = None
    evidence_score: float | None = None
    evidence_cues: tuple[str, ...] = ()
    policy_reason: str | None = None
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
                domain=candidate.recognition_domain,
                evidence=candidate.recognition_evidence,
                evidence_source=candidate.evidence_source,
                evidence_score=candidate.evidence_score,
                evidence_cues=candidate.evidence_cues,
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

    def record_suppressed(self, text: str, suppression: Any) -> None:
        self._records.append(
            CandidateTrace(
                rule=suppression.rule or "unknown",
                family=_family_for_rule(suppression.rule),
                start=suppression.start,
                end=suppression.end,
                source=text[suppression.start : suppression.end],
                status="suppressed",
                reject_reason=suppression.reason,
                domain=suppression.domain,
                evidence=suppression.evidence,
                policy_reason=suppression.reason,
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
    interpretation_mode: InterpretationMode = InterpretationMode.CONTEXTUAL,
    disabled_domains: frozenset[RecognitionDomain] = frozenset(),
    allowed_domains: frozenset[RecognitionDomain] | None = None,
    lexical_evidence: LexicalEvidenceProvider | None = None,
) -> tuple[CandidateTrace, ...]:
    """Collect candidate, rejection, protection, and shadowing evidence."""
    from .structured import iter_structured_candidates, resolve_structured_candidates

    validate_provider(lexical_evidence, language)
    evidence = EvidenceSession(lexical_evidence)
    collector = TraceCollector()
    candidates = iter_structured_candidates(
        text,
        language=language,
        protected_ranges=protected_ranges,
        promote_literals=promote_literals,
        generic_acronym_mode=generic_acronym_mode,
        generic_acronym_case=generic_acronym_case,
        interpretation_mode=interpretation_mode,
        evidence=evidence,
        trace=collector,
    )
    resolved = resolve_structured_candidates(
        text,
        candidates,
        language=language,
        interpretation_mode=interpretation_mode,
        disabled_domains=disabled_domains,
        allowed_domains=allowed_domains,
        trace=collector,
    )
    collector.mark_shadowed(resolved)
    return collector.records


__all__ = [
    "CandidateTrace",
    "TraceCollector",
    "TraceStatus",
    "trace_structured_candidates",
    "SequenceFallbackMode",
    "SequenceFallbackTrace",
    "trace_sequence_fallback",
]
