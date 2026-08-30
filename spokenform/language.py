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
    "ara": "ar",
    "msa": "ar",
    "heb": "he",
    "kaz": "kk",
}
_BASE_LANGUAGE_ALIASES: Final[dict[str, str]] = {
    "swe": "sv",
    "rus": "ru",
    "ar": "ar",
    "he": "he",
    "kk": "kk",
}
KOKOROG2P_PROFILE_VERSION: Final[str] = "0.3.2"
_KOKOROG2P_PROFILES: Final[frozenset[str]] = frozenset(
    {
        "ar",
        "cs",
        "de",
        "en",
        "es",
        "fr",
        "he",
        "it",
        "ja",
        "kk",
        "ko",
        "pt",
        "ru",
        "sv",
        "th",
        "vi",
        "zh",
    }
)
SUPPORTED_BASE_LANGUAGES: Final[tuple[str, ...]] = tuple(sorted(_KOKOROG2P_PROFILES))
_DEPENDENCY_LANGUAGE_ALIASES: Final[dict[str, str]] = {
    # Spokenform exposes the product-standard kk name while both supported
    # semantic dependencies publish their Kazakh tables as kz.
    "kk": "kz",
}


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
    base = _BASE_LANGUAGE_ALIASES.get(parts[0].casefold(), parts[0].lower())
    if len(parts) == 1:
        return base
    return f"{base}_{parts[1].upper()}"


def base_language(language: str) -> str:
    """Return the base language component of a normalized identifier."""
    return normalize_language(language).split("_", 1)[0]


def supported_languages() -> tuple[str, ...]:
    """Return Spokenform's supported base language identifiers."""
    return SUPPORTED_BASE_LANGUAGES


def supports_profile(language: str, profile: str = "kokorog2p") -> bool:
    """Return whether a language has an explicit integration preparation profile."""
    if profile != "kokorog2p":
        return False
    try:
        return base_language(language) in _KOKOROG2P_PROFILES
    except (TypeError, ValueError):
        return False


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
    requested = normalize_language(language)
    dependency_language = _DEPENDENCY_LANGUAGE_ALIASES.get(
        base_language(requested),
        requested,
    )
    return _resolve_dependency_language(dependency_language, CONVERTER_CLASSES)


_EXACT_ABBR2WORDS_LOCALES = frozenset({"es_MX", "zh_CN"})


def resolve_abbr2words_language(language: str) -> str:
    """Select an exact abbr2words language or its supported base fallback."""
    requested = normalize_language(language)
    dependency_language = _DEPENDENCY_LANGUAGE_ALIASES.get(
        base_language(requested),
        requested,
    )
    # Regional abbr2words tables can expose the base inventory under a
    # variant name without providing a distinct abbreviation contract.  The
    # Mexican Spanish table is the reviewed exception: its currency symbols
    # have a different canonical identity and must remain locale-specific.
    if dependency_language not in _EXACT_ABBR2WORDS_LOCALES and "_" in dependency_language:
        dependency_language = base_language(dependency_language)
    supported = {normalize_language(code) for code in abbr2words_supported_languages()}
    usable: set[str] = set()
    for code in supported:
        try:
            unit_entries(code)
        except KeyError:
            continue
        else:
            usable.add(code)
    return _resolve_dependency_language(dependency_language, usable)


__all__ = [
    "SUPPORTED_BASE_LANGUAGES",
    "base_language",
    "normalize_language",
    "resolve_abbr2words_language",
    "resolve_num2words_language",
    "KOKOROG2P_PROFILE_VERSION",
    "supports_profile",
    "supported_languages",
]
