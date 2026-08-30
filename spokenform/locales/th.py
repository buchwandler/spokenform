"""Thai semantic grammar owned by Spokenform.

The rules are intentionally source-aligned so KokoroG2P can consume prepared
text without running a second whole-string semantic normalizer.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from abbr2words import UnitMatch, iter_unit_matches

from ..config import NumberPolicy
from ..language import resolve_abbr2words_language
from ..mapping import Replacement
from ..number_words import number_words
from ..numeric_lexeme import NumericLexeme, parse_numeric_lexeme

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN
_TIME = re.compile(r"(?<!\w)(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)(?!\w)")
_RANGE = re.compile(r"(?<!\w)(?P<start>\d+)\s*(?:-|–|—|ถึง)\s*(?P<end>\d+)(?!\w)")
_DECIMAL = re.compile(r"(?<![\w,.])(?P<sign>[+-]?)(?P<integer>\d+)\.(?P<fraction>\d+)(?![\w.])")
_BAHT = re.compile(r"(?<!\w)(?P<value>[+\-]?\d+(?:\.\d+)?)\s*บาท(?!\w)")
_IDENTIFIER = re.compile(r"(?P<prefix>เลขที่|รหัส|โทร|เบอร์|บัญชี)\s+(?P<value>[\d\-/]{3,})")
_GENERIC_IDENTIFIER = re.compile(r"(?<!\w)(?P<value>\d[\d\-/]*[/-]\d[\d\-/]*)(?!\w)")
_LAUGHTER = re.compile(r"(?<!\w)555(?!\w)(?!\s*(?:บาท|คน|ครั้ง|กิโลเมตร))")
_REPETITION = re.compile(r"(?P<word>\S+)\s*ๆ")
_OPERATORS = {
    "%": "เปอร์เซ็นต์",
    "+": "บวก",
    "=": "เท่ากับ",
    "<": "น้อยกว่า",
    ">": "มากกว่า",
    "≤": "น้อยกว่าหรือเท่ากับ",
    "≥": "มากกว่าหรือเท่ากับ",
}


def _spell_integer(digits: str, language: str) -> str:
    return str(number_words(int(digits), lang=language))


def _spell_digits(value: str, language: str) -> str:
    return " ".join(_spell_integer(digit, language) for digit in value)


def number_text(lexeme: NumericLexeme, *, language: str) -> str:
    """Render a Thai numeric lexeme without losing source precision."""
    if lexeme.fraction_digits is None:
        result = _spell_integer(lexeme.integer_digits, language)
    else:
        result = (
            _spell_integer(lexeme.integer_digits, language)
            + "จุด"
            + "".join(_spell_integer(digit, language) for digit in lexeme.fraction_digits)
        )
    if lexeme.negative:
        return f"ติดลบ{result}"
    if lexeme.raw.startswith("+"):
        return f"บวก{result}"
    return result


def _sign_prefix(lexeme: NumericLexeme) -> str:
    if lexeme.negative:
        return "ติดลบ"
    if lexeme.raw.startswith("+"):
        return "บวก"
    return ""


def _baht_text(lexeme: NumericLexeme, *, language: str) -> str | None:
    """Render exact Thai baht and satang amounts without float conversion."""
    fraction = lexeme.fraction_digits
    if fraction is not None and len(fraction) > 2:
        return None
    major = _spell_integer(lexeme.integer_digits, language)
    prefix = _sign_prefix(lexeme)
    if fraction is None:
        return f"{prefix}{major} บาท"
    minor_value = int(fraction.ljust(2, "0"))
    if minor_value == 0:
        return f"{prefix}{major} บาท"
    minor = _spell_integer(str(minor_value), language)
    if int(lexeme.integer_digits) == 0:
        return f"{prefix}{minor} สตางค์"
    return f"{prefix}{major} บาท {minor} สตางค์"


def _quantity_text(match: UnitMatch, *, language: str) -> str | None:
    context = "currency" if match.category == "currency" else "quantity"
    lexeme = parse_numeric_lexeme(match.value, language, context=context)
    if lexeme is None:
        return None
    canonical_id = match.canonical_id or ""
    if match.category == "currency":
        if canonical_id != "currency-thai-baht":
            return None
        return _baht_text(lexeme, language=language)
    if not canonical_id or not match.expansion:
        return None
    return f"{number_text(lexeme, language=language)} {match.expansion}"


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def iter_replacements(
    text: str,
    *,
    language: str = "th",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return source-aligned Thai semantic replacements."""
    protected = tuple(protected_ranges)
    dependency_language = resolve_abbr2words_language(language)
    candidates: list[Replacement] = []

    def add(match: re.Match[str], replacement: str, rule: str) -> None:
        if not _overlaps(match.start(), match.end(), protected):
            candidates.append(
                Replacement(match.start(), match.end(), replacement, "structured", "th", rule)
            )

    for match in _TIME.finditer(text):
        add(
            match,
            f"{_spell_integer(match['hour'], language)} นาฬิกา {_spell_digits(match['minute'], language)} นาที",
            "th.time",
        )
    for match in _DECIMAL.finditer(text):
        add(
            match,
            (
                ("ติดลบ" if match["sign"] == "-" else "บวก" if match["sign"] == "+" else "")
                + f"{_spell_integer(match['integer'], language)} จุด "
                + f"{_spell_digits(match['fraction'], language)}"
            ),
            "th.decimal",
        )
    for match in _RANGE.finditer(text):
        add(
            match,
            f"{_spell_integer(match['start'], language)} ถึง {_spell_integer(match['end'], language)}",
            "th.range",
        )
    for match in _IDENTIFIER.finditer(text):
        add(
            match,
            f"{match['prefix']} {_spell_identifier(match['value'], language)}",
            "th.identifier",
        )
    for match in _GENERIC_IDENTIFIER.finditer(text):
        add(match, _spell_identifier(match["value"], language), "th.identifier")
    for match in _LAUGHTER.finditer(text):
        add(match, "ฮ่า ฮ่า ฮ่า", "th.laughter.555")
    for match in _REPETITION.finditer(text):
        add(match, f"{match['word']} {match['word']}", "th.repetition")
    for symbol, spoken in _OPERATORS.items():
        for start in (match.start() for match in re.finditer(re.escape(symbol), text)):
            if not _overlaps(start, start + len(symbol), protected):
                candidates.append(
                    Replacement(
                        start,
                        start + len(symbol),
                        f" {spoken} ",
                        "structured",
                        "th",
                        f"th.operator.{symbol}",
                    )
                )
    for match in _BAHT.finditer(text):
        lexeme = parse_numeric_lexeme(match["value"], language, context="currency")
        if lexeme is not None:
            replacement = _baht_text(lexeme, language=language)
            if replacement is not None:
                add(match, replacement, "th.currency")

    for match in iter_unit_matches(text, dependency_language, protected_spans=protected):
        if _overlaps(match.start, match.end, protected):
            continue
        try:
            replacement = _quantity_text(match, language=language)
        except (TypeError, ValueError):
            replacement = None
        if replacement is None:
            continue
        rule = "th.currency" if match.category == "currency" else "th.quantity"
        candidates.append(
            Replacement(match.start, match.end, replacement, "structured", "th", rule)
        )
    return tuple(candidates)


def _spell_identifier(value: str, language: str) -> str:
    return " ".join(
        _spell_digits(part, language) if part.isdigit() else "ขีด"
        for part in re.split(r"([/-])", value)
        if part
    )


__all__ = ["NUMBER_POLICY", "iter_replacements", "number_text"]
