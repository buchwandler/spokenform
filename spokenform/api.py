"""Public preparation pipeline."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from typing import Literal

from abbr2words import abbr2words, normalize_language

from .annotations import to_abbr2words_annotations
from .config import PreparationConfig
from .detection import LanguageDetector, lingua_detector
from .mapping import OffsetMap, replacements_from_diff
from .models import (
    LanguageSpan,
    PreparationStage,
    PreparedText,
    TokenAnnotation,
    make_stage,
)
from .numbers import normalize_numbers
from .protection import (
    ProtectedSpan,
    coerce_protected_spans,
    discover_protected_spans,
    protect_text,
)
from .spacy_support import SpacyModelError, load_spacy_model
from .ssmd import parse_markup
from .stages import apply_stage

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


def _run_stage(
    stages: list[PreparationStage],
    name: str,
    before: str,
    after: str,
) -> str:
    stages.append(make_stage(name, before, after))
    return after


def prepare(
    text: str,
    *,
    language: str = "en",
    config: PreparationConfig | None = None,
    detect_language: bool = False,
    detector: LanguageDetector | None = None,
    allowed_languages: Iterable[str] | None = None,
    annotations: Iterable[TokenAnnotation] | None = None,
    nlp: object | None = None,
    language_spans: Iterable[LanguageSpan] | None = None,
    protected_spans: Iterable[ProtectedSpan] | None = None,
    markup: Literal["plain", "ssmd", "auto"] = "plain",
    render_language_marks: bool = False,
    use_spacy: bool | None = None,
    spacy_model: str | None = None,
    expand_abbreviations: bool = True,
    expand_numbers: bool = True,
    normalize_whitespace: bool = True,
    normalize_unicode: bool = True,
    context: bool = True,
    strict: bool = False,
) -> PreparedText:
    """Convert written text into a readable form intended for speech.

    Abbreviation and unit expansion runs before number verbalization so numeric
    context remains available to :mod:`abbr2words` guards.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if config is not None:
        language = config.language or "en"
        detect_language = config.detect_language
        allowed_languages = config.allowed_languages
        markup = config.markup
        render_language_marks = config.render_language_marks
        use_spacy = config.use_spacy
        spacy_model = config.spacy_model
        expand_abbreviations = config.expand_abbreviations
        expand_numbers = config.expand_numbers
        normalize_whitespace = config.normalize_whitespace
        normalize_unicode = config.normalize_unicode
        context = config.context
        strict = config.strict
    elif markup != "plain" or render_language_marks or use_spacy is not None or spacy_model:
        PreparationConfig(
            language=language,
            detect_language=detect_language,
            allowed_languages=tuple(allowed_languages or ()),
            markup=markup,
            render_language_marks=render_language_marks,
            use_spacy=use_spacy,
            spacy_model=spacy_model,
            expand_abbreviations=expand_abbreviations,
            expand_numbers=expand_numbers,
            normalize_whitespace=normalize_whitespace,
            normalize_unicode=normalize_unicode,
            context=context,
            strict=strict,
        )
    if markup != "plain":
        parsed_markup = parse_markup(
            text,
            mode=markup,
            language=language,
            strict=strict,
        )
    else:
        parsed_markup = parse_markup(text, mode="plain")

    clean_text = parsed_markup.clean_text

    supplied_spans, protection_warnings = coerce_protected_spans(
        protected_spans,
        text_length=len(clean_text),
        strict=strict,
    )
    markup_protected, markup_protection_warnings = coerce_protected_spans(
        parsed_markup.protected_spans,
        text_length=len(clean_text),
        strict=strict,
    )
    discovered_spans = discover_protected_spans(clean_text)
    merged_protected: list[ProtectedSpan] = list(discovered_spans) + list(markup_protected)
    for candidate in supplied_spans:
        if not any(
            existing.start < candidate.end and candidate.start < existing.end
            for existing in merged_protected
        ):
            merged_protected.append(candidate)
    merged_protected.sort(key=lambda item: (item.start, item.end))
    protected = protect_text(clean_text, tuple(merged_protected))

    detected = False
    resolved_language = language
    if detect_language:
        detector_impl = detector or lingua_detector(tuple(allowed_languages or ()))
        resolved_language = detector_impl(clean_text)
        detected = True
    language_code = normalize_language(resolved_language)

    spacy_warnings: list[str] = []
    if nlp is None and use_spacy is not False and spacy_model is not None:
        try:
            nlp = load_spacy_model(spacy_model, language=language_code)
        except SpacyModelError as exc:
            if strict:
                raise
            spacy_warnings.append(f"[SPACY] {exc}")
    elif use_spacy is True and nlp is None:
        try:
            nlp = load_spacy_model(spacy_model, language=language_code)
        except SpacyModelError as exc:
            if strict:
                raise
            spacy_warnings.append(f"[SPACY] {exc}")

    if nlp is not None and annotations is None and use_spacy is not False:
        from .annotations import spacy_annotations

        annotations = spacy_annotations(clean_text, nlp)

    stages: list[PreparationStage] = []
    current = protected.text

    if expand_abbreviations:
        current = apply_stage(
            stages,
            "abbreviations",
            current,
            lambda value: abbr2words(
                value,
                lang=language_code,
                context=context,
                annotations=to_abbr2words_annotations(annotations),
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

    source: Literal["configured", "detected"] = "detected" if detected else "configured"
    if parsed_markup.language_spans:
        spans = parsed_markup.language_spans
    elif language_spans is not None:
        spans = tuple(language_spans)
    else:
        spans = (
            (LanguageSpan(start=0, end=len(clean_text), language=language_code, source=source),)
            if clean_text
            else ()
        )

    warnings = (
        *parsed_markup.warnings,
        *protection_warnings,
        *markup_protection_warnings,
        *spacy_warnings,
    )
    marked_text = None
    if render_language_marks:
        marked_text = PreparedText(
            source_text=text,
            clean_text=clean_text,
            spoken_text=current,
            language=language_code,
            language_spans=spans,
        ).render_ssmd(source="clean")

    return PreparedText(
        source_text=text,
        clean_text=clean_text,
        spoken_text=current,
        language=language_code,
        stages=tuple(stages),
        language_spans=spans,
        mapped_edits=tuple(edit for stage in stages for edit in stage.mapped_edits),
        offset_map=offset_map,
        semantic_spans=parsed_markup.semantic_spans,
        warnings=warnings,
        marked_text=marked_text,
    )


prepare_text = prepare


__all__ = ["prepare", "prepare_text", "normalize_spacing"]
