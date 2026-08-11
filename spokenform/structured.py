"""Provider-neutral structured written-to-spoken normalization."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .language import base_language, normalize_language
from .mapping import Replacement, resolve_replacements
from .models import ReservedSpan


@dataclass(frozen=True, slots=True)
class StageResult:
    """The exact replacements produced by one structured stage."""

    text: str
    replacements: tuple[Replacement, ...]
    reserved: tuple[ReservedSpan, ...] = ()


def iter_structured_replacements(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
    promote_literals: bool = False,
) -> tuple[Replacement, ...]:
    """Return exact, non-overlapping semantic replacements for one language."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    language = normalize_language(language)
    base = base_language(language)
    protected = tuple(protected_ranges)
    from .recognizers import iter_sequence_replacements

    shared_candidates = iter_sequence_replacements(
        text, language=language, protected_ranges=protected, promote_literals=promote_literals
    )
    if base == "en":
        from .locales.en import iter_replacements

        candidates = iter_replacements(text, language=language, protected_ranges=protected)
    elif base == "de":
        from .locales.de import iter_replacements

        candidates = iter_replacements(text, language=language, protected_ranges=protected)
    elif base == "fr":
        from .locales.fr import iter_replacements

        candidates = iter_replacements(text, language=language, protected_ranges=protected)
    elif base == "es":
        from .locales.es import iter_replacements

        candidates = iter_replacements(text, language=language, protected_ranges=protected)
    elif base == "it":
        from .locales.it import iter_replacements

        candidates = iter_replacements(text, language=language, protected_ranges=protected)
    elif base == "pt":
        from .locales.pt import iter_replacements as iter_portuguese_replacements

        candidates = iter_portuguese_replacements(
            text, language=language, protected_ranges=protected
        )
    elif base == "cs":
        from .locales.cs import iter_replacements

        candidates = iter_replacements(text, language=language, protected_ranges=protected)
    else:
        return ()
    return resolve_replacements((*shared_candidates, *candidates), source_length=len(text))


def normalize_structured(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
    promote_literals: bool = False,
) -> StageResult:
    """Normalize structured values and return exact semantic provenance."""
    replacements = iter_structured_replacements(
        text, language=language, protected_ranges=protected_ranges
        , promote_literals=promote_literals
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


__all__ = ["StageResult", "iter_structured_replacements", "normalize_structured"]
