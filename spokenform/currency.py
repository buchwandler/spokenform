"""Shared currency adaptation between abbr2words and Numeralform."""

from __future__ import annotations

import re
from decimal import Decimal

from .language import base_language
from .number_words import currency as render_currency
from .number_words import number_words
from .numeric_lexeme import NumericLexeme, parse_numeric_lexeme

CANONICAL_TO_ISO: dict[str, str] = {
    "currency-euro": "EUR",
    "currency-us-dollar": "USD",
    "currency-pound-sterling": "GBP",
    "currency-swiss-franc": "CHF",
    "currency-japanese-yen": "JPY",
    "currency-indian-rupee": "INR",
    "currency-south-korean-won": "KRW",
    "currency-mexican-peso": "MXN",
    "currency-vietnamese-dong": "VND",
    "currency-mongolian-tugrik": "MNT",
}

ISO_TO_CANONICAL = {code: canonical for canonical, code in CANONICAL_TO_ISO.items()}


def canonical_currency_id(code: str) -> str | None:
    """Return the abbr2words canonical ID for an ISO code."""
    return ISO_TO_CANONICAL.get(code.upper())


def currency_code(canonical_id: str) -> str | None:
    """Return the ISO code owned by abbr2words for a canonical currency ID."""
    return CANONICAL_TO_ISO.get(canonical_id)


def currency_decimal(lexeme: NumericLexeme) -> Decimal:
    """Build an exact Decimal from normalized lexeme digits."""
    sign = "-" if lexeme.negative else ""
    if lexeme.fraction_digits is None:
        normalized = f"{sign}{lexeme.integer_digits}"
    else:
        normalized = f"{sign}{lexeme.integer_digits}.{lexeme.fraction_digits}"
    return Decimal(normalized)


def parse_currency_decimal(raw: str, language: str) -> tuple[NumericLexeme, Decimal] | None:
    """Parse one currency value without a binary-float round trip."""
    lexeme = parse_numeric_lexeme(raw, language, context="currency")
    if lexeme is None:
        return None
    return lexeme, currency_decimal(lexeme)


def render_currency_text(
    raw: str,
    canonical_id: str,
    language: str,
    *,
    separator: str | None = None,
    omit_zero_minor: bool = True,
) -> str | None:
    if (
        base_language(language) == "en"
        and "," in raw
        and not re.fullmatch(r"[+\-−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", raw.strip())
    ):
        return None
    """Render an abbr2words currency match through Numeralform."""
    code = currency_code(canonical_id)
    if code is None:
        return None
    parsed = parse_currency_decimal(raw, language)
    if parsed is None:
        return None
    _, value = parsed
    try:
        rendered = render_currency(
            value,
            language,
            code,
            separator=separator,
            omit_zero_minor=omit_zero_minor,
        )
    except (TypeError, ValueError):
        return None
    if base_language(language) == "en":
        rendered = rendered.replace("-", " ")
    if base_language(language) == "es" and code == "GBP":
        rendered = re.sub(r"\blibras\b", "libras esterlinas", rendered)
        rendered = re.sub(r"\blibra\b", "libra esterlina", rendered)
    return " ".join(rendered.split())


def currency_major_name(canonical_id: str, language: str, *, singular: bool = False) -> str:
    """Return a locale-owned major-unit name for finance-rate speech."""
    code = currency_code(canonical_id) or canonical_id
    names = {
        "en": {
            "EUR": ("euro", "euros"),
            "USD": ("U S dollar", "U S dollars"),
            "GBP": ("pound", "pounds"),
            "CHF": ("Swiss franc", "Swiss francs"),
            "JPY": ("yen", "yen"),
            "MXN": ("peso", "pesos"),
            "KRW": ("won", "won"),
            "VND": ("dong", "dongs"),
            "MNT": ("tugrik", "tugriks"),
        },
        "de": {
            "EUR": ("Euro", "Euro"),
            "USD": ("Dollar", "Dollar"),
            "GBP": ("Pfund", "Pfund"),
            "CHF": ("Schweizer Franken", "Schweizer Franken"),
        },
        "es": {
            "EUR": ("euro", "euros"),
            "USD": ("dólar", "dólares"),
            "GBP": ("libra", "libras"),
            "CHF": ("franco suizo", "francos suizos"),
            "JPY": ("yen", "yenes"),
            "MXN": ("peso", "pesos"),
            "KRW": ("won", "wones"),
            "VND": ("dong", "dongs"),
            "MNT": ("tugrik", "tugriks"),
        },
    }
    pair = names.get(base_language(language), {}).get(code)
    if pair is None:
        return code
    return pair[0] if singular else pair[1]


def render_exchange_amount(
    raw: str,
    code: str,
    language: str,
    *,
    symbol: str | None = None,
) -> str | None:
    """Render a decimal exchange-rate amount with major-unit naming."""
    parsed = parse_currency_decimal(raw, language)
    canonical_id = ISO_TO_CANONICAL.get(code.upper())
    if parsed is None or canonical_id is None:
        return None
    lexeme, value = parsed
    if base_language(language) == "de" and symbol in {"$", "£"}:
        major = (
            "ein"
            if int(lexeme.integer_digits) == 1
            else number_words(int(lexeme.integer_digits), lang=language)
        )
        if lexeme.negative:
            major = f"minus {major}"
        minor = ""
        if lexeme.fraction_digits:
            minor_value = int(lexeme.fraction_digits[:2].ljust(2, "0"))
            if minor_value:
                minor = f" {number_words(minor_value, lang=language)}"
        numeric = f"{major}{minor}"
    else:
        numeric = number_words(value, lang=language, to="decimal")
        if base_language(language) == "en":
            numeric = numeric.replace("-", " ")
        if base_language(language) == "de" and value == 1:
            numeric = "ein"
    if base_language(language) == "de" and symbol in {"$", "£"}:
        return f"{major} {currency_major_name(canonical_id, language, singular=value == 1)}{minor}"
    return f"{numeric} {currency_major_name(canonical_id, language, singular=value == 1)}"


__all__ = [
    "CANONICAL_TO_ISO",
    "canonical_currency_id",
    "currency_code",
    "currency_decimal",
    "currency_major_name",
    "parse_currency_decimal",
    "render_currency_text",
    "render_exchange_amount",
]
