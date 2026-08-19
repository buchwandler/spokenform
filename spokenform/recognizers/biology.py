"""Conservative biomedical identifier recognition."""

from __future__ import annotations

import re
from collections.abc import Iterable

from num2words import num2words

from ..language import base_language, normalize_language, resolve_num2words_language
from ..mapping import Replacement
from ..sequences import render_letters, render_sequence

_PATHOGEN_RE = re.compile(r"(?<!\w)(?P<value>MERS|COVID(?:-19)?|SARS)(?!\w)")
_VIRUS_RE = re.compile(
    r"(?<!\w)(?P<value>(?:(?:SARS)(?:-[A-Z]{1,4})?|(?:DENV|HIV|HCV|HPV|HBV|EBV|MMR))-\d+)(?!\w)",
    re.IGNORECASE,
)
_REVIEWED_BIO_TOKEN_RE = re.compile(r"(?<!\w)(?P<value>HPV|HBV|HIV|EBV|MMR)(?:-\d+)?(?!\w)")
_GENE_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]{2,8}\d{1,4})(?!\w)")
_MIXED_BIO_RE = re.compile(
    r"(?<!\w)(?P<value>(?:p[A-Z]{2,8}\d+|CRF\d{2}_[A-Z]{2,4}|Col-\d+))(?!\w)"
)
_LINEAGE_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]\.(?:\d+\.)+\d+)(?!\w)")
_BIO_CONTEXT_RE = re.compile(
    r"\b(?:gene|strain|virus|variant|lineage|plasmid|ecotype|chromosome|isolate|serotype)\b",
    re.IGNORECASE,
)


def _cardinal(value: int, language: str) -> str:
    return (
        str(num2words(value, lang=resolve_num2words_language(language)))
        .replace(",", "")
        .replace("-", " ")
        .replace(" and ", " ")
    )


def _alpha(value: str, language: str) -> str:
    lexical = {"MERS": "Mers", "SARS": "Sars", "COVID": "covid", "COV": "Cov"}
    if value.upper() in lexical:
        return lexical[value.upper()]
    return render_letters(value, language=language)


def _render(value: str, language: str, *, digitwise: bool = False) -> str:
    parts: list[str] = []
    for token in re.findall(r"[A-Za-z]+|\d+|[._-]", value):
        if token.isdigit():
            parts.append(
                render_sequence(token, language=language, digit_mode="digitwise")
                if digitwise
                else _cardinal(int(token), language)
            )
        elif token == ".":
            parts.append(
                {"de": "Punkt", "es": "punto", "fr": "point", "it": "punto"}.get(
                    base_language(language), "point"
                )
            )
        elif token in "-_":
            continue
        else:
            parts.append(_alpha(token, language))
    return " ".join(parts)


def _contextual(value: str, text: str, start: int, end: int) -> bool:
    if value.casefold().startswith(("brca", "tp", "puc", "crf", "col-")):
        return True
    context = f"{text[max(0, start - 48) : start]} {text[end : end + 48]}"
    return bool(_BIO_CONTEXT_RE.search(context))


def iter_replacements(
    text: str,
    *,
    language: str = "en",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return reviewed biomedical identifier claims."""
    language = normalize_language(language)
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []

    def add(match: re.Match[str], *, contextual: bool = False) -> None:
        start, end = match.span("value")
        if any(start < right and left < end for left, right in protected):
            return
        if contextual and not _contextual(match["value"], text, start, end):
            return
        candidates.append(
            Replacement(
                start,
                end,
                _render(
                    match["value"],
                    language,
                    digitwise=match.re is _GENE_RE or match.re is _MIXED_BIO_RE,
                ),
                "structured",
                language,
                "sequence.biomedical",
                25,
                "biology",
                "contextual" if contextual else "intrinsic",
            )
        )

    for match in _PATHOGEN_RE.finditer(text):
        add(match)
    for match in _VIRUS_RE.finditer(text):
        add(match)
    for match in _REVIEWED_BIO_TOKEN_RE.finditer(text):
        add(match)
    for match in _MIXED_BIO_RE.finditer(text):
        add(match, contextual=True)
    for match in _GENE_RE.finditer(text):
        add(match, contextual=True)
    for match in _LINEAGE_RE.finditer(text):
        add(match, contextual=True)
    return tuple(candidates)


__all__ = ["iter_replacements"]
