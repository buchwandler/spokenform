"""Provider-neutral structured written-to-spoken normalization."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from .mapping import Replacement, resolve_replacements


@dataclass(frozen=True, slots=True)
class StageResult:
    """The exact replacements produced by one structured stage."""

    text: str
    replacements: tuple[Replacement, ...]
    reserved: tuple[tuple[int, int], ...] = ()


def _base_language(language: str) -> str:
    return language.strip().lower().replace("_", "-").split("-", 1)[0]


def iter_structured_replacements(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return exact, non-overlapping semantic replacements for one language."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    base = _base_language(language)
    protected = tuple(protected_ranges)
    if base == "de":
        from .locales.de import iter_replacements
    elif base == "fr":
        from .locales.fr import iter_replacements
    elif base == "es":
        from .locales.es import iter_replacements
    else:
        return ()

    candidates = iter_replacements(text, protected_ranges=protected)
    return resolve_replacements(candidates, source_length=len(text))


def normalize_structured(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> StageResult:
    """Normalize structured values and return exact semantic provenance."""
    replacements = iter_structured_replacements(
        text, language=language, protected_ranges=protected_ranges
    )
    from .mapping import apply_replacements

    result, _, _ = apply_replacements(text, replacements, stage="structured")
    return StageResult(result, replacements)


__all__ = ["StageResult", "iter_structured_replacements", "normalize_structured"]
