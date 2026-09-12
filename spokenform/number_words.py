"""Provider-neutral locale-routed number word rendering."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

import cn2an
import numeralform

from .language import base_language, normalize_language, resolve_numeralform_locale

Number = int | str | Decimal
_INTEGER_RE = re.compile(r"^[+-]?\d+$")


@dataclass(frozen=True, slots=True)
class NumberBackend:
    """A released backend and dependency locale selected for one input."""

    name: str
    language: str


def resolve_number_backend(language: str) -> NumberBackend | None:
    """Return the installed number backend, or ``None`` when unavailable."""
    normalized = normalize_language(language)
    if base_language(normalized) == "zh":
        return NumberBackend("cn2an", normalized)
    try:
        numeralform_locale = resolve_numeralform_locale(normalized)
    except ValueError:
        return None
    return NumberBackend("numeralform", numeralform_locale)


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


def _coerce_numeralform_value(value: Number) -> int | Decimal:
    if isinstance(value, bool):
        raise TypeError("number must be an integer or Decimal")
    if isinstance(value, int | Decimal):
        return value
    text = value.strip()
    if _INTEGER_RE.fullmatch(text):
        return int(text)
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Cannot parse numeric value {value!r}") from exc


def _render_numeralform(
    value: Number,
    language: str,
    *,
    form: str | None = None,
    style: str | None = None,
) -> str:
    """Render Numeralform with narrowly scoped reviewed compatibility spellings."""
    backend = require_number_backend(language)
    if backend.name == "cn2an":
        raise ValueError(
            f"Numeralform rendering is not supported for {normalize_language(language)!r}"
        )
    rendered_value = _coerce_numeralform_value(value)
    if (
        style is None
        and base_language(language) == "en"
        and form in {None, "cardinal"}
        and isinstance(rendered_value, int)
    ):
        style = "british-and"
    try:
        rendered = numeralform.render(
            rendered_value,
            locale=backend.language,
            form=form,
            style=style,
        )
        if base_language(language) == "de" and form == "ordinal" and rendered_value in {100, 1000}:
            rendered = rendered.removeprefix("ein")
        if (
            base_language(language) == "en"
            and form in {None, "cardinal"}
            and isinstance(rendered_value, int)
        ):
            rendered = re.sub(
                r"\b(thousand|million|billion|trillion) (?=[a-z-]+ hundred\b)",
                r"\1, ",
                rendered,
            )
        return rendered
    except numeralform.NumeralFormError as exc:
        if (
            base_language(language) == "de"
            and form in {None, "cardinal"}
            and rendered_value == 1_000_000_000_000
        ):
            return "eine Billion"
        requested_form = form or "cardinal"
        raise ValueError(
            f"Cannot render {requested_form} for {normalize_language(language)!r}: {exc}"
        ) from exc


def cardinal(value: Number, language: str) -> str:
    """Render a cardinal number with the language's released backend."""
    backend = require_number_backend(language)
    if backend.name == "cn2an":
        return cn2an.an2cn(str(value), "low")
    return _render_numeralform(value, language)


def ordinal(value: int, language: str) -> str:
    """Render an ordinal, rejecting languages without an ordinal contract."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("ordinal values must be integers")
    backend = require_number_backend(language)
    if backend.name == "cn2an":
        raise ValueError(f"Ordinal rendering is not supported for {normalize_language(language)!r}")
    return _render_numeralform(value, language, form="ordinal")


def year(value: int, language: str) -> str:
    """Render a semantic year with Numeralform year semantics."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("year values must be integers")
    backend = require_number_backend(language)
    if backend.name == "cn2an":
        return cardinal(value, language)
    return _render_numeralform(value, language, form="year")


def decimal(value: Decimal, language: str) -> str:
    """Render a Decimal while retaining its visible fractional precision."""
    if not isinstance(value, Decimal):
        raise TypeError("decimal values must be Decimal instances")
    return _render_numeralform(value, language, form="decimal")


def currency(value: Number, language: str, currency_code: str) -> str:
    """Render a currency amount through Numeralform's currency API."""
    backend = require_number_backend(language)
    if backend.name == "cn2an":
        raise ValueError(
            f"Currency rendering is not supported for {normalize_language(language)!r}"
        )
    try:
        return numeralform.render_currency(
            _coerce_numeralform_value(value),
            locale=backend.language,
            currency=currency_code,
        )
    except numeralform.NumeralFormError as exc:
        raise ValueError(
            f"Cannot render currency for {normalize_language(language)!r}: {exc}"
        ) from exc


def digits(value: str, language: str) -> tuple[str, ...]:
    """Render a string of decimal digits one at a time."""
    if not value or not value.isdecimal():
        raise ValueError("digits must contain only decimal digits")
    backend = require_number_backend(language)
    if backend.name == "cn2an":
        return tuple(cn2an.an2cn(value, "direct"))
    return tuple(cardinal(int(character), language) for character in value)


def number_words(
    value: Number, *, lang: str, to: str = "cardinal", currency: str | None = None
) -> str:
    """Compatibility-shaped facade for existing Spokenform production callers."""
    if to == "cardinal":
        return cardinal(value, lang)
    if to == "ordinal":
        if not isinstance(value, int):
            raise TypeError("ordinal values must be integers")
        return ordinal(value, lang)
    if to == "year":
        if not isinstance(value, int):
            raise TypeError("year values must be integers")
        return year(value, lang)
    if to == "decimal":
        if not isinstance(value, Decimal):
            raise TypeError("decimal values must be Decimal instances")
        return decimal(value, lang)
    if to == "currency":
        if currency is None:
            raise ValueError("currency is required for currency rendering")
        return globals()["currency"](value, lang, currency)
    raise ValueError(f"{to!r} rendering is not supported for {normalize_language(lang)!r}")


__all__ = [
    "NumberBackend",
    "cardinal",
    "currency",
    "decimal",
    "digits",
    "number_backend_for_language",
    "number_words",
    "ordinal",
    "require_number_backend",
    "resolve_number_backend",
    "year",
]
