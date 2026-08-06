"""Single-language written-to-spoken text normalization."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("spokenform")
except PackageNotFoundError:  # source tree before installation
    __version__ = "0.1.0"

from .annotations import annotations_from_spacy, spacy_annotations, validate_annotations
from .api import normalize_spacing, prepare, prepare_text
from .config import PreparationConfig
from .mapping import OffsetMap, Replacement, resolve_replacements
from .models import (
    MappedEdit,
    PreparationStage,
    PreparedText,
    TextEdit,
    TokenAnnotation,
)
from .numbers import normalize_numbers
from .protection import ProtectedSpan, ProtectionError
from .spacy_support import SpacyModelError, load_spacy_model, reset_spacy_cache
from .structured import StageResult, iter_structured_replacements, normalize_structured

__all__ = [
    "PreparationConfig",
    "MappedEdit",
    "OffsetMap",
    "PreparedText",
    "PreparationStage",
    "ProtectedSpan",
    "ProtectionError",
    "SpacyModelError",
    "load_spacy_model",
    "reset_spacy_cache",
    "Replacement",
    "resolve_replacements",
    "StageResult",
    "TextEdit",
    "TokenAnnotation",
    "__version__",
    "annotations_from_spacy",
    "validate_annotations",
    "normalize_numbers",
    "iter_structured_replacements",
    "normalize_structured",
    "normalize_spacing",
    "prepare",
    "prepare_text",
    "spacy_annotations",
]
