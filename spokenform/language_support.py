"""Orthogonal capability metadata for supported Spokenform languages."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .language import (
    KOKOROG2P_PROFILE_LANGUAGES,
    base_language,
    normalize_language,
    resolve_numeralform_locale,
)

REVIEWED_STRUCTURED_LANGUAGES = frozenset(
    {"cs", "de", "en", "es", "fr", "it", "ja", "ko", "pt", "ru", "sv", "th", "vi", "zh"}
)
CONSERVATIVE_INTEGRATION_LANGUAGES = frozenset({"ar", "he", "kk"})
SEQUENCE_POLICY_LANGUAGES = frozenset(
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
SHARED_SEQUENCE_RECOGNIZER_LANGUAGES = REVIEWED_STRUCTURED_LANGUAGES - {"ja", "ko", "zh"}
REVIEWED_NUMERIC_PUNCTUATION_LANGUAGES = frozenset(
    {"de", "en", "es", "fr", "it", "ja", "ko", "pt", "ru", "sv", "th", "vi", "zh"}
)


class SupportTier(str, Enum):
    FOUNDATION = "foundation"
    REVIEWED_STRUCTURED = "reviewed_structured"
    CONSERVATIVE_INTEGRATION = "conservative_integration"


@dataclass(frozen=True, slots=True)
class LanguageSupport:
    language: str
    base: str
    abbreviation_language: str
    number_backend: str | None
    number_language: str | None
    number_backend_available: bool
    tier: SupportTier
    exact_locale: bool
    plain_cardinals: bool
    decimal_policy: bool
    structured: bool
    sequence_policy: bool
    kokorog2p_profile: bool


def _number_capability(language: str) -> tuple[str | None, str | None]:
    base = base_language(language)
    if base == "zh":
        return "cn2an", language
    try:
        resolved = resolve_numeralform_locale(language)
    except ValueError:
        return None, None
    return "numeralform", resolved


def language_support(language: str) -> LanguageSupport:
    """Describe specialist capabilities for one supported language input."""
    normalized = normalize_language(language)
    base = base_language(normalized)
    backend, number_language = _number_capability(normalized)
    if base in REVIEWED_STRUCTURED_LANGUAGES:
        tier = SupportTier.REVIEWED_STRUCTURED
    elif base in CONSERVATIVE_INTEGRATION_LANGUAGES:
        tier = SupportTier.CONSERVATIVE_INTEGRATION
    else:
        tier = SupportTier.FOUNDATION
    return LanguageSupport(
        language=normalized,
        base=base,
        abbreviation_language=normalized,
        number_backend=backend,
        number_language=number_language,
        number_backend_available=backend is not None,
        tier=tier,
        exact_locale="_" in normalized,
        plain_cardinals=backend is not None and base not in {"hi", "hy", "mn"},
        decimal_policy=base in REVIEWED_NUMERIC_PUNCTUATION_LANGUAGES,
        structured=base in REVIEWED_STRUCTURED_LANGUAGES,
        sequence_policy=base in SEQUENCE_POLICY_LANGUAGES,
        kokorog2p_profile=base in KOKOROG2P_PROFILE_LANGUAGES,
    )


def language_has_plain_number_backend(language: str) -> bool:
    return language_support(language).plain_cardinals


def language_has_reviewed_structured_numbers(language: str) -> bool:
    return language_support(language).structured


def supported_profile_languages() -> frozenset[str]:
    """Return the independent KokoroG2P profile language set."""
    return KOKOROG2P_PROFILE_LANGUAGES


__all__ = [
    "CONSERVATIVE_INTEGRATION_LANGUAGES",
    "LanguageSupport",
    "REVIEWED_NUMERIC_PUNCTUATION_LANGUAGES",
    "REVIEWED_STRUCTURED_LANGUAGES",
    "SEQUENCE_POLICY_LANGUAGES",
    "SHARED_SEQUENCE_RECOGNIZER_LANGUAGES",
    "SupportTier",
    "language_has_plain_number_backend",
    "language_has_reviewed_structured_numbers",
    "language_support",
    "supported_profile_languages",
]
