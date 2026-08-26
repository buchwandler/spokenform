"""Korean structured rendering."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..config import NumberPolicy
from ..mapping import Replacement
from ..number_words import cardinal
from ._cjk import iter_quantities, iter_semantic_replacements

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN
_DATE = re.compile(
    r"(?<!\d)(?P<year>\d{4})년\s*(?P<month>0?[1-9]|1[0-2])월\s*(?P<day>0?[1-9]|[12]\d|3[01])일"
)
_ISO_DATE = re.compile(
    r"(?<!\d)(?P<year>\d{4})[-/](?P<month>0?[1-9]|1[0-2])[-/](?P<day>0?[1-9]|[12]\d|3[01])(?!\d)"
)
_TIME = re.compile(r"(?<!\d)(?P<hour>[01]?\d|2[0-3])시\s*(?P<minute>[0-5]\d)분")


def _date_text(year: int, month: int, day: int) -> str:
    return f"{cardinal(year, 'ko')}년 {cardinal(month, 'ko')}월 {cardinal(day, 'ko')}일"


def _time_text(hour: int, minute: int) -> str:
    return f"{cardinal(hour, 'ko')}시 {cardinal(minute, 'ko')}분"


def iter_replacements(
    text: str,
    *,
    language: str = "ko",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    protected = tuple(protected_ranges)
    replacements: list[Replacement] = []

    def add(start: int, end: int, replacement: str, rule: str) -> None:
        if not any(start < right and left < end for left, right in protected):
            replacements.append(Replacement(start, end, replacement, "structured", language, rule))

    for pattern in (_DATE, _ISO_DATE):
        for match in pattern.finditer(text):
            add(
                match.start(),
                match.end(),
                _date_text(int(match["year"]), int(match["month"]), int(match["day"])),
                "ko.date",
            )
    for match in _TIME.finditer(text):
        add(
            match.start(),
            match.end(),
            _time_text(int(match["hour"]), int(match["minute"])),
            "ko.time",
        )
    replacements.extend(
        iter_semantic_replacements(
            text, language=language, protected_ranges=protected, rule_prefix="ko"
        )
    )
    replacements.extend(
        iter_quantities(text, language=language, protected_ranges=protected, rule_prefix="ko")
    )
    return tuple(replacements)


__all__ = ["NUMBER_POLICY", "iter_replacements"]
