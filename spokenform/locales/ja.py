"""Japanese structured rendering."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..config import NumberPolicy
from ..mapping import Replacement
from ..number_words import cardinal, digits
from ._cjk import iter_quantities, iter_semantic_replacements

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN
_DATE = re.compile(
    r"(?<!\d)(?P<year>\d{4})年(?P<month>0?[1-9]|1[0-2])月(?P<day>0?[1-9]|[12]\d|3[01])日"
)
_ISO_DATE = re.compile(
    r"(?<!\d)(?P<year>\d{4})[-/](?P<month>0?[1-9]|1[0-2])[-/](?P<day>0?[1-9]|[12]\d|3[01])(?!\d)"
)
_TIME = re.compile(r"(?<!\d)(?P<hour>[01]?\d|2[0-3])時(?P<minute>[0-5]\d)分(?:([0-5]\d)秒)?")


def _date_text(year: int, month: int, day: int) -> str:
    year_text = "".join(digits(str(year), "ja"))
    return f"{year_text}年{cardinal(month, 'ja')}月{cardinal(day, 'ja')}日"


def _time_text(hour: int, minute: int, second: str | None) -> str:
    result = f"{cardinal(hour, 'ja')}時{cardinal(minute, 'ja')}分"
    if second is not None:
        result += f"{cardinal(int(second), 'ja')}秒"
    return result


def iter_replacements(
    text: str,
    *,
    language: str = "ja",
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
                "ja.date",
            )
    for match in _TIME.finditer(text):
        add(
            match.start(),
            match.end(),
            _time_text(int(match["hour"]), int(match["minute"]), match.group(3)),
            "ja.time",
        )
    replacements.extend(
        iter_semantic_replacements(
            text, language=language, protected_ranges=protected, rule_prefix="ja"
        )
    )
    replacements.extend(
        iter_quantities(text, language=language, protected_ranges=protected, rule_prefix="ja")
    )
    return tuple(replacements)


__all__ = ["NUMBER_POLICY", "iter_replacements"]
