"""Locale-routed number word rendering."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

import cn2an
from num2words import num2words

from .language import base_language, normalize_language, resolve_num2words_language

Number = int | str | Decimal


@dataclass(frozen=True, slots=True)
class NumberBackend:
    """A released backend and dependency language selected for one input."""

    name: str
    language: str


def resolve_number_backend(language: str) -> NumberBackend | None:
    """Return the installed number backend, or ``None`` when unavailable."""
    normalized = normalize_language(language)
    if base_language(normalized) == "zh":
        return NumberBackend("cn2an", normalized)
    try:
        dependency_language = resolve_num2words_language(normalized)
    except ValueError:
        return None
    return NumberBackend("num2words", dependency_language)


def require_number_backend(language: str) -> NumberBackend:
    """Return a number backend or raise for direct rendering callers."""
    backend = resolve_number_backend(language)
    if backend is None:
        normalized = normalize_language(language)
        raise ValueError(f"No released numeric backend for language {normalized!r}")
    return backend


def number_backend_for_language(language: str) -> str:
    """Return the backend responsible for a supported language family."""
    return require_number_backend(language).name


def cardinal(value: Number, language: str) -> str:
    """Render a cardinal number with the language's released backend."""
    backend = require_number_backend(language)
    if backend.name == "cn2an":
        return cn2an.an2cn(str(value), "low")
    return str(num2words(value, lang=backend.language))


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
    backend = require_number_backend(lang)
    if backend.name == "cn2an":
        raise ValueError(f"{to!r} rendering is not supported for {normalize_language(lang)!r}")
    kwargs: dict[str, object] = {"lang": backend.language, "to": to}
    if currency is not None:
        kwargs["currency"] = currency
    return str(num2words(value, **kwargs))


def ordinal(value: int, language: str) -> str:
    """Render an ordinal, rejecting languages without an ordinal contract."""
    backend = require_number_backend(language)
    if backend.name == "cn2an":
        raise ValueError(f"Ordinal rendering is not supported for {normalize_language(language)!r}")
    return str(num2words(value, lang=backend.language, to="ordinal"))


def year(value: int, language: str) -> str:
    """Render a year as a cardinal number."""
    return cardinal(value, language)


def digits(value: str, language: str) -> tuple[str, ...]:
    """Render a string of decimal digits one at a time."""
    if not value or not value.isdecimal():
        raise ValueError("digits must contain only decimal digits")
    backend = require_number_backend(language)
    if backend.name == "cn2an":
        return tuple(cn2an.an2cn(value, "direct"))
    return tuple(cardinal(int(character), language) for character in value)


__all__ = [
    "NumberBackend",
    "cardinal",
    "digits",
    "number_backend_for_language",
    "number_words",
    "ordinal",
    "require_number_backend",
    "resolve_number_backend",
    "year",
]
