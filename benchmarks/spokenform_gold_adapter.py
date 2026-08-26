"""Thin adapter from Spokenform Gold records to the public Spokenform API."""

from __future__ import annotations

from typing import Any

from spokenform import prepare

_SUPPORTED_PREPARE_KEYS = {
    "use_spacy",
    "spacy_model",
    "normalize_literals",
    "expand_abbreviations",
    "expand_structured",
    "expand_numbers",
    "normalize_whitespace",
    "normalize_unicode",
    "strip_outer_whitespace",
    "collapse_horizontal_whitespace",
    "normalize_line_whitespace",
    "collapse_blank_lines",
    "preserve_run_boundaries",
    "model_punctuation",
    "symbol_mode",
    "keep_symbols",
    "generic_acronym_mode",
    "generic_acronym_case",
    "long_number_mode",
    "registered_acronym_mode",
    "context",
    "interpretation_mode",
    "disabled_domains",
    "allowed_domains",
    "sequence_fallback_mode",
    "strict",
}


def prepare_gold_record(
    text: str,
    language: str,
    locale: str,
    profile: dict[str, Any] | None = None,
) -> str:
    """Prepare one Gold input using a frozen profile and return plain text."""
    if not isinstance(language, str) or not language:
        raise ValueError("Gold language must be a non-empty string")
    if not isinstance(locale, str) or not locale:
        raise ValueError("Gold locale must be a non-empty string")
    language_base = language.split("-", 1)[0].lower()
    locale_base = locale.split("-", 1)[0].lower()
    if language_base != locale_base:
        raise ValueError(f"Gold language {language!r} does not match locale {locale!r}")

    if profile is None or profile.get("name") != "gold-v1":
        raise ValueError("Spokenform benchmark expects the gold-v1 profile")
    kwargs = dict((profile or {}).get("prepare_kwargs", {}))
    unknown = sorted(set(kwargs) - _SUPPORTED_PREPARE_KEYS)
    if unknown:
        raise ValueError(f"Gold profile contains unsupported Spokenform options: {unknown}")
    prepared = prepare(text, language=language_base, **kwargs)
    return prepared.spoken_text
