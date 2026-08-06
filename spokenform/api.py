"""Public preparation pipeline."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from abbr2words import abbr2words, normalize_language

from .annotations import (
    remap_annotations_for_replacements,
    to_abbr2words_annotations,
    validate_annotations,
)
from .config import PreparationConfig
from .mapping import OffsetMap, replacements_from_diff
from .models import PreparationStage, PreparedText, TokenAnnotation
from .numbers import normalize_numbers
from .protection import (
    ProtectedSpan,
    coerce_protected_spans,
    discover_protected_spans,
    protect_text,
)
from .spacy_support import SpacyModelError, load_spacy_model
from .stages import apply_replacement_stage, apply_stage
from .structured import normalize_structured

_HORIZONTAL_SPACE_RE = re.compile(r"[\t\u00a0\u202f ]+")
_LINE_SPACE_RE = re.compile(r" *\n *")
_EXCESS_LINES_RE = re.compile(r"\n{3,}")


def normalize_spacing(text: str, *, normalize_unicode: bool = True) -> str:
    """Apply conservative Unicode and whitespace normalization."""
    normalized = unicodedata.normalize("NFC", text) if normalize_unicode else text
    normalized = _HORIZONTAL_SPACE_RE.sub(" ", normalized)
    normalized = _LINE_SPACE_RE.sub("\n", normalized)
    normalized = _EXCESS_LINES_RE.sub("\n\n", normalized)
    return normalized.strip()


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
            context=context,
            strict=strict,
        )

    clean_text = text
    language_code = normalize_language(language)

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

    protected_annotations = remap_annotations_for_replacements(
        annotations,
        ((span.start, span.end, 1) for span in protected.spans),
    )
    if protected_annotations is not None:
        protected_annotations = validate_annotations(protected.text, protected_annotations)

    stages: list[PreparationStage] = []
    current = protected.text

    if expand_structured:
        structured = normalize_structured(
            protected.restore(current),
            language=language_code,
            protected_ranges=((span.start, span.end) for span in merged_protected),
        )
        if structured.replacements:
            current = apply_replacement_stage(
                stages,
                "structured",
                current,
                structured.replacements,
                protected_values=protected.values,
                language=language_code,
            )

    if expand_abbreviations:
        current = apply_stage(
            stages,
            "abbreviations",
            current,
            lambda value: abbr2words(
                value,
                lang=language_code,
                context=context,
                annotations=to_abbr2words_annotations(protected_annotations),
            ),
            restore=protected.restore,
        )

    if expand_numbers:
        current = apply_stage(
            stages,
            "numbers",
            current,
            lambda value: normalize_numbers(value, language=language_code),
            restore=protected.restore,
        )

    if normalize_whitespace:
        current = apply_stage(
            stages,
            "whitespace",
            current,
            lambda value: normalize_spacing(value, normalize_unicode=normalize_unicode),
            restore=protected.restore,
        )

    current = protected.restore(current)

    stage_maps = [
        OffsetMap.from_replacements(
            len(stage.before),
            replacements_from_diff(stage.before, stage.after, stage.name),
            output_length=len(stage.after),
            edits=stage.mapped_edits,
        )
        for stage in stages
    ]
    offset_map = OffsetMap.identity(len(clean_text))
    for stage_map in stage_maps:
        offset_map = offset_map.compose(stage_map)

    return PreparedText(
        source_text=text,
        clean_text=clean_text,
        spoken_text=current,
        language=language_code,
        stages=tuple(stages),
        mapped_edits=tuple(edit for stage in stages for edit in stage.mapped_edits),
        offset_map=offset_map,
        warnings=(*protection_warnings, *spacy_warnings),
    )


prepare_text = prepare


__all__ = ["prepare", "prepare_text", "normalize_spacing"]
