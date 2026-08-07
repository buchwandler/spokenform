"""Public preparation pipeline."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from abbr2words import abbr2words_with_replacements, normalize_language

from .annotations import (
    remap_annotations_for_replacements,
    to_abbr2words_annotations,
    validate_annotations,
)
from .config import NumberPolicy, PreparationConfig
from .mapping import (
    OffsetMap,
    Replacement,
    compose_source_replacements,
    convert_abbr_replacements,
    replacements_from_diff,
)
from .models import PreparationStage, PreparedText, TokenAnnotation
from .numbers import normalize_numbers
from .protection import (
    ProtectedSpan,
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
_LINE_SPACE_RE = re.compile(r" *\n *")
_EXCESS_LINES_RE = re.compile(r"\n{3,}")


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
    """Apply independently configurable Unicode and whitespace policies."""
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


def prepare(
    text: str,
    *,
    language: str = "en",
    config: PreparationConfig | None = None,
    annotations: Iterable[TokenAnnotation] | None = None,
    nlp: object | None = None,
    protected_spans: Iterable[ProtectedSpan | tuple[int, int]] | None = None,
    use_spacy: bool | None = None,
    spacy_model: str | None = None,
    expand_abbreviations: bool = True,
    expand_structured: bool = True,
    expand_numbers: bool = True,
    normalize_whitespace: bool = True,
    normalize_unicode: bool = True,
    strip_outer_whitespace: bool = True,
    collapse_horizontal_whitespace: bool = True,
    normalize_line_whitespace: bool = True,
    collapse_blank_lines: bool = True,
    number_policy: NumberPolicy | None = None,
    context: bool = True,
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

    if config is not None:
        language = config.language
        use_spacy = config.use_spacy
        spacy_model = config.spacy_model
        expand_abbreviations = config.expand_abbreviations
        expand_structured = config.expand_structured
        expand_numbers = config.expand_numbers
        normalize_whitespace = config.normalize_whitespace
        normalize_unicode = config.normalize_unicode
        strip_outer_whitespace = config.strip_outer_whitespace
        collapse_horizontal_whitespace = config.collapse_horizontal_whitespace
        normalize_line_whitespace = config.normalize_line_whitespace
        collapse_blank_lines = config.collapse_blank_lines
        number_policy = config.number_policy
        context = config.context
        strict = config.strict
    elif use_spacy is not None or spacy_model is not None:
        PreparationConfig(
            language=language,
            use_spacy=use_spacy,
            spacy_model=spacy_model,
            expand_abbreviations=expand_abbreviations,
            expand_structured=expand_structured,
            expand_numbers=expand_numbers,
            normalize_whitespace=normalize_whitespace,
            normalize_unicode=normalize_unicode,
            strip_outer_whitespace=strip_outer_whitespace,
            collapse_horizontal_whitespace=collapse_horizontal_whitespace,
            normalize_line_whitespace=normalize_line_whitespace,
            collapse_blank_lines=collapse_blank_lines,
            number_policy=number_policy,
            context=context,
            strict=strict,
        )

    clean_text = text
    language_code = normalize_language(language)
    selected_number_policy = number_policy
    policy_warnings: list[str] = []
    if selected_number_policy is None:
        structured_numbers_enabled = expand_structured
        plain_numbers_enabled = expand_numbers
    else:
        structured_numbers_enabled = expand_structured and selected_number_policy in {
            NumberPolicy.STRUCTURED_AND_PLAIN,
        }
        plain_numbers_enabled = expand_numbers and selected_number_policy in {
            NumberPolicy.PLAIN,
            NumberPolicy.STRUCTURED_AND_PLAIN,
        }
        if selected_number_policy is NumberPolicy.CALLER_MANAGED:
            policy_warnings.append(
                f"[NUMBERS] caller-managed number categories for language {language_code!r}"
            )
        elif selected_number_policy is NumberPolicy.NONE:
            policy_warnings.append(
                f"[NUMBERS] unsupported number policy for language {language_code!r}"
            )

    supplied_spans, protection_warnings = coerce_protected_spans(
        protected_spans,
        text_length=len(clean_text),
        strict=strict,
    )
    discovered_spans = discover_protected_spans(clean_text)
    merged_protected: list[ProtectedSpan] = list(discovered_spans)
    for candidate in supplied_spans:
        if not any(
            existing.start < candidate.end and candidate.start < existing.end
            for existing in merged_protected
        ):
            merged_protected.append(candidate)
    merged_protected.sort(key=lambda item: (item.start, item.end))
    protected = protect_text(clean_text, tuple(merged_protected))

    spacy_warnings: list[str] = []
    if annotations is not None:
        annotations = validate_annotations(clean_text, annotations)
    if annotations is None and use_spacy is not False:
        if nlp is None and (spacy_model is not None or use_spacy is True):
            try:
                nlp = load_spacy_model(spacy_model, language=language_code)
            except SpacyModelError as exc:
                if strict:
                    raise
                spacy_warnings.append(f"[SPACY] {exc}")
        if nlp is not None:
            from .annotations import spacy_annotations

            annotations = spacy_annotations(clean_text, nlp)

    current_annotations = remap_annotations_for_replacements(
        annotations,
        ((span.start, span.end, 1) for span in protected.spans),
    )
    if current_annotations is not None:
        current_annotations = validate_annotations(protected.text, current_annotations)

    stages: list[PreparationStage] = []
    current = protected.text

    if normalize_unicode:
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
            )
            current_annotations = remap_annotations_for_replacements(
                current_annotations,
                ((item.start, item.end, len(item.text)) for item in internal_replacements),
            )

    if structured_numbers_enabled:
        structured = normalize_structured(
            protected.restore(current),
            language=language_code,
            protected_ranges=map_internal_protected_spans_to_visible(
                current,
                protected.values,
            ),
        )
        if structured.replacements:
            internal_replacements = map_visible_replacements_to_internal(
                current,
                structured.replacements,
                protected.values,
            )
            current = apply_replacement_stage(
                stages,
                "structured",
                current,
                structured.replacements,
                protected_values=protected.values,
                language=language_code,
            )
            current_annotations = remap_annotations_for_replacements(
                current_annotations,
                ((item.start, item.end, len(item.text)) for item in internal_replacements),
            )

    if expand_abbreviations:
        visible_annotations = remap_annotations_for_replacements(
            current_annotations,
            (
                (index, index + 1, len(value))
                for index, character in enumerate(current)
                if 0xE000 <= ord(character) < 0xE000 + len(protected.values)
                for value in (protected.values[ord(character) - 0xE000],)
            ),
        )
        abbreviation_result = abbr2words_with_replacements(
            protected.restore(current),
            lang=language_code,
            context=context,
            annotations=to_abbr2words_annotations(visible_annotations),
            protected_spans=map_internal_protected_spans_to_visible(
                current,
                protected.values,
            ),
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
            language=language_code,
        )
        internal_replacements = map_visible_replacements_to_internal(
            before,
            abbreviation_replacements,
            protected.values,
        )
        current_annotations = remap_annotations_for_replacements(
            current_annotations,
            ((item.start, item.end, len(item.text)) for item in internal_replacements),
        )

    if plain_numbers_enabled:
        before = current
        current = apply_stage(
            stages,
            "numbers",
            current,
            lambda value: normalize_numbers(value, language=language_code),
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
        )
        current_annotations = remap_annotations_for_replacements(
            current_annotations,
            ((item.start, item.end, len(item.text)) for item in internal_replacements),
        )

    if normalize_whitespace:
        before = current
        current = apply_stage(
            stages,
            "whitespace",
            current,
            lambda value: normalize_spacing(
                value,
                normalize_unicode=False,
                strip_outer_whitespace=strip_outer_whitespace,
                collapse_horizontal_whitespace=collapse_horizontal_whitespace,
                normalize_line_whitespace=normalize_line_whitespace,
                collapse_blank_lines=collapse_blank_lines,
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
        )
        current_annotations = remap_annotations_for_replacements(
            current_annotations,
            ((item.start, item.end, len(item.text)) for item in internal_replacements),
        )

    current = protected.restore(current)

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
        current,
        tuple(stages),
        stage_maps,
    )

    return PreparedText(
        source_text=text,
        clean_text=clean_text,
        spoken_text=current,
        language=language_code,
        stages=tuple(stages),
        mapped_edits=tuple(edit for stage in stages for edit in stage.mapped_edits),
        source_replacements=source_replacements,
        protected_spans=tuple(merged_protected),
        offset_map=offset_map,
        warnings=(*protection_warnings, *spacy_warnings, *policy_warnings),
    )


prepare_text = prepare


def prepare_for_kokorog2p(
    text: str,
    language: str = "en",
    *,
    config: PreparationConfig | None = None,
    **kwargs: object,
) -> PreparedText:
    """Prepare one language with the kokorog2p-safe profile."""
    selected = config or PreparationConfig.for_kokorog2p(language)
    return prepare(text, config=selected, **kwargs)  # type: ignore[arg-type]


__all__ = ["prepare", "prepare_text", "prepare_for_kokorog2p", "normalize_spacing"]
