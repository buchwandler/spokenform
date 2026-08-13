"""Single-language written-to-spoken text normalization."""

from __future__ import annotations

try:
    from ._version import version as __version__
except (ImportError, AttributeError):  # source tree before setuptools_scm generation
    __version__ = "0+unknown"

from .annotations import annotations_from_spacy, spacy_annotations, validate_annotations
from .api import normalize_spacing, prepare, prepare_for_kokorog2p, prepare_text
from .config import (
    GenericAcronymCase,
    GenericAcronymMode,
    LongNumberMode,
    NumberPolicy,
    PreparationConfig,
    RegisteredAcronymMode,
    number_policy_for_language,
)
from .language import (
    SUPPORTED_BASE_LANGUAGES,
    base_language,
    normalize_language,
    resolve_abbr2words_language,
    resolve_num2words_language,
    supported_languages,
)
from .mapping import (
    OffsetMap,
    Replacement,
    compose_source_replacements,
    convert_abbr_replacements,
    resolve_replacements,
)
from .models import (
    MappedEdit,
    PreparationStage,
    PreparedText,
    ReservedSpan,
    SourceReplacement,
    TextEdit,
    TokenAnnotation,
)
from .numbers import normalize_numbers
from .protection import ProtectedSpan, ProtectionError
from .spacy_support import SpacyModelError, load_spacy_model, reset_spacy_cache
from .structured import StageResult, iter_structured_replacements, normalize_structured

__all__ = [
    "PreparationConfig",
    "GenericAcronymMode",
    "GenericAcronymCase",
    "LongNumberMode",
    "RegisteredAcronymMode",
    "NumberPolicy",
    "number_policy_for_language",
    "SUPPORTED_BASE_LANGUAGES",
    "normalize_language",
    "base_language",
    "supported_languages",
    "resolve_num2words_language",
    "resolve_abbr2words_language",
    "MappedEdit",
    "OffsetMap",
    "PreparedText",
    "PreparationStage",
    "ReservedSpan",
    "ProtectedSpan",
    "ProtectionError",
    "SpacyModelError",
    "load_spacy_model",
    "reset_spacy_cache",
    "Replacement",
    "SourceReplacement",
    "compose_source_replacements",
    "convert_abbr_replacements",
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
    "prepare_for_kokorog2p",
    "prepare_text",
    "spacy_annotations",
]
