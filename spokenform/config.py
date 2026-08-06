"""Configuration for the spokenform preparation pipeline."""

from __future__ import annotations

from dataclasses import dataclass


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
        for name in (
            "expand_abbreviations",
            "expand_structured",
            "expand_numbers",
            "normalize_whitespace",
            "normalize_unicode",
            "context",
            "strict",
        ):
            if not isinstance(getattr(self, name), bool):
                raise TypeError(f"{name} must be a bool")


__all__ = ["PreparationConfig"]
