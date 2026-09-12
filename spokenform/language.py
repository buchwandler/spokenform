"""Language identifiers and dependency-specific language selection."""

from __future__ import annotations

from typing import Final

import numeralform
from abbr2words import (
    normalize_language as normalize_abbr2words_language,
)
from abbr2words import (
    supported_languages as abbr2words_supported_languages,
)

_LANGUAGE_ALIASES: Final[dict[str, str]] = {
    "jp": "ja",
    "cn": "zh_CN",
    "ara": "ar",
    "msa": "ar",
    "heb": "he",
    "kaz": "kk",
    "kz": "kk",
}
_BASE_LANGUAGE_ALIASES: Final[dict[str, str]] = {
    "swe": "sv",
    "rus": "ru",
    "ar": "ar",
    "he": "he",
    "kk": "kk",
}
KOKOROG2P_PROFILE_VERSION: Final[str] = "0.3.2"
KOKOROG2P_PROFILE_LANGUAGES: Final[frozenset[str]] = frozenset(
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

_ABBR2WORDS_LANGUAGE_ALIASES: Final[dict[str, str]] = {
    "kk": "kz",
}

_RAW_ABBR2WORDS_LANGUAGES: Final[tuple[str, ...]] = abbr2words_supported_languages(
    include_locales=True
)
_RAW_ABBR2WORDS_LOCALES: Final[frozenset[str]] = frozenset(
    code for code in _RAW_ABBR2WORDS_LANGUAGES if "_" in code
)
_RAW_ABBR2WORDS_BASES: Final[frozenset[str]] = frozenset(
    code for code in _RAW_ABBR2WORDS_LANGUAGES if "_" not in code
)

# Public Spokenform keeps kk as its canonical Kazakh key while the dependency
# registries expose kz. The remaining keys are owned by abbr2words.
SUPPORTED_BASE_LANGUAGES: Final[tuple[str, ...]] = tuple(
    sorted(_LANGUAGE_ALIASES.get(code, code) for code in _RAW_ABBR2WORDS_BASES)
)
SUPPORTED_LOCALES: Final[tuple[str, ...]] = tuple(sorted(_RAW_ABBR2WORDS_LOCALES))
SUPPORTED_LANGUAGE_KEYS: Final[tuple[str, ...]] = tuple(
    sorted((*SUPPORTED_BASE_LANGUAGES, *SUPPORTED_LOCALES))
)
_COMPATIBILITY_LOCALES: Final[frozenset[str]] = frozenset({"pt_PT"})


def canonicalize_language(language: str) -> str:
    """Normalize language syntax and compatibility aliases without validation."""
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


def normalize_language(language: str) -> str:
    """Return a supported canonical Spokenform language identifier.

    Exact registered locales are retained. Other regional inputs resolve to
    their registered base language, and unknown language families are rejected.
    """
    requested = canonicalize_language(language)
    if requested in _COMPATIBILITY_LOCALES:
        return requested
    if requested in SUPPORTED_LANGUAGE_KEYS:
        return requested
    base = requested.split("_", 1)[0]
    if base in SUPPORTED_BASE_LANGUAGES:
        return base
    supported_text = ", ".join(SUPPORTED_LANGUAGE_KEYS)
    raise ValueError(f"Unsupported language {language!r}; Spokenform supports: {supported_text}")


def base_language(language: str) -> str:
    """Return the base language component of a supported identifier."""
    return normalize_language(language).split("_", 1)[0]


def supported_languages(*, include_locales: bool = False) -> tuple[str, ...]:
    """Return supported base families or all public language keys."""
    return SUPPORTED_LANGUAGE_KEYS if include_locales else SUPPORTED_BASE_LANGUAGES


def supports_language(language: str) -> bool:
    """Return whether an input resolves to a supported Spokenform language."""
    try:
        normalize_language(language)
    except (TypeError, ValueError):
        return False
    return True


def supports_profile(language: str, profile: str = "kokorog2p") -> bool:
    """Return whether a language has an explicit integration preparation profile."""
    if profile != "kokorog2p":
        return False
    try:
        return base_language(language) in KOKOROG2P_PROFILE_LANGUAGES
    except (TypeError, ValueError):
        return False


def resolve_numeralform_locale(language: str) -> str:
    """Resolve a Spokenform language to a Numeralform BCP-47 locale."""
    normalized = normalize_language(language)
    requested = normalized.replace("_", "-")
    try:
        return numeralform.resolve_locale(requested)
    except ValueError as exc:
        raise ValueError(
            f"Unsupported language {language!r}; Numeralform supports locale {requested!r}"
        ) from exc


def resolve_abbr2words_language(language: str) -> str:
    """Select an exact abbr2words language or its supported base fallback."""
    requested = normalize_language(language)
    dependency_language = _ABBR2WORDS_LANGUAGE_ALIASES.get(
        base_language(requested), base_language(requested)
    )
    if "_" in requested:
        dependency_language = f"{dependency_language}_{requested.split('_', 1)[1]}"
    try:
        return normalize_abbr2words_language(dependency_language)
    except ValueError:
        return normalize_abbr2words_language(dependency_language.split("_", 1)[0])


__all__ = [
    "KOKOROG2P_PROFILE_LANGUAGES",
    "KOKOROG2P_PROFILE_VERSION",
    "SUPPORTED_BASE_LANGUAGES",
    "SUPPORTED_LANGUAGE_KEYS",
    "SUPPORTED_LOCALES",
    "base_language",
    "canonicalize_language",
    "normalize_language",
    "resolve_abbr2words_language",
    "resolve_numeralform_locale",
    "supported_languages",
    "supports_language",
    "supports_profile",
]
