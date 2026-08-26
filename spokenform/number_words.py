"""Locale-routed number word rendering."""

from __future__ import annotations

from decimal import Decimal

import cn2an
from num2words import num2words

from .language import base_language, normalize_language, resolve_num2words_language

Number = int | str | Decimal


def number_backend_for_language(language: str) -> str:
    """Return the backend responsible for a supported language family."""
    return "cn2an" if base_language(language) == "zh" else "num2words"


def cardinal(value: Number, language: str) -> str:
    """Render a cardinal number with the language's released backend."""
    normalized = normalize_language(language)
    if number_backend_for_language(normalized) == "cn2an":
        return cn2an.an2cn(str(value), "low")
    return str(num2words(value, lang=resolve_num2words_language(normalized)))


def number_words(
    value: Number, *, lang: str, to: str = "cardinal", currency: str | None = None
) -> str:
    """Compatibility-shaped facade for migrated production callers."""
    if to == "cardinal":
        return cardinal(value, lang)
    if to == "ordinal":
        if not isinstance(value, int):
            raise TypeError("ordinal values must be integers")
        return ordinal(value, lang)
    normalized = normalize_language(lang)
    if number_backend_for_language(normalized) == "cn2an":
        raise ValueError(f"{to!r} rendering is not supported for {normalized!r}")
    kwargs: dict[str, object] = {"lang": resolve_num2words_language(normalized), "to": to}
    if currency is not None:
        kwargs["currency"] = currency
    return str(num2words(value, **kwargs))


def ordinal(value: int, language: str) -> str:
    """Render an ordinal, rejecting languages without an ordinal contract."""
    normalized = normalize_language(language)
    if number_backend_for_language(normalized) == "cn2an":
        raise ValueError(f"Ordinal rendering is not supported for {normalized!r}")
    return str(num2words(value, lang=resolve_num2words_language(normalized), to="ordinal"))


def year(value: int, language: str) -> str:
    """Render a year as a cardinal number.

    Locale date renderers may apply a distinct year policy before calling this
    helper.
    """
    return cardinal(value, language)


def digits(value: str, language: str) -> tuple[str, ...]:
    """Render a string of decimal digits one at a time."""
    if not value or not value.isdecimal():
        raise ValueError("digits must contain only decimal digits")
    normalized = normalize_language(language)
    if number_backend_for_language(normalized) == "cn2an":
        return tuple(cn2an.an2cn(value, "direct"))
    return tuple(cardinal(int(character), normalized) for character in value)


__all__ = ["cardinal", "digits", "number_backend_for_language", "ordinal", "year"]
