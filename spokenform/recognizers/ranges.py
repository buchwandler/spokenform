"""Context-bound year and numeric-range recognizers."""

from __future__ import annotations

import re
from collections.abc import Iterable

from num2words import num2words

from ..dates import render_english_year
from ..language import base_language, normalize_language, resolve_num2words_language
from ..mapping import Replacement

_YEAR = r"(?:1[0-9]{3}|20[0-9]{2})"
_YEAR_RANGE_RE = re.compile(
    rf"(?<![\w./:-])(?P<start>{_YEAR})\s*[-–]\s*(?P<end>{_YEAR})(?![\w/:-])"
)
_NUMERIC_RANGE_RE = re.compile(
    r"(?<![\w./:-])(?P<start>\d{1,6})\s*[-–]\s*(?P<end>\d{1,6})(?![\w/:-])"
)
_PAREN_YEAR_RE = re.compile(rf"(?<=\()(?P<year>{_YEAR})(?=\))")
_KEYWORD_YEAR_RE = re.compile(
    rf"\b(?:in|since|during|year|anno|im\s+jahr|en|desde|durante|año|année|anno)\s+"
    rf"(?P<year>{_YEAR})(?![\w./:-])",
    re.IGNORECASE,
)
_LEADING_YEAR_RE = re.compile(rf"(?<!\w)(?P<year>{_YEAR})(?=\s+[A-ZÀ-ÖØ-Þ])")
_MONTH_YEAR_RE = re.compile(
    rf"\b(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    rf"enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|"
    rf"janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre)\s+"
    rf"(?P<year>{_YEAR})(?![\w./:-])",
    re.IGNORECASE,
)
_BIBLIO_YEAR_RE = re.compile(rf"(?:,\s*|\(\s*)(?P<year>{_YEAR})(?=\s*[),.;:]|$)")
_RANGE_CONTEXT_RE = re.compile(
    r"\b(?:from|between|range|pages?|pp\.?|lines?|chapter|section|von|zwischen|seiten?|de|entre|páginas?|da|tra|pagine?)\b",
    re.IGNORECASE,
)


def _cardinal(value: int, language: str) -> str:
    rendered = str(num2words(value, lang=resolve_num2words_language(language)))
    return rendered.replace(",", "").replace("-", " ").replace(" and ", " ")


def _year_text(value: int, language: str) -> str:
    if base_language(language) == "en":
        return render_english_year(value, language=language, source_digits=4)
    return _cardinal(value, language)


def _connector(language: str) -> str:
    return {
        "de": "bis",
        "es": "a",
        "fr": "à",
        "it": "a",
        "pt": "a",
        "cs": "až",
    }.get(base_language(language), "to")


def _claimed(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return not any(start < right and left < end for left, right in protected)


def _is_safe_numeric_range(value: str, start: int, end: int, text: str) -> bool:
    """Reject source shapes owned by another typed recognizer."""
    if re.search(r"[./:]", value):
        return False
    if re.fullmatch(r"\d{3}\s*[-–]\s*\d{4}", value) and not _RANGE_CONTEXT_RE.search(
        text[max(0, start - 48) : start]
    ):
        return False
    before = text[max(0, start - 24) : start]
    after = text[end : end + 24]
    if re.search(
        r"(?:isbn|version|release|serial|sku|model|product|vin|phone|tel)\b", before, re.I
    ):
        return False
    if re.search(r"\s[-–]\s*", value) and not _RANGE_CONTEXT_RE.search(before[-40:]):
        return False
    if re.search(r"\d\s*[-–]\s*$", before) or re.match(r"\s*[-–]\s*\d", after):
        return False
    left, right = (int(part) for part in re.split(r"\s*[-–]\s*", value))
    if left < 10 and right < 10 and not _RANGE_CONTEXT_RE.search(before[-40:]):
        return False
    return left <= 999999 and right <= 999999


def iter_replacements(
    text: str,
    *,
    language: str = "en",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return positive-evidence year and numeric-range replacements."""
    language = normalize_language(language)
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []

    for match in _YEAR_RANGE_RE.finditer(text):
        start, end = match.span()
        if not _claimed(start, end, protected):
            continue
        left, right = int(match["start"]), int(match["end"])
        if left >= 1800 and right >= 1800:
            candidates.append(
                Replacement(
                    start,
                    end,
                    f"{_year_text(left, language)} {_connector(language)} {_year_text(right, language)}",
                    "structured",
                    language,
                    "sequence.year-range",
                    76,
                )
            )

    for pattern in (
        _PAREN_YEAR_RE,
        _KEYWORD_YEAR_RE,
        _LEADING_YEAR_RE,
        _MONTH_YEAR_RE,
        _BIBLIO_YEAR_RE,
    ):
        for match in pattern.finditer(text):
            start, end = match.span("year")
            if _claimed(start, end, protected):
                value = int(match["year"])
                candidates.append(
                    Replacement(
                        start,
                        end,
                        _year_text(value, language),
                        "structured",
                        language,
                        "sequence.year",
                        72,
                    )
                )

    for match in _NUMERIC_RANGE_RE.finditer(text):
        start, end = match.span()
        if not _claimed(start, end, protected) or not _is_safe_numeric_range(
            match.group(0), start, end, text
        ):
            continue
        left, right = int(match["start"]), int(match["end"])
        candidates.append(
            Replacement(
                start,
                end,
                f"{_cardinal(left, language)} {_connector(language)} {_cardinal(right, language)}",
                "structured",
                language,
                "sequence.numeric-range",
                55,
            )
        )
    return tuple(candidates)


__all__ = ["iter_replacements"]
