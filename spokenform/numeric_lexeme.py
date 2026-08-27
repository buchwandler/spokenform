"""Conservative parsing of written numeric lexemes.

The locale grammars all need to answer the same small question: which
separator is decimal punctuation and which separators are grouping marks?  A
numeric lexeme is deliberately provider-neutral; rendering remains owned by
the recognizer and locale grammar that understands the surrounding meaning.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
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


class NumberRenderMode(str, Enum):
    """Semantic rendering mode selected by a recognizer."""

    CARDINAL = "cardinal"
    DIGIT_SEQUENCE = "digit_sequence"
    YEAR = "year"
    DECIMAL = "decimal"
    ORDINAL = "ordinal"


@dataclass(frozen=True, slots=True)
class NumericPunctuationPolicy:
    """Locale punctuation contract used before any ambiguity fallback."""

    decimal_separator: str
    grouping_separators: tuple[str, ...]
    alternate_decimal_separators: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class NumericSpeechPolicy:
    """Locale-selected wording policy for a parsed numeric lexeme."""

    decimal_word: str
    fraction_mode: Literal["digitwise", "two_digit_cardinal", "cardinal"]
    preserve_leading_zero_fraction: bool = True
    omit_cardinal_conjunction: bool = False
    year_mode: Literal["cardinal", "split_hundreds", "short", "locale"] = "cardinal"


_NUMERIC_SPEECH_POLICIES: dict[str, NumericSpeechPolicy] = {
    "en_US": NumericSpeechPolicy(
        "point", "digitwise", omit_cardinal_conjunction=True, year_mode="locale"
    ),
    "de_DE": NumericSpeechPolicy("Komma", "digitwise", year_mode="split_hundreds"),
    "es_MX": NumericSpeechPolicy("punto", "two_digit_cardinal"),
    "fr_FR": NumericSpeechPolicy("virgule", "two_digit_cardinal"),
    "it_IT": NumericSpeechPolicy("virgola", "two_digit_cardinal"),
}


_NUMERIC_PUNCTUATION_POLICIES: dict[str, NumericPunctuationPolicy] = {
    "en_US": NumericPunctuationPolicy(".", (",", " ", "\u00a0", "\u202f")),
    # Mexican Spanish commonly uses comma grouping and dot decimals, while
    # accepting short comma decimals in quantities from mixed corpora.
    "es_MX": NumericPunctuationPolicy(".", (",", " ", "\u00a0", "\u202f"), (",",)),
    "de_DE": NumericPunctuationPolicy(",", (".", " ", "\u00a0", "\u202f"), (".",)),
    "fr_FR": NumericPunctuationPolicy(",", (" ", "\u00a0", "\u202f", "."), (".",)),
    "it_IT": NumericPunctuationPolicy(",", (".", " ", "\u00a0", "\u202f"), (".",)),
}

_BASE_NUMERIC_PUNCTUATION_POLICIES: dict[str, NumericPunctuationPolicy] = {
    "en": NumericPunctuationPolicy(".", (",", " ", "\u00a0", "\u202f")),
    "es": NumericPunctuationPolicy(",", (".", " ", "\u00a0", "\u202f"), (".",)),
    "de": NumericPunctuationPolicy(",", (".", " ", "\u00a0", "\u202f"), (".",)),
    "fr": NumericPunctuationPolicy(",", (" ", "\u00a0", "\u202f", "."), (".",)),
    "it": NumericPunctuationPolicy(",", (".", " ", "\u00a0", "\u202f"), (".",)),
    "pt": NumericPunctuationPolicy(",", (".", " ", "\u00a0", "\u202f"), (".",)),
    "sv": NumericPunctuationPolicy(",", (" ", "\u00a0", "\u202f")),
    "ja": NumericPunctuationPolicy(".", (",", " ", "\u00a0", "\u202f")),
    "ko": NumericPunctuationPolicy(".", (",", " ", "\u00a0", "\u202f")),
    "zh": NumericPunctuationPolicy(".", (",", " ", "\u00a0", "\u202f")),
}

_BASE_NUMERIC_SPEECH_POLICIES: dict[str, NumericSpeechPolicy] = {
    "en": NumericSpeechPolicy("point", "digitwise"),
    "de": NumericSpeechPolicy("Komma", "digitwise", year_mode="split_hundreds"),
    "es": NumericSpeechPolicy("coma", "digitwise"),
    "fr": NumericSpeechPolicy("virgule", "digitwise"),
    "it": NumericSpeechPolicy("virgola", "digitwise"),
    "pt": NumericSpeechPolicy("vírgula", "digitwise"),
    "sv": NumericSpeechPolicy("komma", "digitwise"),
    "ja": NumericSpeechPolicy("点", "digitwise"),
    "ko": NumericSpeechPolicy("점", "digitwise"),
    "zh": NumericSpeechPolicy("点", "digitwise"),
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


def numeric_punctuation_policy(language: str) -> NumericPunctuationPolicy:
    """Return the locale punctuation policy for numeric lexeme parsing."""
    normalized = normalize_language(language)
    return _NUMERIC_PUNCTUATION_POLICIES.get(
        normalized,
        _BASE_NUMERIC_PUNCTUATION_POLICIES.get(
            base_language(normalized), NumericPunctuationPolicy(".", (",", " "))
        ),
    )


def fraction_digit_groups(
    fraction_digits: str,
    language: str,
    *,
    mode: Literal["policy", "digitwise"] = "policy",
) -> tuple[str, ...]:
    """Group fractional digits according to the locale or render mode."""
    if mode == "digitwise":
        return tuple(fraction_digits)
    policy = numeric_speech_policy(language)
    if (
        policy.fraction_mode in {"two_digit_cardinal", "cardinal"}
        and len(fraction_digits) == 2
        and not (policy.preserve_leading_zero_fraction and fraction_digits.startswith("0"))
    ):
        return (fraction_digits,)
    return tuple(fraction_digits)


_NUMERIC_RE = re.compile(
    r"^[+\-−]?(?:\d(?:[\d\s\u00a0\u202f.,'’]*\d)?|[.,]\d[\d\s\u00a0\u202f.,'’]*)$"
)
_STRONG_DECIMAL_CONTEXTS = frozenset({"quantity", "currency", "percent", "coordinate"})
_NON_NUMERIC_CONTEXTS = frozenset({"date", "date_candidate", "time", "version"})


def _separator_positions(value: str, separator: str) -> list[int]:
    return [index for index, character in enumerate(value) if character == separator]


def _grouping_is_valid(value: str, separator: str) -> bool:
    groups = value.split(separator)
    return len(groups) > 1 and bool(groups[0]) and all(len(group) == 3 for group in groups[1:])


def _clean_grouping(value: str) -> str:
    return re.sub(r"[\s\u00a0\u202f'’]", "", value)


@dataclass(frozen=True, slots=True)
class _SeparatorResolution:
    decimal_separator: str | None
    grouping_separators: tuple[str, ...] = ()


def _validated_numeric_token(raw: str, context: str) -> tuple[bool, str] | None:
    if not isinstance(raw, str) or not raw.strip() or context in _NON_NUMERIC_CONTEXTS:
        return None
    value = raw.strip()
    if not _NUMERIC_RE.fullmatch(value):
        return None
    negative = value.startswith(("-", "−"))
    unsigned = value.lstrip("+−-")
    if not unsigned or not any(character.isdigit() for character in unsigned):
        return None
    return negative, unsigned


def _resolve_mixed_separators(
    unsigned: str,
    policy: NumericPunctuationPolicy,
) -> _SeparatorResolution | None:
    rightmost_index = max(unsigned.rfind("."), unsigned.rfind(","))
    candidate = unsigned[rightmost_index]
    tail = unsigned[rightmost_index + 1 :]
    # The locale's declared decimal separator wins even for a three-digit
    # fractional tail (for example de-DE ``42,195``).
    if candidate == policy.decimal_separator or (
        candidate in policy.alternate_decimal_separators and len(tail) != 3
    ):
        return _SeparatorResolution(candidate)
    return None


def _resolve_repeated_separator(
    unsigned: str,
    separator: str,
    *,
    context: str,
    policy: NumericPunctuationPolicy,
) -> _SeparatorResolution | None:
    valid_grouping = _grouping_is_valid(unsigned, separator)
    currency_grouping = (
        context == "currency" and separator == policy.decimal_separator and valid_grouping
    )
    if (separator in policy.grouping_separators or currency_grouping) and valid_grouping:
        return _SeparatorResolution(None, (separator,))
    return None


def _resolve_single_separator(
    unsigned: str,
    separator: str,
    *,
    language: str,
    context: str,
    policy: NumericPunctuationPolicy,
) -> _SeparatorResolution | None:
    head, tail = unsigned.split(separator, 1)
    if not tail:
        return None
    if not head:
        if separator not in (policy.decimal_separator, *policy.alternate_decimal_separators):
            return None
        head = "0"
    if separator == policy.decimal_separator:
        if context == "currency" and len(tail) > 2:
            if separator not in policy.grouping_separators and base_language(language) != "es":
                return None
            if len(tail) != 3 or not _grouping_is_valid(unsigned, separator):
                return None
            return _SeparatorResolution(None, (separator,))
        return _SeparatorResolution(separator)
    if separator in policy.alternate_decimal_separators and (
        len(tail) in {1, 2} or context in {"coordinate", "math"}
    ):
        return _SeparatorResolution(separator)
    if len(tail) == 3 and separator in policy.grouping_separators:
        return _SeparatorResolution(None, (separator,))
    if context in _STRONG_DECIMAL_CONTEXTS and len(tail) in {1, 2}:
        return _SeparatorResolution(separator)
    return None


def _resolve_separator_shape(
    unsigned: str,
    *,
    language: str,
    context: str,
    policy: NumericPunctuationPolicy,
) -> _SeparatorResolution | None:
    separators = tuple(character for character in unsigned if character in ".,")
    distinct = set(separators)
    if len(distinct) == 2:
        return _resolve_mixed_separators(unsigned, policy)
    separator = separators[0]
    positions = _separator_positions(unsigned, separator)
    if len(positions) > 1:
        return _resolve_repeated_separator(unsigned, separator, context=context, policy=policy)
    return _resolve_single_separator(
        unsigned,
        separator,
        language=language,
        context=context,
        policy=policy,
    )


def _build_numeric_lexeme(
    raw: str,
    *,
    negative: bool,
    unsigned: str,
    resolution: _SeparatorResolution,
) -> NumericLexeme | None:
    decimal_separator = resolution.decimal_separator
    grouping_separators = list(resolution.grouping_separators)
    distinct = {character for character in unsigned if character in ".,"}
    if decimal_separator is not None:
        integer, fraction = unsigned.rsplit(decimal_separator, 1)
        integer = integer or "0"
        if not fraction or not fraction.isdigit():
            return None
        remaining = _clean_grouping(integer.replace(",", "").replace(".", ""))
        if not remaining.isdigit():
            return None
        for separator in distinct:
            if separator != decimal_separator:
                grouping_separators.append(separator)
        integer = _clean_grouping(remaining)
        if any(character not in "0123456789" for character in integer):
            return None
        return NumericLexeme(
            raw,
            negative,
            integer,
            fraction,
            decimal_separator,
            tuple(dict.fromkeys(grouping_separators)),
        )
    integer = _clean_grouping(unsigned.replace(",", "").replace(".", ""))
    if not integer.isdigit():
        return None
    return NumericLexeme(
        raw,
        negative,
        integer,
        None,
        None,
        tuple(dict.fromkeys(grouping_separators)),
    )


_NUMERIC_COMPATIBILITY_RE = re.compile(
    r"(?<![0-9０-９A-Za-zＡ-Ｚａ-ｚ_])[＋－]?[０-９]+(?:[．，][０-９]+)?(?![0-9０-９A-Za-zＡ-Ｚａ-ｚ_])"
)
_NUMERIC_COMPATIBILITY_TABLE = str.maketrans(
    "０１２３４５６７８９．，＋－",
    "0123456789.,+-",
)


def normalize_numeric_compatibility(text: str) -> str:
    """Fold full-width punctuation only inside numeric-looking spans."""
    return _NUMERIC_COMPATIBILITY_RE.sub(
        lambda match: match.group(0).translate(_NUMERIC_COMPATIBILITY_TABLE),
        text,
    )


def parse_numeric_lexeme(
    raw: str,
    language: str = "en",
    *,
    context: str = "plain",
) -> NumericLexeme | None:
    """Parse one numeric token, failing closed when separators are ambiguous."""
    validated = _validated_numeric_token(raw, context)
    if validated is None:
        return None
    negative, unsigned = validated
    language = normalize_language(language)
    policy = numeric_punctuation_policy(language)
    if base_language(language) == "sv" and "." in unsigned:
        return None
    if not any(character in unsigned for character in ".,"):
        return NumericLexeme(raw, negative, _clean_grouping(unsigned), None, None, ())
    resolution = _resolve_separator_shape(
        unsigned,
        language=language,
        context=context,
        policy=policy,
    )
    if resolution is None:
        return None
    return _build_numeric_lexeme(
        raw,
        negative=negative,
        unsigned=unsigned,
        resolution=resolution,
    )


__all__ = [
    "NumericLexeme",
    "NumberRenderMode",
    "NumericPunctuationPolicy",
    "NumericSpeechPolicy",
    "fraction_digit_groups",
    "normalize_numeric_compatibility",
    "numeric_punctuation_policy",
    "numeric_speech_policy",
    "parse_numeric_lexeme",
]
