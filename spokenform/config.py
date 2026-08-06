"""Configuration for the spokenform preparation pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

MarkupMode = Literal["plain", "ssmd", "auto"]


@dataclass(frozen=True, slots=True)
class PreparationConfig:
    """Immutable options controlling written-to-spoken preparation."""

    language: str | None = "en"
    detect_language: bool = False
    allowed_languages: tuple[str, ...] = ()
    markup: MarkupMode = "plain"
    render_language_marks: bool = False
    use_spacy: bool | None = None
    spacy_model: str | None = None
    expand_abbreviations: bool = True
    expand_numbers: bool = True
    normalize_whitespace: bool = True
    normalize_unicode: bool = True
    context: bool = True
    strict: bool = False

    def __post_init__(self) -> None:
        if self.markup not in {"plain", "ssmd", "auto"}:
            raise ValueError("markup must be 'plain', 'ssmd', or 'auto'")
        if self.language is not None and not isinstance(self.language, str):
            raise TypeError("language must be a string or None")
        if self.spacy_model is not None and not isinstance(self.spacy_model, str):
            raise TypeError("spacy_model must be a string or None")


__all__ = ["MarkupMode", "PreparationConfig"]
