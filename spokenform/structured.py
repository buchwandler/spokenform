"""Provider-neutral structured written-to-spoken normalization."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .casing import capitalize_generated_numeric_replacements
from .config import GenericAcronymCase, GenericAcronymMode
from .diagnostics import TraceCollector
from .language import base_language, normalize_language
from .mapping import Replacement, resolve_replacements
from .models import ReservedSpan


@dataclass(frozen=True, slots=True)
class StageResult:
    """The exact replacements produced by one structured stage."""

    text: str
    replacements: tuple[Replacement, ...]
    reserved: tuple[ReservedSpan, ...] = ()


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
    trace: TraceCollector | None = None,
) -> tuple[Replacement, ...]:
    """Return all admissible structured candidates before conflict resolution."""
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
        trace=trace,
    )
    locale_candidates = _iter_locale_replacements(
        text,
        language=language,
        protected_ranges=protected,
    )
    candidates = (*shared_candidates, *locale_candidates)
    if trace is not None:
        for candidate in candidates:
            trace.record_emitted(text, candidate)
    return candidates


def resolve_structured_candidates(
    text: str,
    candidates: tuple[Replacement, ...],
    *,
    language: str,
) -> tuple[Replacement, ...]:
    """Resolve structured candidates using the production structured policy."""
    resolved = resolve_replacements(candidates, source_length=len(text))
    return capitalize_generated_numeric_replacements(text, resolved, language=language)


def iter_structured_replacements(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
    promote_literals: bool = False,
    generic_acronym_mode: GenericAcronymMode = "known_only",
    generic_acronym_case: GenericAcronymCase = "upper",
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
        trace=trace,
    )
    return resolve_structured_candidates(text, candidates, language=normalize_language(language))


def normalize_structured(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
    promote_literals: bool = False,
    generic_acronym_mode: GenericAcronymMode = "known_only",
    generic_acronym_case: GenericAcronymCase = "upper",
    trace: TraceCollector | None = None,
) -> StageResult:
    """Normalize structured values and return exact semantic provenance."""
    replacements = iter_structured_replacements(
        text,
        language=language,
        protected_ranges=protected_ranges,
        promote_literals=promote_literals,
        generic_acronym_mode=generic_acronym_mode,
        generic_acronym_case=generic_acronym_case,
        trace=trace,
    )
    from .mapping import apply_replacements

    result, mapped_edits, _ = apply_replacements(text, replacements, stage="structured")
    reserved = tuple(
        ReservedSpan(
            start=edit.output_start,
            end=edit.output_end,
            owner="structured-generated",
            reason=edit.rule or "accepted structured replacement",
        )
        for edit in mapped_edits
        if edit.output_start < edit.output_end
    )
    return StageResult(result, replacements, reserved)


__all__ = [
    "StageResult",
    "iter_structured_candidates",
    "iter_structured_replacements",
    "normalize_structured",
    "resolve_structured_candidates",
]
