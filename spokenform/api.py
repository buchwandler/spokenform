"""Public preparation pipeline."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass, replace
from typing import Any, cast

from abbr2words import (
    InitialismCase,
    InitialismMode,
    RegisteredInitialismMode,
    abbr2words_with_replacements,
    iter_unit_matches,
)

from .annotations import (
    _SpacyPipeline,
    remap_annotations_for_replacements,
    to_abbr2words_annotations,
    validate_annotations,
)
from .config import (
    GenericAcronymCase,
    GenericAcronymMode,
    InterpretationMode,
    LongNumberMode,
    NumberPolicy,
    PreparationConfig,
    RecognitionDomain,
    RegisteredAcronymMode,
    SequenceFallbackMode,
    SymbolMode,
)
from .evidence import EvidenceSession, LexicalEvidenceProvider, validate_provider
from .fallback import iter_sequence_fallback_replacements
from .language import base_language, normalize_language, resolve_abbr2words_language
from .mapping import (
    OffsetMap,
    Replacement,
    apply_replacements,
    compose_source_replacements,
    convert_abbr_replacements,
    replacements_from_diff,
)
from .models import PreparationStage, PreparedText, ReservedSpan, SourceReplacement, TokenAnnotation
from .numbers import normalize_plain_numbers
from .numeric_lexeme import normalize_numeric_compatibility
from .profiles import (
    SpeechProfile,
    get_compiled_profile_expander,
    profile_requires_registered_spelling,
)
from .protection import (
    ProtectedSpan,
    ProtectedText,
    coerce_protected_spans,
    discover_protected_spans,
    protect_text,
)
from .spacy_support import SpacyModelError, load_spacy_model
from .stages import (
    apply_replacement_stage,
    apply_stage,
    map_internal_protected_spans_to_visible,
    map_visible_replacements_to_internal,
)
from .structured import normalize_structured

_HORIZONTAL_SPACE_RE = re.compile(r"[\t\u00a0\u202f ]+")
_EXCESS_LINES_RE = re.compile(r"\n{3,}")
_SOFT_VERSION_RE = re.compile(
    r"(?<![\w.])(?:v\d+(?:\.\d+){1,}|\d+(?:\.\d+){2,})(?![\w.])",
    re.IGNORECASE,
)


def normalize_spacing(
    text: str,
    *,
    normalize_unicode: bool = True,
    strip_outer_whitespace: bool = True,
    collapse_horizontal_whitespace: bool = True,
    normalize_line_whitespace: bool = True,
    collapse_blank_lines: bool = True,
    number_policy: NumberPolicy | None = None,
) -> str:
    """Apply independently configurable Unicode and whitespace policies.

    ``number_policy`` remains accepted for 0.2.x compatibility. Numeric policy
    selection belongs to :func:`prepare`; spacing itself does not consume it.
    """
    normalized = unicodedata.normalize("NFC", text) if normalize_unicode else text
    if collapse_horizontal_whitespace:
        normalized = _HORIZONTAL_SPACE_RE.sub(" ", normalized)
    if normalize_line_whitespace:
        normalized = re.sub(r"[\t\u00a0\u202f ]*\n[\t\u00a0\u202f ]*", "\n", normalized)
    if collapse_blank_lines:
        normalized = _EXCESS_LINES_RE.sub("\n\n", normalized)
    if strip_outer_whitespace:
        normalized = normalized.strip()
    return normalized


def _run_unicode_stage(
    current: str,
    current_annotations: Iterable[TokenAnnotation] | None,
    stages: list[PreparationStage],
    protected: ProtectedText,
    selected: PreparationConfig,
) -> tuple[str, Iterable[TokenAnnotation] | None]:
    if selected.normalize_unicode:
        before = current
        normalized = unicodedata.normalize("NFC", current)
        if normalized != current:
            current = apply_stage(
                stages,
                "unicode",
                current,
                lambda value: unicodedata.normalize("NFC", value),
                restore=protected.restore,
            )
            unicode_stage = stages[-1]
            unicode_replacements = replacements_from_diff(
                unicode_stage.before,
                unicode_stage.after,
                unicode_stage.name,
            )
            internal_replacements = map_visible_replacements_to_internal(
                before,
                unicode_replacements,
                protected.values,
                protected.placeholders,
            )
            current_annotations = remap_annotations_for_replacements(
                current_annotations,
                ((item.start, item.end, len(item.text)) for item in internal_replacements),
            )
    return current, current_annotations


def _run_numeric_compatibility_stage(
    current: str,
    current_annotations: Iterable[TokenAnnotation] | None,
    stages: list[PreparationStage],
    protected: ProtectedText,
) -> tuple[str, Iterable[TokenAnnotation] | None]:
    """Normalize full-width characters only within numeric-looking spans."""
    if not any(character in current for character in "０１２３４５６７８９．，＋－"):
        return current, current_annotations
    before = current
    current = apply_stage(
        stages,
        "numeric-compatibility",
        current,
        normalize_numeric_compatibility,
        restore=protected.restore,
    )
    if current != before:
        edits = replacements_from_diff(before, current, "numeric-compatibility")
        internal_edits = map_visible_replacements_to_internal(
            before, edits, protected.values, protected.placeholders
        )
        current_annotations = remap_annotations_for_replacements(
            current_annotations,
            ((item.start, item.end, len(item.text)) for item in internal_edits),
        )
    return current, current_annotations


def _run_structured_stage(
    current: str,
    current_annotations: Iterable[TokenAnnotation] | None,
    reserved_spans: tuple[ReservedSpan, ...],
    stages: list[PreparationStage],
    protected: ProtectedText,
    selected: PreparationConfig,
    language_code: str,
    evidence: EvidenceSession,
    structured_numbers_enabled: bool,
) -> tuple[str, Iterable[TokenAnnotation] | None, tuple[ReservedSpan, ...]]:
    if structured_numbers_enabled:
        structured = normalize_structured(
            protected.restore(current),
            language=language_code,
            protected_ranges=map_internal_protected_spans_to_visible(
                current,
                protected.values,
                protected.placeholders,
            ),
            promote_literals=selected.normalize_literals,
            generic_acronym_mode=selected.generic_acronym_mode,
            generic_acronym_case=selected.generic_acronym_case,
            interpretation_mode=selected.interpretation_mode,
            disabled_domains=cast(frozenset[RecognitionDomain], selected.disabled_domains),
            allowed_domains=cast(frozenset[RecognitionDomain] | None, selected.allowed_domains),
            evidence=evidence,
        )
        if structured.replacements or structured.reserved:
            internal_replacements = map_visible_replacements_to_internal(
                current,
                structured.replacements,
                protected.values,
                protected.placeholders,
            )
            current = apply_replacement_stage(
                stages,
                "structured",
                current,
                structured.replacements,
                protected_values=protected.values,
                protected_placeholders=protected.placeholders,
                language=language_code,
                reserved=structured.reserved,
            )
            reserved_spans = structured.reserved
            current_annotations = remap_annotations_for_replacements(
                current_annotations,
                ((item.start, item.end, len(item.text)) for item in internal_replacements),
            )
    return current, current_annotations, reserved_spans


@dataclass(frozen=True, slots=True)
class _AbbreviationPolicy:
    context: bool
    initialism_mode: InitialismMode
    initialism_case: InitialismCase
    registered_initialism_mode: RegisteredInitialismMode


def _resolve_abbreviation_policy(
    selected: PreparationConfig,
    profile: SpeechProfile | None,
) -> _AbbreviationPolicy:
    initialism_mode: InitialismMode = "dotted_only"
    initialism_case: InitialismCase = "source"
    if selected.generic_acronym_mode == "conservative_unknown":
        initialism_mode = "conservative_undotted"
    elif selected.generic_acronym_mode == "spell_unknown":
        initialism_mode = "spell_undotted"
    if selected.generic_acronym_mode != "known_only" or selected.generic_acronym_case != "upper":
        initialism_case = selected.generic_acronym_case
    registered_mode: RegisteredInitialismMode = selected.registered_acronym_mode
    if profile is not None and profile_requires_registered_spelling(profile):
        registered_mode = "spell"
    return _AbbreviationPolicy(
        context=selected.context and selected.interpretation_mode is InterpretationMode.CONTEXTUAL,
        initialism_mode=initialism_mode,
        initialism_case=initialism_case,
        registered_initialism_mode=registered_mode,
    )


def _run_abbreviation_stage(
    current: str,
    current_annotations: Iterable[TokenAnnotation] | None,
    reserved_spans: tuple[ReservedSpan, ...],
    stages: list[PreparationStage],
    protected: ProtectedText,
    selected: PreparationConfig,
    language_code: str,
    profile: SpeechProfile | None,
) -> tuple[str, Iterable[TokenAnnotation] | None, tuple[ReservedSpan, ...]]:
    if selected.expand_abbreviations:
        protected_value_by_placeholder = dict(
            zip(protected.placeholders, protected.values, strict=True)
        )
        visible_annotations = remap_annotations_for_replacements(
            current_annotations,
            (
                (index, index + 1, len(value))
                for index, character in enumerate(current)
                if character in protected_value_by_placeholder
                for value in (protected_value_by_placeholder[character],)
            ),
        )
        abbreviation_protected_spans = map_internal_protected_spans_to_visible(
            current,
            protected.values,
            protected.placeholders,
        ) + tuple((item.start, item.end) for item in reserved_spans)
        abbreviation_language = resolve_abbr2words_language(language_code)
        policy = _resolve_abbreviation_policy(selected, profile)
        abbreviation_annotations = to_abbr2words_annotations(visible_annotations)
        if profile is None:
            abbreviation_result = abbr2words_with_replacements(
                protected.restore(current),
                lang=abbreviation_language,
                context=policy.context,
                initialism_mode=policy.initialism_mode,
                initialism_case=policy.initialism_case,
                registered_initialism_mode=policy.registered_initialism_mode,
                annotations=abbreviation_annotations,
                protected_spans=abbreviation_protected_spans,
            )
        else:
            expander = get_compiled_profile_expander(
                profile,
                abbreviation_language,
                policy.context,
                policy.initialism_mode,
                policy.initialism_case,
                policy.registered_initialism_mode,
            )
            abbreviation_result = expander.expand_with_replacements(
                protected.restore(current),
                annotations=abbreviation_annotations,
                protected_spans=abbreviation_protected_spans,
            )
        abbreviation_replacements = convert_abbr_replacements(
            abbreviation_result.replacements,
            language=language_code,
        )
        before = current
        current = apply_replacement_stage(
            stages,
            "abbreviations",
            current,
            abbreviation_replacements,
            protected_values=protected.values,
            protected_placeholders=protected.placeholders,
            language=language_code,
            reserved=reserved_spans,
        )
        _, _, abbreviation_map = apply_replacements(
            protected.restore(before), abbreviation_replacements, stage="abbreviations"
        )
        reserved_spans = _remap_reserved_spans(reserved_spans, abbreviation_map)
        stages[-1] = replace(stages[-1], reserved=reserved_spans)
        internal_replacements = map_visible_replacements_to_internal(
            before,
            abbreviation_replacements,
            protected.values,
            protected.placeholders,
        )
        current_annotations = remap_annotations_for_replacements(
            current_annotations,
            ((item.start, item.end, len(item.text)) for item in internal_replacements),
        )
    return current, current_annotations, reserved_spans


def _run_number_stage(
    current: str,
    current_annotations: Iterable[TokenAnnotation] | None,
    reserved_spans: tuple[ReservedSpan, ...],
    stages: list[PreparationStage],
    protected: ProtectedText,
    selected: PreparationConfig,
    language_code: str,
    effective_long_number_mode: LongNumberMode,
    plain_numbers_enabled: bool,
) -> tuple[str, Iterable[TokenAnnotation] | None, tuple[ReservedSpan, ...]]:
    if plain_numbers_enabled:
        before = current
        internal_reserved_ranges = _reserved_ranges_in_internal(
            before,
            reserved_spans,
            protected.values,
            protected.placeholders,
        )
        current = apply_stage(
            stages,
            "numbers",
            current,
            lambda value: normalize_plain_numbers(
                value,
                language=language_code,
                protected_ranges=internal_reserved_ranges,
                long_number_mode=effective_long_number_mode,
            ),
            restore=protected.restore,
        )
        number_stage = stages[-1]
        number_replacements = replacements_from_diff(
            number_stage.before,
            number_stage.after,
            number_stage.name,
        )
        internal_replacements = map_visible_replacements_to_internal(
            before,
            number_replacements,
            protected.values,
            protected.placeholders,
        )
        current_annotations = remap_annotations_for_replacements(
            current_annotations,
            ((item.start, item.end, len(item.text)) for item in internal_replacements),
        )
        number_map = OffsetMap.from_replacements(
            len(number_stage.before), number_replacements, output_length=len(number_stage.after)
        )
        reserved_spans = _remap_reserved_spans(reserved_spans, number_map)
        stages[-1] = replace(stages[-1], reserved=reserved_spans)
    return current, current_annotations, reserved_spans


def _run_sequence_fallback_stage(
    current: str,
    current_annotations: Iterable[TokenAnnotation] | None,
    reserved_spans: tuple[ReservedSpan, ...],
    stages: list[PreparationStage],
    protected: ProtectedText,
    language_code: str,
    selected: PreparationConfig,
) -> tuple[str, Iterable[TokenAnnotation] | None, tuple[ReservedSpan, ...]]:
    if selected.sequence_fallback_mode is SequenceFallbackMode.SPELL:
        before = current
        visible_before = protected.restore(current)
        protected_ranges = map_internal_protected_spans_to_visible(
            current,
            protected.values,
            protected.placeholders,
        ) + tuple(
            (item.start, item.end)
            for item in reserved_spans
            if item.owner == "structured-generated"
        )
        fallback_replacements = iter_sequence_fallback_replacements(
            visible_before,
            language=language_code,
            protected_ranges=protected_ranges,
        )
        if fallback_replacements:
            current = apply_replacement_stage(
                stages,
                "sequence_fallback",
                current,
                fallback_replacements,
                protected_values=protected.values,
                protected_placeholders=protected.placeholders,
                language=language_code,
                reserved=reserved_spans,
            )
            fallback_stage = stages[-1]
            internal_replacements = map_visible_replacements_to_internal(
                before,
                fallback_replacements,
                protected.values,
                protected.placeholders,
            )
            current_annotations = remap_annotations_for_replacements(
                current_annotations,
                ((item.start, item.end, len(item.text)) for item in internal_replacements),
            )
            fallback_map = OffsetMap.from_replacements(
                len(fallback_stage.before),
                fallback_replacements,
                output_length=len(fallback_stage.after),
            )
            reserved_spans = _remap_reserved_spans(reserved_spans, fallback_map)
            stages[-1] = replace(stages[-1], reserved=reserved_spans)
    return current, current_annotations, reserved_spans


def _run_symbol_stage(
    current: str,
    current_annotations: Iterable[TokenAnnotation] | None,
    reserved_spans: tuple[ReservedSpan, ...],
    stages: list[PreparationStage],
    protected: ProtectedText,
    language_code: str,
    selected: PreparationConfig,
) -> tuple[str, Iterable[TokenAnnotation] | None, tuple[ReservedSpan, ...]]:
    if selected.symbol_mode != "none":
        before = current
        visible_before = protected.restore(current)
        symbol_replacements = _iter_symbol_replacements(
            visible_before,
            mode=selected.symbol_mode,
            keep_symbols=selected.keep_symbols,
            language=language_code,
            protected_ranges=(
                map_internal_protected_spans_to_visible(
                    current,
                    protected.values,
                    protected.placeholders,
                )
                + tuple((item.start, item.end) for item in reserved_spans)
            ),
        )
        current = apply_replacement_stage(
            stages,
            "symbols",
            current,
            symbol_replacements,
            protected_values=protected.values,
            protected_placeholders=protected.placeholders,
            language=language_code,
            reserved=reserved_spans,
        )
        symbol_stage = stages[-1]
        internal_replacements = map_visible_replacements_to_internal(
            before,
            symbol_replacements,
            protected.values,
            protected.placeholders,
        )
        current_annotations = remap_annotations_for_replacements(
            current_annotations,
            ((item.start, item.end, len(item.text)) for item in internal_replacements),
        )
        symbol_map = OffsetMap.from_replacements(
            len(symbol_stage.before),
            symbol_replacements,
            output_length=len(symbol_stage.after),
        )
        reserved_spans = _remap_reserved_spans(reserved_spans, symbol_map)
        stages[-1] = replace(stages[-1], reserved=reserved_spans)
    return current, current_annotations, reserved_spans


def _run_whitespace_stage(
    current: str,
    current_annotations: Iterable[TokenAnnotation] | None,
    reserved_spans: tuple[ReservedSpan, ...],
    stages: list[PreparationStage],
    protected: ProtectedText,
    language_code: str,
    selected: PreparationConfig,
) -> tuple[str, Iterable[TokenAnnotation] | None, tuple[ReservedSpan, ...]]:
    if selected.normalize_whitespace:
        before = current
        current = apply_stage(
            stages,
            "whitespace",
            current,
            lambda value: normalize_spacing(
                value,
                normalize_unicode=False,
                strip_outer_whitespace=(
                    selected.strip_outer_whitespace and not selected.preserve_run_boundaries
                ),
                collapse_horizontal_whitespace=(
                    selected.collapse_horizontal_whitespace and not selected.preserve_run_boundaries
                ),
                normalize_line_whitespace=(
                    selected.normalize_line_whitespace and not selected.preserve_run_boundaries
                ),
                collapse_blank_lines=(
                    selected.collapse_blank_lines and not selected.preserve_run_boundaries
                ),
            ),
            restore=protected.restore,
        )
        whitespace_stage = stages[-1]
        whitespace_replacements = replacements_from_diff(
            whitespace_stage.before,
            whitespace_stage.after,
            whitespace_stage.name,
        )
        internal_replacements = map_visible_replacements_to_internal(
            before,
            whitespace_replacements,
            protected.values,
            protected.placeholders,
        )
        current_annotations = remap_annotations_for_replacements(
            current_annotations,
            ((item.start, item.end, len(item.text)) for item in internal_replacements),
        )
        whitespace_map = OffsetMap.from_replacements(
            len(whitespace_stage.before),
            whitespace_replacements,
            output_length=len(whitespace_stage.after),
        )
        reserved_spans = _remap_reserved_spans(reserved_spans, whitespace_map)
        stages[-1] = replace(stages[-1], reserved=reserved_spans)
    return current, current_annotations, reserved_spans


def prepare(
    text: str,
    *,
    language: str = "en",
    config: PreparationConfig | None = None,
    profile: SpeechProfile | None = None,
    annotations: Iterable[TokenAnnotation] | None = None,
    nlp: object | None = None,
    protected_spans: Iterable[ProtectedSpan | tuple[int, int]] | None = None,
    lexical_evidence: LexicalEvidenceProvider | None = None,
    use_spacy: bool | None = None,
    spacy_model: str | None = None,
    expand_abbreviations: bool = True,
    expand_structured: bool = True,
    normalize_literals: bool = False,
    expand_numbers: bool = True,
    normalize_whitespace: bool = True,
    normalize_unicode: bool = True,
    strip_outer_whitespace: bool = True,
    collapse_horizontal_whitespace: bool = True,
    normalize_line_whitespace: bool = True,
    collapse_blank_lines: bool = True,
    number_policy: NumberPolicy | None = None,
    preserve_run_boundaries: bool = False,
    model_punctuation: bool = False,
    symbol_mode: SymbolMode = "none",
    keep_symbols: str = "",
    generic_acronym_mode: GenericAcronymMode = "known_only",
    generic_acronym_case: GenericAcronymCase = "upper",
    long_number_mode: LongNumberMode = "preserve",
    registered_acronym_mode: RegisteredAcronymMode = "expand",
    context: bool = True,
    interpretation_mode: InterpretationMode = InterpretationMode.CONTEXTUAL,
    disabled_domains: Iterable[RecognitionDomain | str] = frozenset(),
    allowed_domains: Iterable[RecognitionDomain | str] | None = None,
    sequence_fallback_mode: SequenceFallbackMode = SequenceFallbackMode.PRESERVE,
    strict: bool = False,
) -> PreparedText:
    """Convert one-language written text into a readable form intended for speech.

    The caller selects the processing language. Language detection, mixed-language
    segmentation, and markup parsing belong outside spokenform.

    Structured values run before lexical abbreviation expansion and generic
    numbers so each complete expression receives one semantic replacement.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if profile is not None and not isinstance(profile, SpeechProfile):
        raise TypeError("profile must be a SpeechProfile or None")

    selected = config or PreparationConfig(
        language=language,
        use_spacy=use_spacy,
        spacy_model=spacy_model,
        expand_abbreviations=expand_abbreviations,
        expand_structured=expand_structured,
        normalize_literals=normalize_literals,
        expand_numbers=expand_numbers,
        normalize_whitespace=normalize_whitespace,
        normalize_unicode=normalize_unicode,
        strip_outer_whitespace=strip_outer_whitespace,
        collapse_horizontal_whitespace=collapse_horizontal_whitespace,
        normalize_line_whitespace=normalize_line_whitespace,
        collapse_blank_lines=collapse_blank_lines,
        number_policy=number_policy,
        preserve_run_boundaries=preserve_run_boundaries,
        model_punctuation=model_punctuation,
        symbol_mode=symbol_mode,
        keep_symbols=keep_symbols,
        generic_acronym_mode=generic_acronym_mode,
        generic_acronym_case=generic_acronym_case,
        long_number_mode=long_number_mode,
        registered_acronym_mode=registered_acronym_mode,
        interpretation_mode=interpretation_mode,
        disabled_domains=frozenset(disabled_domains),
        allowed_domains=(frozenset(allowed_domains) if allowed_domains is not None else None),
        sequence_fallback_mode=sequence_fallback_mode,
        context=context,
        strict=strict,
    )

    if profile is not None and normalize_language(profile.language) != normalize_language(
        selected.language
    ):
        raise ValueError(
            "profile language does not match selected preparation language: "
            f"{profile.language!r} != {selected.language!r}"
        )
    clean_text = text
    language_code = selected.language
    validate_provider(lexical_evidence, language_code)
    evidence = EvidenceSession(lexical_evidence)
    structured_numbers_enabled, plain_numbers_enabled, policy_warnings = _resolve_number_options(
        language_code,
        expand_structured=selected.expand_structured,
        expand_numbers=selected.expand_numbers,
        number_policy=selected.number_policy,
        model_punctuation=selected.model_punctuation,
    )
    effective_long_number_mode = selected.long_number_mode
    if (
        selected.interpretation_mode is InterpretationMode.SURFACE
        and selected.long_number_mode == "contextual"
    ):
        effective_long_number_mode = "preserve"
        policy_warnings = (
            *policy_warnings,
            "[POLICY] surface mode treats contextual long numbers as preserve",
        )

    protected, merged_protected, protection_warnings = _prepare_protected_text(
        clean_text,
        language=selected.language,
        protected_spans=protected_spans,
        protect_literals=not selected.normalize_literals,
        strict=selected.strict,
    )
    current_annotations, spacy_warnings = _prepare_annotations(
        clean_text,
        protected,
        annotations=annotations,
        nlp=nlp,
        use_spacy=selected.use_spacy,
        spacy_model=selected.spacy_model,
        language_code=language_code,
        interpretation_mode=selected.interpretation_mode,
        strict=selected.strict,
    )

    stages: list[PreparationStage] = []
    current = protected.text
    reserved_spans: tuple[ReservedSpan, ...] = ()

    current, current_annotations = _run_unicode_stage(
        current, current_annotations, stages, protected, selected
    )
    current, current_annotations = _run_numeric_compatibility_stage(
        current, current_annotations, stages, protected
    )
    current, current_annotations, reserved_spans = _run_structured_stage(
        current,
        current_annotations,
        reserved_spans,
        stages,
        protected,
        selected,
        language_code,
        evidence,
        structured_numbers_enabled,
    )
    current, current_annotations, reserved_spans = _run_abbreviation_stage(
        current,
        current_annotations,
        reserved_spans,
        stages,
        protected,
        selected,
        language_code,
        profile,
    )
    current, current_annotations, reserved_spans = _run_number_stage(
        current,
        current_annotations,
        reserved_spans,
        stages,
        protected,
        selected,
        language_code,
        effective_long_number_mode,
        plain_numbers_enabled,
    )
    current, current_annotations, reserved_spans = _run_sequence_fallback_stage(
        current, current_annotations, reserved_spans, stages, protected, language_code, selected
    )
    current, current_annotations, reserved_spans = _run_symbol_stage(
        current, current_annotations, reserved_spans, stages, protected, language_code, selected
    )
    current, current_annotations, reserved_spans = _run_whitespace_stage(
        current, current_annotations, reserved_spans, stages, protected, language_code, selected
    )
    current = protected.restore(current)

    offset_map, source_replacements = _finalize_mapping(
        clean_text,
        current,
        tuple(stages),
    )
    return _build_prepared_text(
        source_text=text,
        clean_text=clean_text,
        spoken_text=current,
        language=language_code,
        stages=tuple(stages),
        protected_spans=tuple(merged_protected),
        offset_map=offset_map,
        source_replacements=source_replacements,
        reserved_spans=reserved_spans,
        warnings=(*protection_warnings, *spacy_warnings, *policy_warnings),
    )


def prepare_language(
    text: str,
    *,
    language: str,
    **kwargs: object,
) -> PreparedText:
    """Prepare one explicitly selected language run with generic policy.

    Unlike :func:`prepare`, this future-facing entry point intentionally has no
    compatibility default for ``language``. The optional ``config`` must use the
    same language so the call cannot silently process a different language.
    """
    normalized_language = normalize_language(language)
    config = kwargs.get("config")
    if config is not None:
        if not isinstance(config, PreparationConfig):
            raise TypeError("config must be a PreparationConfig or None")
        if config.language != normalized_language:
            raise ValueError(
                "config language does not match selected preparation language: "
                f"{config.language!r} != {normalized_language!r}"
            )
    return prepare(
        text,
        language=normalized_language,
        **cast(dict[str, Any], kwargs),
    )


prepare_text = prepare


def prepare_for_kokorog2p(
    text: str,
    language: str = "en",
    *,
    config: PreparationConfig | None = None,
    profile: SpeechProfile | None = None,
    **kwargs: object,
) -> PreparedText:
    """Prepare one language with the kokorog2p-safe profile."""
    selected = config or PreparationConfig.for_kokorog2p(language)
    return prepare(text, config=selected, profile=profile, **kwargs)  # type: ignore[arg-type]


__all__ = [
    "prepare",
    "prepare_language",
    "prepare_text",
    "prepare_for_kokorog2p",
    "normalize_spacing",
]


def _remap_reserved_spans(
    spans: tuple[ReservedSpan, ...],
    mapping: OffsetMap,
) -> tuple[ReservedSpan, ...]:
    """Carry generated ownership through one visible stage edit map."""
    remapped: list[ReservedSpan] = []
    for span in spans:
        start, end = mapping.map_source_span(span.start, span.end)
        if start < end:
            remapped.append(ReservedSpan(start, end, span.owner, span.reason))
    return tuple(remapped)


def _iter_symbol_replacements(
    text: str,
    *,
    mode: SymbolMode,
    keep_symbols: str,
    language: str,
    protected_ranges: tuple[tuple[int, int], ...] = (),
) -> tuple[Replacement, ...]:
    """Return mapped edits for residual symbols without joining lexical runs."""
    if mode == "none":
        return ()
    allowed = frozenset(keep_symbols) if mode == "keep" else frozenset()
    replacements: list[Replacement] = []
    soft_versions = tuple((match.start(), match.end()) for match in _SOFT_VERSION_RE.finditer(text))
    protected_ranges = tuple(protected_ranges) + soft_versions

    def protected_at(index: int) -> tuple[int, int] | None:
        return next(
            ((start, end) for start, end in protected_ranges if start <= index < end),
            None,
        )

    def removable(character: str) -> bool:
        return unicodedata.category(character).startswith(("P", "S")) and character not in allowed

    index = 0
    while index < len(text):
        protected = protected_at(index)
        if protected is not None:
            index = protected[1]
            continue
        character = text[index]
        if not removable(character):
            index += 1
            continue

        start = index
        while index < len(text) and removable(text[index]) and protected_at(index) is None:
            index += 1
        end = index
        left = text[start - 1] if start else ""
        right = text[end] if end < len(text) else ""
        replacement = " " if left.isalnum() and right.isalnum() else ""

        if (
            character == "&"
            and base_language(language) == "en"
            and start > 0
            and end < len(text)
            and text[start - 1].isspace()
            and text[end].isspace()
        ):
            replacement = "and"
        replacements.append(
            Replacement(start, end, replacement, "symbols", language, "symbol.remove")
        )
    return tuple(replacements)


def _reserved_ranges_in_internal(
    text: str,
    spans: tuple[ReservedSpan, ...],
    protected_values: tuple[str, ...],
    protected_placeholders: tuple[str, ...],
) -> tuple[tuple[int, int], ...]:
    """Translate visible reservation coordinates into sentinel text coordinates."""
    replacements = tuple(
        Replacement(span.start, span.end, "") for span in spans if span.start < span.end
    )
    internal = map_visible_replacements_to_internal(
        text,
        replacements,
        protected_values,
        protected_placeholders,
    )
    return tuple((item.start, item.end) for item in internal)


def _expand_partial_structured_protection(
    text: str,
    *,
    language: str,
    spans: tuple[ProtectedSpan, ...],
) -> tuple[ProtectedSpan, ...]:
    """Fail closed when a caller span intersects a recognized quantity."""
    if not spans:
        return spans
    ranges = [(span.start, span.end, span.kind) for span in spans]
    for match in iter_unit_matches(text, resolve_abbr2words_language(language)):
        for index, (start, end, kind) in enumerate(ranges):
            if start < match.end and match.start < end:
                ranges[index] = (min(start, match.start), max(end, match.end), kind)
    return tuple(ProtectedSpan(start, end, kind=kind) for start, end, kind in ranges)


def _prepare_protected_text(
    text: str,
    *,
    language: str,
    protected_spans: Iterable[ProtectedSpan | tuple[int, int]] | None,
    protect_literals: bool,
    strict: bool,
) -> tuple[ProtectedText, tuple[ProtectedSpan, ...], tuple[str, ...]]:
    """Validate, discover, merge, and sentinel-protect source ranges."""
    supplied_spans, warnings = coerce_protected_spans(
        protected_spans,
        text_length=len(text),
        strict=strict,
    )
    supplied_spans = _expand_partial_structured_protection(
        text, language=language, spans=supplied_spans
    )
    merged: list[ProtectedSpan] = list(
        discover_protected_spans(text, language=language, protect_literals=protect_literals)
    )
    for candidate in supplied_spans:
        if not any(
            existing.start < candidate.end and candidate.start < existing.end for existing in merged
        ):
            merged.append(candidate)
    merged.sort(key=lambda item: (item.start, item.end))
    return protect_text(text, tuple(merged)), tuple(merged), warnings


def _prepare_annotations(
    clean_text: str,
    protected: ProtectedText,
    *,
    annotations: Iterable[TokenAnnotation] | None,
    nlp: object | None,
    use_spacy: bool | None,
    spacy_model: str | None,
    language_code: str,
    interpretation_mode: InterpretationMode,
    strict: bool,
) -> tuple[Iterable[TokenAnnotation] | None, tuple[str, ...]]:
    """Load/validate annotations and remap them into protected coordinates."""
    warnings: list[str] = []
    if interpretation_mode is InterpretationMode.SURFACE:
        if use_spacy is True or nlp is not None:
            message = "[POLICY] surface mode ignores spaCy/NLP recognition context"
            if strict:
                raise ValueError(message)
            warnings.append(message)
        return None, tuple(warnings)
    if annotations is not None:
        annotations = validate_annotations(clean_text, annotations)
    if annotations is None and use_spacy is not False:
        if nlp is None and (spacy_model is not None or use_spacy is True):
            try:
                nlp = load_spacy_model(spacy_model, language=language_code)
            except SpacyModelError as exc:
                if strict:
                    raise
                warnings.append(f"[SPACY] {exc}")
        if nlp is not None:
            from .annotations import spacy_annotations

            annotations = spacy_annotations(clean_text, cast(_SpacyPipeline, nlp))

    current = remap_annotations_for_replacements(
        annotations,
        ((span.start, span.end, 1) for span in protected.spans),
    )
    if current is not None:
        current = validate_annotations(protected.text, current)
    return current, tuple(warnings)


def _resolve_number_options(
    language_code: str,
    *,
    expand_structured: bool,
    expand_numbers: bool,
    number_policy: NumberPolicy | None,
    model_punctuation: bool,
) -> tuple[bool, bool, tuple[str, ...]]:
    """Resolve numeric ownership and downstream punctuation warnings once."""
    warnings: list[str] = []
    if model_punctuation:
        warnings.append("[PUNCTUATION] model punctuation remains downstream")
    if number_policy is None:
        return expand_structured, expand_numbers, tuple(warnings)

    structured_enabled = expand_structured and number_policy is NumberPolicy.STRUCTURED_AND_PLAIN
    plain_enabled = expand_numbers and number_policy in {
        NumberPolicy.PLAIN,
        NumberPolicy.STRUCTURED_AND_PLAIN,
    }
    if number_policy is NumberPolicy.CALLER_MANAGED:
        warnings.append(
            f"[NUMBERS] caller-managed number categories for language {language_code!r}"
        )
    elif number_policy is NumberPolicy.NONE:
        warnings.append(f"[NUMBERS] unsupported number policy for language {language_code!r}")
    return structured_enabled, plain_enabled, tuple(warnings)


def _finalize_mapping(
    clean_text: str,
    spoken_text: str,
    stages: tuple[PreparationStage, ...],
) -> tuple[OffsetMap, tuple[SourceReplacement, ...]]:
    """Compose stage maps and project edits into source coordinates."""
    stage_maps = tuple(
        OffsetMap.from_replacements(
            len(stage.before),
            tuple(
                Replacement(
                    edit.source_start,
                    edit.source_end,
                    edit.replacement,
                    edit.kind,
                    edit.language,
                    edit.rule,
                )
                for edit in stage.mapped_edits
            ),
            output_length=len(stage.after),
            edits=stage.mapped_edits,
        )
        for stage in stages
    )
    offset_map = OffsetMap.identity(len(clean_text))
    for stage_map in stage_maps:
        offset_map = offset_map.compose(stage_map)
    source_replacements = compose_source_replacements(
        clean_text,
        spoken_text,
        stages,
        stage_maps,
    )
    return offset_map, source_replacements


def _build_prepared_text(
    *,
    source_text: str,
    clean_text: str,
    spoken_text: str,
    language: str,
    stages: tuple[PreparationStage, ...],
    protected_spans: tuple[ProtectedSpan, ...],
    offset_map: OffsetMap,
    source_replacements: tuple[SourceReplacement, ...],
    reserved_spans: tuple[ReservedSpan, ...],
    warnings: tuple[str, ...],
) -> PreparedText:
    """Construct the public result from finalized pipeline state."""
    return PreparedText(
        source_text=source_text,
        clean_text=clean_text,
        spoken_text=spoken_text,
        language=language,
        stages=stages,
        mapped_edits=tuple(edit for stage in stages for edit in stage.mapped_edits),
        source_replacements=source_replacements,
        protected_spans=protected_spans,
        reserved_spans=reserved_spans,
        offset_map=offset_map,
        warnings=warnings,
    )
