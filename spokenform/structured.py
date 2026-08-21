"""Provider-neutral structured written-to-spoken normalization."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .casing import capitalize_generated_numeric_replacements
from .config import (
    GenericAcronymCase,
    GenericAcronymMode,
    InterpretationMode,
    RecognitionDomain,
)
from .diagnostics import TraceCollector
from .evidence import EvidenceSession
from .language import base_language, normalize_language
from .mapping import Replacement, resolve_replacements
from .models import ReservedSpan
from .recognition_policy import PolicySuppression, annotate_candidate, filter_candidates


@dataclass(frozen=True, slots=True)
class StageResult:
    """The exact replacements produced by one structured stage."""

    text: str
    replacements: tuple[Replacement, ...]
    reserved: tuple[ReservedSpan, ...] = ()
    suppressed: tuple[PolicySuppression, ...] = ()


def _iter_locale_replacements(
    text: str,
    *,
    language: str,
    protected_ranges: tuple[tuple[int, int], ...],
) -> tuple[Replacement, ...]:
    """Collect locale-specific structured candidates with the production imports."""
    base = base_language(language)
    if base == "en":
        from .locales.en import iter_replacements

        return iter_replacements(text, language=language, protected_ranges=protected_ranges)
    if base == "de":
        from .locales.de import iter_replacements

        return iter_replacements(text, language=language, protected_ranges=protected_ranges)
    if base == "fr":
        from .locales.fr import iter_replacements

        return iter_replacements(text, language=language, protected_ranges=protected_ranges)
    if base == "es":
        from .locales.es import iter_replacements

        return iter_replacements(text, language=language, protected_ranges=protected_ranges)
    if base == "it":
        from .locales.it import iter_replacements

        return iter_replacements(text, language=language, protected_ranges=protected_ranges)
    if base == "pt":
        from .locales.pt import iter_replacements as iter_portuguese_replacements

        return iter_portuguese_replacements(
            text, language=language, protected_ranges=protected_ranges
        )
    if base == "cs":
        from .locales.cs import iter_replacements

        return iter_replacements(text, language=language, protected_ranges=protected_ranges)
    return ()


def iter_structured_candidates(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
    promote_literals: bool = False,
    generic_acronym_mode: GenericAcronymMode = "known_only",
    generic_acronym_case: GenericAcronymCase = "upper",
    interpretation_mode: InterpretationMode = InterpretationMode.CONTEXTUAL,
    evidence: EvidenceSession | None = None,
    trace: TraceCollector | None = None,
) -> tuple[Replacement, ...]:
    """Return all annotated structured candidates before policy and precedence."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    language = normalize_language(language)
    protected = tuple(protected_ranges)
    from .recognizers import iter_sequence_replacements

    shared_candidates = iter_sequence_replacements(
        text,
        language=language,
        protected_ranges=protected,
        promote_literals=promote_literals,
        generic_acronym_mode=generic_acronym_mode,
        generic_acronym_case=generic_acronym_case,
        interpretation_mode=interpretation_mode,
        evidence=evidence,
        trace=trace,
    )
    locale_candidates = _iter_locale_replacements(
        text,
        language=language,
        protected_ranges=protected,
    )
    candidates = tuple(
        annotate_candidate(candidate) for candidate in (*shared_candidates, *locale_candidates)
    )
    if trace is not None:
        for candidate in candidates:
            trace.record_emitted(text, candidate)
    return candidates


def resolve_structured_candidates(
    text: str,
    candidates: tuple[Replacement, ...],
    *,
    language: str,
    interpretation_mode: InterpretationMode = InterpretationMode.CONTEXTUAL,
    disabled_domains: frozenset[RecognitionDomain] = frozenset(),
    allowed_domains: frozenset[RecognitionDomain] | None = None,
    trace: TraceCollector | None = None,
) -> tuple[Replacement, ...]:
    """Resolve structured candidates after applying recognition policy."""
    eligible, suppressed = filter_candidates(
        candidates,
        interpretation_mode=interpretation_mode,
        disabled_domains=disabled_domains,
        allowed_domains=allowed_domains,
    )
    if trace is not None:
        for item in suppressed:
            trace.record_suppressed(text, item)
    resolved = resolve_replacements(eligible, source_length=len(text))
    return capitalize_generated_numeric_replacements(text, resolved, language=language)


def iter_structured_replacements(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
    promote_literals: bool = False,
    generic_acronym_mode: GenericAcronymMode = "known_only",
    generic_acronym_case: GenericAcronymCase = "upper",
    interpretation_mode: InterpretationMode = InterpretationMode.CONTEXTUAL,
    disabled_domains: frozenset[RecognitionDomain] = frozenset(),
    allowed_domains: frozenset[RecognitionDomain] | None = None,
    evidence: EvidenceSession | None = None,
    trace: TraceCollector | None = None,
) -> tuple[Replacement, ...]:
    """Return exact, non-overlapping semantic replacements for one language."""
    candidates = iter_structured_candidates(
        text,
        language=language,
        protected_ranges=protected_ranges,
        promote_literals=promote_literals,
        generic_acronym_mode=generic_acronym_mode,
        generic_acronym_case=generic_acronym_case,
        interpretation_mode=interpretation_mode,
        evidence=evidence,
        trace=trace,
    )
    return resolve_structured_candidates(
        text,
        candidates,
        language=normalize_language(language),
        interpretation_mode=interpretation_mode,
        disabled_domains=disabled_domains,
        allowed_domains=allowed_domains,
        trace=trace,
    )


def normalize_structured(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
    promote_literals: bool = False,
    generic_acronym_mode: GenericAcronymMode = "known_only",
    generic_acronym_case: GenericAcronymCase = "upper",
    interpretation_mode: InterpretationMode = InterpretationMode.CONTEXTUAL,
    disabled_domains: frozenset[RecognitionDomain] = frozenset(),
    allowed_domains: frozenset[RecognitionDomain] | None = None,
    evidence: EvidenceSession | None = None,
    trace: TraceCollector | None = None,
) -> StageResult:
    """Normalize structured values and return exact semantic provenance."""
    candidates = iter_structured_candidates(
        text,
        language=language,
        protected_ranges=protected_ranges,
        promote_literals=promote_literals,
        generic_acronym_mode=generic_acronym_mode,
        generic_acronym_case=generic_acronym_case,
        interpretation_mode=interpretation_mode,
        evidence=evidence,
        trace=trace,
    )
    eligible, suppressed = filter_candidates(
        candidates,
        interpretation_mode=interpretation_mode,
        disabled_domains=disabled_domains,
        allowed_domains=allowed_domains,
    )
    if trace is not None:
        for item in suppressed:
            trace.record_suppressed(text, item)
    replacements = capitalize_generated_numeric_replacements(
        text,
        resolve_replacements(eligible, source_length=len(text)),
        language=language,
    )
    from .mapping import apply_replacements

    result, mapped_edits, offset_map = apply_replacements(text, replacements, stage="structured")
    reserved = [
        ReservedSpan(
            start=edit.output_start,
            end=edit.output_end,
            owner="structured-generated",
            reason=edit.rule or "accepted structured replacement",
        )
        for edit in mapped_edits
        if edit.output_start < edit.output_end
    ]
    for item in suppressed:
        start, end = offset_map.map_source_span(item.start, item.end)
        if start >= end:
            continue
        if any(existing.start < end and start < existing.end for existing in reserved):
            continue
        reserved.append(
            ReservedSpan(
                start=start,
                end=end,
                owner="structured-policy",
                reason=item.reason,
            )
        )
    return StageResult(result, replacements, tuple(reserved), suppressed)


__all__ = [
    "StageResult",
    "iter_structured_candidates",
    "iter_structured_replacements",
    "normalize_structured",
    "resolve_structured_candidates",
]
