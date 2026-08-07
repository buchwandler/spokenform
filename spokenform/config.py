"""Configuration for the spokenform preparation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class NumberPolicy(str, Enum):
    """Ownership policy for numeric normalization."""

    NONE = "none"
    PLAIN = "plain"
    STRUCTURED_AND_PLAIN = "structured_and_plain"
    CALLER_MANAGED = "caller_managed"


def number_policy_for_language(language: str) -> NumberPolicy:
    """Return the initial kokorog2p policy for a normalized language code."""
    base = language.strip().lower().replace("_", "-").split("-", 1)[0]
    if base == "de":
        return NumberPolicy.STRUCTURED_AND_PLAIN
    if base in {"cs", "es", "fr", "it", "pt", "en"}:
        return NumberPolicy.CALLER_MANAGED
    return NumberPolicy.NONE


@dataclass(frozen=True, slots=True)
class PreparationConfig:
    """Immutable options controlling single-language written-to-spoken preparation."""

    language: str = "en"
    use_spacy: bool | None = None
    spacy_model: str | None = None
    expand_abbreviations: bool = True
    expand_structured: bool = True
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
    context: bool = True
    strict: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.language, str):
            raise TypeError("language must be a string")
        if not self.language.strip():
            raise ValueError("language must not be empty")
        if self.use_spacy is not None and not isinstance(self.use_spacy, bool):
            raise TypeError("use_spacy must be a bool or None")
        if self.spacy_model is not None:
            if not isinstance(self.spacy_model, str):
                raise TypeError("spacy_model must be a string or None")
            if not self.spacy_model.strip():
                raise ValueError("spacy_model must not be empty")
        if self.number_policy is not None and not isinstance(self.number_policy, NumberPolicy):
            raise TypeError("number_policy must be a NumberPolicy or None")
        for name in (
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


__all__ = ["NumberPolicy", "PreparationConfig", "number_policy_for_language"]
