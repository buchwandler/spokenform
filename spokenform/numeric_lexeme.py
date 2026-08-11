"""Conservative parsing of written numeric lexemes.

The locale grammars all need to answer the same small question: which
separator is decimal punctuation and which separators are grouping marks?  A
numeric lexeme is deliberately provider-neutral; rendering remains owned by
the recognizer and locale grammar that understands the surrounding meaning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .language import base_language, normalize_language


@dataclass(frozen=True, slots=True)
class NumericLexeme:
    """A validated numeric token without committing to spoken wording."""

    raw: str
    negative: bool
    integer_digits: str
    fraction_digits: str | None
    decimal_separator: str | None
    grouping_separators: tuple[str, ...]

    @property
    def signed_integer(self) -> str:
        """Return the integer digits with the source sign."""
        return f"{'-' if self.negative else ''}{self.integer_digits}"


@dataclass(frozen=True, slots=True)
class NumericSpeechPolicy:
    """Locale-selected wording policy for a parsed numeric lexeme."""

    decimal_word: str
    fraction_mode: Literal["digitwise", "two_digit_cardinal", "cardinal"]
    preserve_leading_zero_fraction: bool = True
    omit_cardinal_conjunction: bool = False
    year_mode: Literal["cardinal", "split_hundreds", "short", "locale"] = "cardinal"


_NUMERIC_SPEECH_POLICIES: dict[str, NumericSpeechPolicy] = {
    "en_US": NumericSpeechPolicy("point", "digitwise", omit_cardinal_conjunction=True, year_mode="locale"),
    "de_DE": NumericSpeechPolicy("Komma", "digitwise", year_mode="split_hundreds"),
    "es_MX": NumericSpeechPolicy("punto", "two_digit_cardinal"),
    "fr_FR": NumericSpeechPolicy("virgule", "two_digit_cardinal"),
    "it_IT": NumericSpeechPolicy("virgola", "two_digit_cardinal"),
}

_BASE_NUMERIC_SPEECH_POLICIES: dict[str, NumericSpeechPolicy] = {
    "en": NumericSpeechPolicy("point", "digitwise"),
    "de": NumericSpeechPolicy("Komma", "digitwise", year_mode="split_hundreds"),
    "es": NumericSpeechPolicy("coma", "digitwise"),
    "fr": NumericSpeechPolicy("virgule", "digitwise"),
    "it": NumericSpeechPolicy("virgola", "digitwise"),
    "pt": NumericSpeechPolicy("vírgula", "digitwise"),
}


def numeric_speech_policy(language: str) -> NumericSpeechPolicy:
    """Return the immutable numeric speech policy for a normalized locale."""
    normalized = normalize_language(language)
    return _NUMERIC_SPEECH_POLICIES.get(
        normalized,
        _BASE_NUMERIC_SPEECH_POLICIES.get(
            base_language(normalized), NumericSpeechPolicy("point", "digitwise")
        ),
    )


def fraction_digit_groups(fraction_digits: str, language: str) -> tuple[str, ...]:
    """Group fractional digits according to the locale speech policy."""
    policy = numeric_speech_policy(language)
    if (
        policy.fraction_mode in {"two_digit_cardinal", "cardinal"}
        and len(fraction_digits) == 2
        and not (policy.preserve_leading_zero_fraction and fraction_digits.startswith("0"))
    ):
        return (fraction_digits,)
    return tuple(fraction_digits)


_NUMERIC_RE = re.compile(
    r"^[+\-−]?(?:\d(?:[\d\s\u00a0\u202f.,'’]*\d)?|\.\d[\d\s\u00a0\u202f.,'’]*)$"
)
_STRONG_DECIMAL_CONTEXTS = frozenset({"quantity", "currency", "percent", "coordinate"})
_NON_NUMERIC_CONTEXTS = frozenset({"date", "date_candidate", "time", "version"})


def _separator_positions(value: str, separator: str) -> list[int]:
    return [index for index, character in enumerate(value) if character == separator]


def _grouping_is_valid(value: str, separator: str) -> bool:
    groups = value.split(separator)
    return len(groups) > 1 and bool(groups[0]) and all(
        len(group) == 3 for group in groups[1:]
    )


def _clean_grouping(value: str) -> str:
    return re.sub(r"[\s\u00a0\u202f'’]", "", value)


def parse_numeric_lexeme(
    raw: str,
    language: str = "en",
    *,
    context: str = "plain",
) -> NumericLexeme | None:
    """Parse one numeric token, failing closed when separators are ambiguous.

    A one- or two-digit terminal group is treated as a decimal in a strong
    semantic context, even when it is not the default separator for the
    selected locale.  Three-digit groups remain grouping marks by default,
    which protects values such as Spanish ``3,000``.  Multiple separators are
    resolved by the rightmost separator only when the remaining grouping
    shape is coherent.
    """
    if not isinstance(raw, str) or not raw.strip() or context in _NON_NUMERIC_CONTEXTS:
        return None
    value = raw.strip()
    if not _NUMERIC_RE.fullmatch(value):
        return None
    negative = value.startswith(("-", "−"))
    unsigned = value.lstrip("+−-")
    if not unsigned or not any(character.isdigit() for character in unsigned):
        return None

    language = normalize_language(language)
    base = base_language(language)
    default_decimal = "," if base in {"cs", "de", "es", "fr", "it", "pt"} else "."
    separators = tuple(character for character in unsigned if character in ".,")
    if not separators:
        return NumericLexeme(raw, negative, _clean_grouping(unsigned), None, None, ())

    distinct = set(separators)
    decimal_separator: str | None = None
    fraction_digits: str | None = None
    grouping_separators: list[str] = []

    if len(distinct) == 2:
        rightmost_index = max(unsigned.rfind("."), unsigned.rfind(","))
        candidate = unsigned[rightmost_index]
        tail = unsigned[rightmost_index + 1 :]
        if tail and len(tail) != 3:
            decimal_separator = candidate
        else:
            # A mixed pair with a three-digit terminal group is ambiguous
            # (for example ``1,234.567``); do not guess.
            return None
    else:
        separator = separators[0]
        positions = _separator_positions(unsigned, separator)
        if len(positions) > 1:
            if _grouping_is_valid(unsigned, separator):
                grouping_separators.append(separator)
            else:
                return None
        else:
            head, tail = unsigned.split(separator, 1)
            if not head or not tail:
                return None
            if len(tail) in {1, 2}:
                # A short terminal group is strong decimal evidence even
                # when the source uses the non-preferred locale separator
                # (for example ``1.5`` in Spanish or Italian).
                decimal_separator = separator
            elif len(tail) == 3:
                if context == "currency" and separator == default_decimal and base == "en":
                    # English currency grammar accepts comma grouping and at
                    # most two dot-decimal minor digits; ``1.005`` is not a
                    # valid amount and must remain untouched.
                    return None
                grouping_separators.append(separator)
            elif separator == default_decimal or context in _STRONG_DECIMAL_CONTEXTS:
                decimal_separator = separator
            else:
                return None

    if decimal_separator is not None:
        integer, fraction = unsigned.rsplit(decimal_separator, 1)
        if not integer or not fraction or not fraction.isdigit():
            return None
        remaining = integer.replace(",", "").replace(".", "")
        if not remaining.isdigit():
            return None
        for separator in distinct:
            if separator != decimal_separator:
                grouping_separators.append(separator)
        return NumericLexeme(
            raw,
            negative,
            remaining,
            fraction,
            decimal_separator,
            tuple(dict.fromkeys(grouping_separators)),
        )

    integer = unsigned.replace(",", "").replace(".", "")
    if not integer.isdigit():
        return None
    return NumericLexeme(
        raw,
        negative,
        integer,
        fraction_digits,
        None,
        tuple(dict.fromkeys(grouping_separators)),
    )


__all__ = [
    "NumericLexeme",
    "NumericSpeechPolicy",
    "fraction_digit_groups",
    "numeric_speech_policy",
    "parse_numeric_lexeme",
]
