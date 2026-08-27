"""Thai semantic grammar owned by spokenform.

``abbr2words`` recognizes reviewed Thai abbreviations, units, and currency
identities. This module owns numeric realization and source-aligned structured
replacements.
"""

from __future__ import annotations

from collections.abc import Iterable

from abbr2words import UnitMatch, iter_unit_matches

from ..config import NumberPolicy
from ..language import resolve_abbr2words_language
from ..mapping import Replacement
from ..number_words import number_words
from ..numeric_lexeme import NumericLexeme, parse_numeric_lexeme

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN


def _spell_integer(digits: str, language: str) -> str:
    return str(number_words(int(digits), lang=language))


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
    """Return Thai structured quantity and currency replacements."""
    protected = tuple(protected_ranges)
    dependency_language = resolve_abbr2words_language(language)
    candidates: list[Replacement] = []
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


__all__ = ["NUMBER_POLICY", "iter_replacements", "number_text"]
