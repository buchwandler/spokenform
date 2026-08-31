"""Korean structured rendering, including native counter morphology."""

from __future__ import annotations

import re
from collections.abc import Iterable

from ..config import NumberPolicy
from ..mapping import Replacement
from ..number_words import cardinal
from ._cjk import iter_quantities, iter_semantic_replacements

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN
BOUND_NOUNS = frozenset(
    "군데 권 개 그루 닢 두 마리 모 모금 뭇 발 발짝 방 번 벌 보루 살 수 술 시 쌈 움큼 정 "
    "짝 채 척 첩 축 켤레 톨 통 가지 배 시간 명 줄 곳".split()
)
_COUNTER_PATTERN = re.compile(
    r"(?<!\d)(?P<number>\d[\d,]*)(?P<space> ?)(?P<noun>"
    + "|".join(sorted((re.escape(noun) for noun in BOUND_NOUNS), key=len, reverse=True))
    + r")"
)
_SINO_COUNTER_PATTERN = re.compile(r"(?<!\d)(?P<number>\d[\d,]*)(?P<space> ?)(?P<noun>분)")
_DATE = re.compile(
    r"(?<!\d)(?P<year>\d{4})년\s*(?P<month>0?[1-9]|1[0-2])월\s*(?P<day>0?[1-9]|[12]\d|3[01])일"
)
_ISO_DATE = re.compile(
    r"(?<!\d)(?P<year>\d{4})[-/](?P<month>0?[1-9]|1[0-2])[-/](?P<day>0?[1-9]|[12]\d|3[01])(?!\d)"
)
_TIME = re.compile(r"(?<!\d)(?P<hour>[01]?\d|2[0-3])시\s*(?P<minute>[0-5]\d)분")


def process_num(num: str, *, sino: bool = True) -> str:
    """Render the g2pk-compatible Korean cardinal or native modifier form."""
    num = num.replace(",", "")
    if num == "0":
        return "영"
    if not sino and num == "20":
        return "스무"

    digit_names = dict(zip("123456789", "일이삼사오육칠팔구", strict=True))
    modifiers = dict(
        zip("123456789", "한 두 세 네 다섯 ^여섯 일곱 ^여덟 아홉".split(), strict=True)
    )
    tens = dict(zip("123456789", "열 스물 서른 마흔 쉰 예순 일흔 여든 아흔".split(), strict=True))
    spelled: list[str] = []
    for offset, digit in enumerate(num):
        position = len(num) - offset - 1
        if sino or len(num) >= 3:
            name = digit_names.get(digit, "") if position == 0 else ""
            if position == 1:
                name = digit_names.get(digit, "") + "십"
                name = name.replace("일십", "십")
        else:
            name = modifiers.get(digit, "") if position == 0 else ""
            if position == 1:
                name = tens.get(digit, "")
        if digit == "0":
            if position % 4 == 0 and "".join(spelled[-min(3, len(spelled)) :]) == "":
                spelled.append("")
                continue
            if position % 4 != 0:
                spelled.append("")
                continue
        if position in {2, 6, 10, 14}:
            name = digit_names.get(digit, "") + "백"
            name = name.replace("일백", "백")
        elif position in {3, 7, 11, 15}:
            name = digit_names.get(digit, "") + "천"
            name = name.replace("일천", "천")
        elif position == 4:
            name = digit_names.get(digit, "") + "만"
            name = name.replace("일만", "만")
        elif position == 5:
            name = digit_names.get(digit, "") + "십"
            name = name.replace("일십", "십")
        elif position == 8:
            name = digit_names.get(digit, "") + "억"
        elif position == 9:
            name = digit_names.get(digit, "") + "십"
        elif position == 12:
            name = digit_names.get(digit, "") + "조"
        elif position == 13:
            name = digit_names.get(digit, "") + "십"
        spelled.append(name)
    return "".join(spelled).replace("^", "")


def _date_text(year: int, month: int, day: int) -> str:
    return f"{cardinal(year, 'ko')}년 {cardinal(month, 'ko')}월 {cardinal(day, 'ko')}일"


def _time_text(hour: int, minute: int) -> str:
    return f"{process_num(str(hour), sino=False)}시 {cardinal(minute, 'ko')}분"


def _iter_counter_replacements(
    text: str,
    *,
    language: str,
    protected: tuple[tuple[int, int], ...],
) -> tuple[Replacement, ...]:
    replacements: list[Replacement] = []
    for pattern, sino in ((_COUNTER_PATTERN, False), (_SINO_COUNTER_PATTERN, True)):
        for match in pattern.finditer(text):
            if any(match.start() < end and start < match.end() for start, end in protected):
                continue
            replacements.append(
                Replacement(
                    match.start(),
                    match.end(),
                    process_num(match["number"], sino=sino) + match["noun"],
                    "structured",
                    language,
                    "ko.counter",
                )
            )
    return tuple(replacements)


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
    replacements.extend(_iter_counter_replacements(text, language=language, protected=protected))
    replacements.extend(
        iter_semantic_replacements(
            text, language=language, protected_ranges=protected, rule_prefix="ko"
        )
    )
    replacements.extend(
        iter_quantities(text, language=language, protected_ranges=protected, rule_prefix="ko")
    )
    return tuple(replacements)


__all__ = ["BOUND_NOUNS", "NUMBER_POLICY", "iter_replacements", "process_num"]
