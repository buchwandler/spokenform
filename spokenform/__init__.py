"""Single-language written-to-spoken text normalization."""

from __future__ import annotations

try:
    from ._version import version as __version__
except (ImportError, AttributeError):  # source tree before setuptools_scm generation
    __version__ = "0+unknown"

from .abbreviations import (
    add_abbreviation,
    has_abbreviation,
    remove_abbreviation,
    reset_abbreviations,
)
from .annotations import annotations_from_spacy, spacy_annotations, validate_annotations
from .api import normalize_spacing, prepare, prepare_for_kokorog2p, prepare_language, prepare_text
from .config import (
    GenericAcronymCase,
    GenericAcronymMode,
    InterpretationMode,
    LongNumberMode,
    NumberPolicy,
    PreparationConfig,
    RecognitionDomain,
    RecognitionEvidence,
    RegisteredAcronymMode,
    SequenceFallbackMode,
    default_number_policy_for_language,
    kokorog2p_number_policy_for_language,
    number_policy_for_language,
)
from .evidence import LexicalEvidenceProvider
from .language import (
    KOKOROG2P_PROFILE_LANGUAGES,
    KOKOROG2P_PROFILE_VERSION,
    SUPPORTED_BASE_LANGUAGES,
    SUPPORTED_LANGUAGE_KEYS,
    SUPPORTED_LOCALES,
    base_language,
    canonicalize_language,
    normalize_language,
    resolve_abbr2words_language,
    resolve_numeralform_locale,
    supported_languages,
    supports_language,
    supports_profile,
)
from .language_support import (
    CONSERVATIVE_INTEGRATION_LANGUAGES,
    REVIEWED_NUMERIC_PUNCTUATION_LANGUAGES,
    REVIEWED_STRUCTURED_LANGUAGES,
    SEQUENCE_POLICY_LANGUAGES,
    SHARED_SEQUENCE_RECOGNIZER_LANGUAGES,
    LanguageSupport,
    SupportTier,
    language_has_plain_number_backend,
    language_has_reviewed_structured_numbers,
    language_support,
    supported_profile_languages,
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
from .number_words import (
    NumberBackend,
    number_backend_for_language,
    require_number_backend,
    resolve_number_backend,
)
from .numbers import normalize_numbers
from .profiles import GlossaryConflictError, GlossaryEntry, GlossaryReadAs, SpeechProfile
from .protection import ProtectedSpan, ProtectionError
from .spacy_support import SpacyModelError, load_spacy_model, reset_spacy_cache
from .structured import StageResult, iter_structured_replacements, normalize_structured

__all__ = [
    "PreparationConfig",
    "GlossaryEntry",
    "GlossaryReadAs",
    "SpeechProfile",
    "GlossaryConflictError",
    "add_abbreviation",
    "remove_abbreviation",
    "has_abbreviation",
    "reset_abbreviations",
    "LexicalEvidenceProvider",
    "InterpretationMode",
    "SequenceFallbackMode",
    "RecognitionDomain",
    "RecognitionEvidence",
    "GenericAcronymMode",
    "GenericAcronymCase",
    "LongNumberMode",
    "RegisteredAcronymMode",
    "NumberPolicy",
    "number_policy_for_language",
    "default_number_policy_for_language",
    "kokorog2p_number_policy_for_language",
    "number_backend_for_language",
    "NumberBackend",
    "require_number_backend",
    "resolve_number_backend",
    "SUPPORTED_BASE_LANGUAGES",
    "SUPPORTED_LANGUAGE_KEYS",
    "SUPPORTED_LOCALES",
    "canonicalize_language",
    "normalize_language",
    "base_language",
    "supported_languages",
    "supports_language",
    "supports_profile",
    "KOKOROG2P_PROFILE_LANGUAGES",
    "KOKOROG2P_PROFILE_VERSION",
    "resolve_numeralform_locale",
    "resolve_abbr2words_language",
    "CONSERVATIVE_INTEGRATION_LANGUAGES",
    "LanguageSupport",
    "REVIEWED_NUMERIC_PUNCTUATION_LANGUAGES",
    "REVIEWED_STRUCTURED_LANGUAGES",
    "SEQUENCE_POLICY_LANGUAGES",
    "SHARED_SEQUENCE_RECOGNIZER_LANGUAGES",
    "SupportTier",
    "language_has_plain_number_backend",
    "language_has_reviewed_structured_numbers",
    "language_support",
    "supported_profile_languages",
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
    "prepare_language",
    "prepare_for_kokorog2p",
    "prepare_text",
    "spacy_annotations",
]
