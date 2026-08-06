"""Multilingual written-to-spoken text normalization."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("spokenform")
except PackageNotFoundError:  # source tree before installation
    __version__ = "0.1.0"

from abbr2words import TokenAnnotation

from .annotations import annotations_from_spacy, spacy_annotations
from .api import normalize_spacing, prepare, prepare_text
from .detection import LanguageDetector, lingua_detector
from .models import LanguageSpan, PreparedText, PreparationStage, TextEdit
from .numbers import normalize_numbers

__all__ = [
    "LanguageDetector",
    "LanguageSpan",
    "PreparedText",
    "PreparationStage",
    "TextEdit",
    "TokenAnnotation",
    "__version__",
    "annotations_from_spacy",
    "lingua_detector",
    "normalize_numbers",
    "normalize_spacing",
    "prepare",
    "prepare_text",
    "spacy_annotations",
]
