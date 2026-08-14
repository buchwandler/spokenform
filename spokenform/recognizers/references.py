"""High-confidence bibliographic and citation-shaped sequence recognizers."""

from __future__ import annotations

import re
from collections.abc import Iterable

from num2words import num2words

from ..dates import render_english_year
from ..language import base_language, normalize_language, resolve_num2words_language
from ..mapping import Replacement

_LABELED = re.compile(
    r"(?<!\w)(?P<volume_label>vol(?:ume)?\.?)[ ]*(?P<volume>\d{1,4})\s*,?\s*"
    r"(?P<page_label>pp?\.?|pages?)\s*(?P<page>\d{1,6}(?:\s*[-–]\s*\d{1,6})?)"
    r"(?:\s*\(\s*(?P<year>1[0-9]{3}|20[0-9]{2})\s*\))?",
    re.IGNORECASE,
)
_COLON_CITATION = re.compile(
    r"(?<![\w.])(?P<volume>\d{1,3})\s*:\s*(?P<page>\d{1,4})\s*"
    r"\(\s*(?P<year>1[0-9]{3}|20[0-9]{2})\s*\)(?!\w)"
)


def _cardinal(value: int, language: str) -> str:
    return str(num2words(value, lang=resolve_num2words_language(language))).replace(" and ", " ")


def _year(value: int, language: str) -> str:
    if base_language(language) == "en":
        return render_english_year(value, language=language, source_digits=4)
    return _cardinal(value, language)


def _page(value: str, language: str) -> str:
    parts = [part for part in re.split(r"\s*[-–]\s*", value) if part]
    rendered = [_cardinal(int(part), language) for part in parts]
    return (" to " if base_language(language) == "en" else " a ").join(rendered)


def _render(volume: str, page: str, year: str | None, language: str) -> str:
    base = base_language(language)
    volume_label = {"es": "volumen", "de": "Band", "fr": "volume", "it": "volume"}.get(
        base, "volume"
    )
    page_label = {"es": "página", "de": "Seite", "fr": "page", "it": "pagina"}.get(base, "page")
    result = (
        f"{volume_label} {_cardinal(int(volume), language)} {page_label} {_page(page, language)}"
    )
    if year is not None:
        result += f" ({_year(int(year), language)})"
    return result


def iter_replacements(
    text: str,
    *,
    language: str = "en",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return only strongly labeled or parenthesized citation candidates."""
    language = normalize_language(language)
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []
    for pattern in (_LABELED, _COLON_CITATION):
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(start < right and left < end for left, right in protected):
                continue
            candidates.append(
                Replacement(
                    start,
                    end,
                    _render(match["volume"], match["page"], match["year"], language),
                    "structured",
                    language,
                    "sequence.reference",
                    95,
                )
            )
    return tuple(candidates)


__all__ = ["iter_replacements"]
