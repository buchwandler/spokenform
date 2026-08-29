"""Shared mechanics for the reviewed CJK locale renderers."""

from __future__ import annotations

import re
from collections.abc import Iterable

from abbr2words import UnitMatch, iter_unit_matches

from ..language import base_language, resolve_abbr2words_language
from ..mapping import Replacement
from ..numbers import _render_numeric_lexeme
from ..numeric_lexeme import (
    NumberRenderMode,
    has_excess_fractional_precision,
    parse_numeric_lexeme,
)

_PERCENT = re.compile(r"(?<!\w)(?P<value>[+\-−]?(?:\d+(?:[.,]\d+)?|[.,]\d+))\s*%")
_FRACTION = re.compile(r"(?<!\w)(?P<numerator>\d+)\s*/\s*(?P<denominator>\d+)(?!\w)")
_RANGE = re.compile(r"(?<!\w)(?P<start>\d+)\s*[–—-]\s*(?P<end>\d+)(?!\w)")


def render_numeric(value: str, language: str) -> str | None:
    """Render one already-recognized numeric value."""
    lexeme = parse_numeric_lexeme(value, language, context="quantity")
    if lexeme is None:
        return None
    mode = (
        NumberRenderMode.DECIMAL
        if lexeme.fraction_digits is not None
        else NumberRenderMode.CARDINAL
    )
    return _render_numeric_lexeme(lexeme, language, mode=mode)


def render_currency(match: UnitMatch, language: str) -> str | None:
    """Render the CJK currencies exposed by the dependency inventory."""
    numeric = render_numeric(match.value, language)
    if numeric is None:
        return None
    lexeme = parse_numeric_lexeme(match.value, language, context="quantity")
    if lexeme is None:
        return None
    integer = render_numeric(lexeme.integer_digits, language)
    if integer is None:
        return None
    if has_excess_fractional_precision(lexeme.fraction_digits):
        if match.canonical_id == "currency-japanese-yen":
            return f"{numeric}円"
        if match.canonical_id == "currency-south-korean-won":
            return f"{numeric} 원"
        if match.canonical_id == "currency-chinese-yuan":
            return f"{integer}元"
        return None
    if match.canonical_id == "currency-japanese-yen":
        return f"{numeric}円"
    if match.canonical_id == "currency-south-korean-won":
        return f"{numeric} 원"
    if match.canonical_id == "currency-chinese-yuan":
        result = f"{integer}元"
        if lexeme.fraction_digits:
            minor = int(lexeme.fraction_digits[:2].ljust(2, "0"))
            if minor:
                if minor % 10 == 0:
                    minor_text = render_numeric(str(minor // 10), language)
                    if minor_text is None:
                        return None
                    result += f"{minor_text}角"
                else:
                    minor_text = render_numeric(str(minor), language)
                    if minor_text is None:
                        return None
                    result += f"{minor_text}分"
        return result
    return None


def render_quantity(match: UnitMatch, language: str) -> str | None:
    """Apply dependency-owned quantity templates and expansions."""
    if match.category == "currency":
        return render_currency(match, language)
    numeric = render_numeric(match.value, language)
    if numeric is None:
        return None
    if match.quantity_template is not None:
        return match.quantity_template.format(value=numeric)
    return f"{numeric} {match.expansion}"


def iter_semantic_replacements(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
    rule_prefix: str,
) -> tuple[Replacement, ...]:
    """Render CJK percentage, fraction, and numeric-range constructions."""
    protected = tuple(protected_ranges)
    replacements: list[Replacement] = []

    def add(match: re.Match[str], replacement: str, rule: str) -> None:
        if not any(match.start() < end and start < match.end() for start, end in protected):
            replacements.append(
                Replacement(match.start(), match.end(), replacement, "structured", language, rule)
            )

    base = base_language(language)
    for match in _PERCENT.finditer(text):
        value = render_numeric(match["value"], language)
        if value is not None:
            replacement = (
                f"百分之{value}"
                if base == "zh"
                else f"{value}{'パーセント' if base == 'ja' else ' 퍼센트'}"
            )
            add(match, replacement, f"{rule_prefix}.percent")
    for match in _FRACTION.finditer(text):
        numerator = render_numeric(match["numerator"], language)
        denominator = render_numeric(match["denominator"], language)
        if numerator is not None and denominator is not None:
            if base == "ja":
                replacement = f"{denominator}分の{numerator}"
            elif base == "ko":
                replacement = f"{denominator}분의 {numerator}"
            else:
                replacement = f"{denominator}分之{numerator}"
            add(match, replacement, f"{rule_prefix}.fraction")
    for match in _RANGE.finditer(text):
        if re.search(r"\s-\d", match.group(0)):
            continue
        start = render_numeric(match["start"], language)
        end = render_numeric(match["end"], language)
        if start is not None and end is not None:
            connector = {"ja": "から", "ko": "에서", "zh": "到"}[base]
            replacement = (
                f"{start}{connector}{end}" if base != "ko" else f"{start}{connector} {end}"
            )
            add(match, replacement, f"{rule_prefix}.range")
    return tuple(replacements)


def iter_quantities(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
    rule_prefix: str,
) -> tuple[Replacement, ...]:
    """Collect source-aligned quantity replacements from abbr2words."""
    protected = tuple(protected_ranges)
    replacements: list[Replacement] = []
    for match in iter_unit_matches(text, resolve_abbr2words_language(language)):
        if any(match.start < end and start < match.end for start, end in protected):
            continue
        replacement = render_quantity(match, language)
        if replacement is not None:
            replacements.append(
                Replacement(
                    match.start,
                    match.end,
                    replacement,
                    "structured",
                    language,
                    f"{rule_prefix}.currency"
                    if match.category == "currency"
                    else f"{rule_prefix}.quantity",
                )
            )
    return tuple(replacements)
