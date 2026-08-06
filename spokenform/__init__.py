"""Multilingual written-to-spoken text normalization."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("spokenform")
except PackageNotFoundError:  # source tree before installation
    __version__ = "0.1.0"

from .annotations import annotations_from_spacy, spacy_annotations
from .api import normalize_spacing, prepare, prepare_text
from .config import PreparationConfig
from .detection import LanguageDetector, lingua_detector
from .mapping import OffsetMap, Replacement
from .models import (
    LanguageSpan,
    MappedEdit,
    PreparationStage,
    PreparedText,
    SemanticSpan,
    TextEdit,
    TokenAnnotation,
)
from .numbers import normalize_numbers
from .protection import ProtectedSpan, ProtectionError
from .spacy_support import SpacyModelError, load_spacy_model, reset_spacy_cache
from .ssmd import ParsedMarkup, SSMDParseError

__all__ = [
    "LanguageDetector",
    "PreparationConfig",
    "LanguageSpan",
    "MappedEdit",
    "OffsetMap",
    "PreparedText",
    "PreparationStage",
    "SemanticSpan",
    "ProtectedSpan",
    "ProtectionError",
    "ParsedMarkup",
    "SSMDParseError",
    "SpacyModelError",
    "load_spacy_model",
    "reset_spacy_cache",
    "Replacement",
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
