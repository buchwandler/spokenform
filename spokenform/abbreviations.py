"""Public abbreviation customization owned by Spokenform."""

from __future__ import annotations

from abbr2words import (
    AbbreviationContext,
    AbbreviationEntry,
    AbbreviationExpander,
    ExpansionResult,
    ProtectedSpan,
    TokenAnnotation,
    abbreviation_guards_match,
    get_shared_expander,
    reset_expanders,
)

from .language import resolve_abbr2words_language

normalize_language = resolve_abbr2words_language


def add_abbreviation(
    abbreviation: str,
    expansion: str,
    *,
    language: str = "en",
    description: str = "",
    case_sensitive: bool = False,
) -> None:
    """Register a custom abbreviation in Spokenform's shared registry."""
    if not isinstance(expansion, str):
        raise TypeError("expansion must be a string")
    get_shared_expander(resolve_abbr2words_language(language), context=True).add_abbreviation(
        AbbreviationEntry(
            abbreviation,
            expansion,
            description=description,
            case_sensitive=case_sensitive,
            origin="custom",
        )
    )


def remove_abbreviation(
    abbreviation: str, *, language: str = "en", case_sensitive: bool = False
) -> bool:
    """Remove a custom or bundled abbreviation from one language registry."""
    return get_shared_expander(
        resolve_abbr2words_language(language), context=True
    ).remove_abbreviation(abbreviation, case_sensitive=case_sensitive)


def has_abbreviation(
    abbreviation: str, *, language: str = "en", case_sensitive: bool = False
) -> bool:
    """Return whether an abbreviation is registered for one language."""
    return get_shared_expander(
        resolve_abbr2words_language(language), context=True
    ).has_abbreviation(abbreviation, case_sensitive=case_sensitive)


def get_expander_class(language: str = "en") -> type[AbbreviationExpander]:
    """Return the locale-specific registry class used by Spokenform."""
    return type(get_shared_expander(resolve_abbr2words_language(language), context=True))


def reset_abbreviations(language: str | None = None) -> None:
    """Reset Spokenform's abbreviation registries."""
    reset_expanders(None if language is None else resolve_abbr2words_language(language))


__all__ = [
    "AbbreviationContext",
    "AbbreviationEntry",
    "AbbreviationExpander",
    "ExpansionResult",
    "ProtectedSpan",
    "TokenAnnotation",
    "abbreviation_guards_match",
    "add_abbreviation",
    "get_shared_expander",
    "get_expander_class",
    "has_abbreviation",
    "normalize_language",
    "remove_abbreviation",
    "reset_abbreviations",
    "reset_expanders",
]
