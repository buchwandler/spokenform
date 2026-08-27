"""Configuration for the spokenform preparation pipeline."""

from __future__ import annotations

from collections.abc import Iterable
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


class InterpretationMode(str, Enum):
    """Amount of contextual evidence allowed during recognition."""

    SURFACE = "surface"
    CONTEXTUAL = "contextual"


class SequenceFallbackMode(str, Enum):
    """Action for residual sequence-shaped spans without semantic ownership."""

    PRESERVE = "preserve"
    SPELL = "spell"


class RecognitionEvidence(str, Enum):
    """Evidence basis used to produce a structured candidate."""

    INTRINSIC = "intrinsic"
    CONTEXTUAL = "contextual"


class RecognitionDomain(str, Enum):
    """Semantic ownership family for a structured recognizer."""

    TEMPORAL = "temporal"
    QUANTITIES = "quantities"
    FINANCE = "finance"
    COMMUNICATIONS = "communications"
    NETWORK = "network"
    IDENTIFIERS = "identifiers"
    ADDRESSES = "addresses"
    REFERENCES = "references"
    LEGAL = "legal"
    SPORTS = "sports"
    MATH = "math"
    MUSIC = "music"
    BIOLOGY = "biology"
    CHEMISTRY = "chemistry"
    SOCIAL = "social"
    GEOGRAPHY = "geography"
    CORE = "core"


SymbolMode = Literal["none", "remove", "keep"]
GenericAcronymMode = Literal["known_only", "conservative_unknown", "spell_unknown"]
GenericAcronymCase = Literal["upper", "lower"]
LongNumberMode = Literal["preserve", "contextual", "cardinal"]
RegisteredAcronymMode = Literal["expand", "spell"]


def number_policy_for_language(language: str) -> NumberPolicy:
    """Return the initial kokorog2p policy for a normalized language code."""
    base = base_language(language)
    if base in {"cs", "de", "en", "es", "fr", "it", "ja", "ko", "pt", "sv", "vi", "zh"}:
        return NumberPolicy.STRUCTURED_AND_PLAIN
    return NumberPolicy.NONE


def _normalized_config_language(value: object) -> str:
    if not isinstance(value, str):
        raise TypeError("language must be a string")
    if not value.strip():
        raise ValueError("language must not be empty")
    return normalize_language(value)


def _coerce_interpretation_mode(value: object) -> InterpretationMode:
    if isinstance(value, InterpretationMode):
        return value
    try:
        return InterpretationMode(value)
    except (TypeError, ValueError) as error:
        raise ValueError("interpretation_mode must be 'surface' or 'contextual'") from error


def _coerce_sequence_fallback_mode(value: object) -> SequenceFallbackMode:
    if isinstance(value, SequenceFallbackMode):
        return value
    try:
        return SequenceFallbackMode(value)
    except (TypeError, ValueError) as error:
        raise ValueError("sequence_fallback_mode must be 'preserve' or 'spell'") from error


def _normalize_recognition_domains(
    values: Iterable[RecognitionDomain | str],
    *,
    field: str,
) -> frozenset[RecognitionDomain]:
    try:
        return frozenset(
            domain if isinstance(domain, RecognitionDomain) else RecognitionDomain(domain)
            for domain in values
        )
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} contains an unknown recognition domain") from error


def _normalize_domain_policy(
    disabled_domains: Iterable[RecognitionDomain | str],
    allowed_domains: Iterable[RecognitionDomain | str] | None,
) -> tuple[frozenset[RecognitionDomain], frozenset[RecognitionDomain] | None]:
    disabled = _normalize_recognition_domains(disabled_domains, field="disabled_domains")
    if allowed_domains is None:
        return disabled, None
    allowed = _normalize_recognition_domains(allowed_domains, field="allowed_domains")
    overlap = allowed & disabled
    if overlap:
        names = ", ".join(sorted(domain.value for domain in overlap))
        raise ValueError(f"allowed_domains and disabled_domains overlap: {names}")
    return disabled, allowed


def _validate_spacy_config(config: PreparationConfig) -> None:
    if config.use_spacy is not None and not isinstance(config.use_spacy, bool):
        raise TypeError("use_spacy must be a bool or None")
    if config.spacy_model is not None:
        if not isinstance(config.spacy_model, str):
            raise TypeError("spacy_model must be a string or None")
        if not config.spacy_model.strip():
            raise ValueError("spacy_model must not be empty")


def _validate_number_policy(config: PreparationConfig) -> None:
    if config.number_policy is not None and not isinstance(config.number_policy, NumberPolicy):
        raise TypeError("number_policy must be a NumberPolicy or None")


def _validate_symbol_config(config: PreparationConfig) -> None:
    if config.symbol_mode not in {"none", "remove", "keep"}:
        raise ValueError("symbol_mode must be 'none', 'remove', or 'keep'")
    if not isinstance(config.keep_symbols, str):
        raise TypeError("keep_symbols must be a string")
    if config.symbol_mode != "keep" and config.keep_symbols:
        raise ValueError("keep_symbols is only valid when symbol_mode='keep'")
    if config.symbol_mode == "keep" and not config.keep_symbols:
        raise ValueError(
            "keep_symbols must not be empty when symbol_mode='keep'; use symbol_mode='remove' to remove all symbols"
        )


def _validate_mode_choices(config: PreparationConfig) -> None:
    if config.generic_acronym_case not in {"upper", "lower"}:
        raise ValueError("generic_acronym_case must be 'upper' or 'lower'")
    if config.generic_acronym_mode not in {"known_only", "conservative_unknown", "spell_unknown"}:
        raise ValueError(
            "generic_acronym_mode must be 'known_only', 'conservative_unknown', or 'spell_unknown'"
        )
    if config.long_number_mode not in {"preserve", "contextual", "cardinal"}:
        raise ValueError("long_number_mode must be 'preserve', 'contextual', or 'cardinal'")
    if config.registered_acronym_mode not in {"expand", "spell"}:
        raise ValueError("registered_acronym_mode must be 'expand' or 'spell'")


_BOOLEAN_CONFIG_FIELDS = (
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
)


def _validate_boolean_options(config: PreparationConfig) -> None:
    for name in _BOOLEAN_CONFIG_FIELDS:
        if not isinstance(getattr(config, name), bool):
            raise TypeError(f"{name} must be a bool")


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
    generic_acronym_mode: GenericAcronymMode = "known_only"
    generic_acronym_case: GenericAcronymCase = "upper"
    long_number_mode: LongNumberMode = "preserve"
    registered_acronym_mode: RegisteredAcronymMode = "expand"
    interpretation_mode: InterpretationMode = InterpretationMode.CONTEXTUAL
    sequence_fallback_mode: SequenceFallbackMode = SequenceFallbackMode.PRESERVE
    disabled_domains: Iterable[RecognitionDomain | str] = frozenset()
    allowed_domains: Iterable[RecognitionDomain | str] | None = None
    context: bool = True
    strict: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "language", _normalized_config_language(self.language))
        object.__setattr__(
            self, "interpretation_mode", _coerce_interpretation_mode(self.interpretation_mode)
        )
        object.__setattr__(
            self,
            "sequence_fallback_mode",
            _coerce_sequence_fallback_mode(self.sequence_fallback_mode),
        )
        disabled, allowed = _normalize_domain_policy(self.disabled_domains, self.allowed_domains)
        object.__setattr__(self, "disabled_domains", disabled)
        object.__setattr__(self, "allowed_domains", allowed)
        _validate_spacy_config(self)
        _validate_number_policy(self)
        _validate_symbol_config(self)
        _validate_mode_choices(self)
        _validate_boolean_options(self)

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
    "SequenceFallbackMode",
    "InterpretationMode",
    "RecognitionDomain",
    "RecognitionEvidence",
    "GenericAcronymMode",
    "GenericAcronymCase",
    "NumberPolicy",
    "LongNumberMode",
    "RegisteredAcronymMode",
    "PreparationConfig",
    "SymbolMode",
    "number_policy_for_language",
]
