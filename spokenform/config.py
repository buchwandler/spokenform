"""Configuration for the spokenform preparation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Literal

from .language import base_language, normalize_language


class NumberPolicy(str, Enum):
    """Ownership policy for numeric normalization."""

    NONE = "none"
    PLAIN = "plain"
    STRUCTURED_AND_PLAIN = "structured_and_plain"
    CALLER_MANAGED = "caller_managed"


SymbolMode = Literal["none", "remove", "keep"]
GenericAcronymCase = Literal["upper", "lower"]


def number_policy_for_language(language: str) -> NumberPolicy:
    """Return the initial kokorog2p policy for a normalized language code."""
    base = base_language(language)
    if base == "de":
        return NumberPolicy.STRUCTURED_AND_PLAIN
    if base == "en":
        return NumberPolicy.STRUCTURED_AND_PLAIN
    if base == "cs":
        return NumberPolicy.STRUCTURED_AND_PLAIN
    if base in {"es", "it", "pt"}:
        return NumberPolicy.STRUCTURED_AND_PLAIN
    if base == "fr":
        return NumberPolicy.STRUCTURED_AND_PLAIN
    return NumberPolicy.NONE


@dataclass(frozen=True, slots=True)
class PreparationConfig:
    """Immutable options controlling single-language written-to-spoken preparation."""

    language: str = "en"
    use_spacy: bool | None = None
    spacy_model: str | None = None
    expand_abbreviations: bool = True
    expand_structured: bool = True
    normalize_literals: bool = False
    expand_numbers: bool = True
    normalize_whitespace: bool = True
    normalize_unicode: bool = True
    strip_outer_whitespace: bool = True
    collapse_horizontal_whitespace: bool = True
    normalize_line_whitespace: bool = True
    collapse_blank_lines: bool = True
    number_policy: NumberPolicy | None = None
    preserve_run_boundaries: bool = False
    model_punctuation: bool = False
    symbol_mode: SymbolMode = "none"
    keep_symbols: str = ""
    generic_acronym_case: GenericAcronymCase = "upper"
    context: bool = True
    strict: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.language, str):
            raise TypeError("language must be a string")
        if not self.language.strip():
            raise ValueError("language must not be empty")
        object.__setattr__(self, "language", normalize_language(self.language))
        if self.use_spacy is not None and not isinstance(self.use_spacy, bool):
            raise TypeError("use_spacy must be a bool or None")
        if self.spacy_model is not None:
            if not isinstance(self.spacy_model, str):
                raise TypeError("spacy_model must be a string or None")
            if not self.spacy_model.strip():
                raise ValueError("spacy_model must not be empty")
        if self.number_policy is not None and not isinstance(self.number_policy, NumberPolicy):
            raise TypeError("number_policy must be a NumberPolicy or None")
        if self.symbol_mode not in {"none", "remove", "keep"}:
            raise ValueError("symbol_mode must be 'none', 'remove', or 'keep'")
        if not isinstance(self.keep_symbols, str):
            raise TypeError("keep_symbols must be a string")
        if self.symbol_mode != "keep" and self.keep_symbols:
            raise ValueError("keep_symbols is only valid when symbol_mode='keep'")
        if self.symbol_mode == "keep" and not self.keep_symbols:
            raise ValueError(
                "keep_symbols must not be empty when symbol_mode='keep'; "
                "use symbol_mode='remove' to remove all symbols"
            )
        if self.generic_acronym_case not in {"upper", "lower"}:
            raise ValueError("generic_acronym_case must be 'upper' or 'lower'")
        for name in (
            "expand_abbreviations",
            "expand_structured",
            "normalize_literals",
            "expand_numbers",
            "normalize_whitespace",
            "normalize_unicode",
            "strip_outer_whitespace",
            "collapse_horizontal_whitespace",
            "normalize_line_whitespace",
            "collapse_blank_lines",
            "preserve_run_boundaries",
            "model_punctuation",
            "context",
            "strict",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a bool")

    @classmethod
    def for_kokorog2p(cls, language: str) -> PreparationConfig:
        """Return a one-language profile safe for kokorog2p adapters."""
        return cls(
            language=language,
            use_spacy=False,
            normalize_unicode=True,
            normalize_whitespace=True,
            strip_outer_whitespace=False,
            collapse_horizontal_whitespace=True,
            normalize_line_whitespace=True,
            collapse_blank_lines=True,
            preserve_run_boundaries=True,
            model_punctuation=False,
            number_policy=number_policy_for_language(language),
        )


__all__ = [
    "GenericAcronymCase",
    "NumberPolicy",
    "PreparationConfig",
    "SymbolMode",
    "number_policy_for_language",
]
