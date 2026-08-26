"""Language identifiers and dependency-specific language selection."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from abbr2words import supported_languages as abbr2words_supported_languages
from abbr2words.units import unit_entries
from num2words import CONVERTER_CLASSES

_LANGUAGE_ALIASES: Final[dict[str, str]] = {
    "jp": "ja",
    "cn": "zh_CN",
}

SUPPORTED_BASE_LANGUAGES: Final[tuple[str, ...]] = (
    "cs",
    "de",
    "en",
    "es",
    "fr",
    "it",
    "ja",
    "ko",
    "pt",
    "zh",
)


def normalize_language(language: str) -> str:
    """Return a canonical Spokenform language identifier.

    Base language codes are lower-case and regional subtags are upper-case,
    with hyphens accepted as input for interoperability with BCP-47 sources.
    """
    if not isinstance(language, str):
        raise TypeError("language must be a string")
    value = language.strip()
    if not value:
        raise ValueError("language must not be empty")
    alias = _LANGUAGE_ALIASES.get(value.casefold())
    if alias is not None:
        return alias
    value = value.replace("-", "_")
    parts = value.split("_", 1)
    base = parts[0].lower()
    if len(parts) == 1:
        return base
    return f"{base}_{parts[1].upper()}"


def base_language(language: str) -> str:
    """Return the base language component of a normalized identifier."""
    return normalize_language(language).split("_", 1)[0]


def supported_languages() -> tuple[str, ...]:
    """Return Spokenform's supported base language identifiers."""
    return SUPPORTED_BASE_LANGUAGES


def _resolve_dependency_language(language: str, supported: Iterable[str]) -> str:
    requested = normalize_language(language)
    supported_codes = {normalize_language(code) for code in supported}
    if requested in supported_codes:
        return requested
    base = base_language(requested)
    if base in supported_codes:
        return base
    supported_text = ", ".join(sorted(supported_codes))
    raise ValueError(f"Unsupported language {language!r}; dependency supports: {supported_text}")


def resolve_num2words_language(language: str) -> str:
    """Select an exact num2words language or its supported base fallback."""
    return _resolve_dependency_language(language, CONVERTER_CLASSES)


_EXACT_ABBR2WORDS_LOCALES = frozenset({"es_MX", "zh_CN"})


def resolve_abbr2words_language(language: str) -> str:
    """Select an exact abbr2words language or its supported base fallback."""
    requested = normalize_language(language)
    # Regional abbr2words tables can expose the base inventory under a
    # variant name without providing a distinct abbreviation contract.  The
    # Mexican Spanish table is the reviewed exception: its currency symbols
    # have a different canonical identity and must remain locale-specific.
    if requested not in _EXACT_ABBR2WORDS_LOCALES and "_" in requested:
        return base_language(requested)
    supported = {normalize_language(code) for code in abbr2words_supported_languages()}
    usable: set[str] = set()
    for code in supported:
        try:
            unit_entries(code)
        except KeyError:
            continue
        else:
            usable.add(code)
    return _resolve_dependency_language(requested, usable)


__all__ = [
    "SUPPORTED_BASE_LANGUAGES",
    "base_language",
    "normalize_language",
    "resolve_abbr2words_language",
    "resolve_num2words_language",
    "supported_languages",
]
