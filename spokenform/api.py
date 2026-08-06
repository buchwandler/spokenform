"""Public preparation pipeline."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

from abbr2words import TokenAnnotation, abbr2words, normalize_language

from .detection import LanguageDetector, lingua_detector
from .models import LanguageSpan, PreparedText, PreparationStage, make_stage
from .numbers import normalize_numbers

_HORIZONTAL_SPACE_RE = re.compile(r"[\t\u00a0\u202f ]+")
_LINE_SPACE_RE = re.compile(r" *\n *")
_EXCESS_LINES_RE = re.compile(r"\n{3,}")


def normalize_spacing(text: str) -> str:
    """Apply conservative Unicode and whitespace normalization."""
    normalized = unicodedata.normalize("NFC", text)
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
    detect_language: bool = False,
    detector: LanguageDetector | None = None,
    allowed_languages: Iterable[str] | None = None,
    annotations: Iterable[TokenAnnotation] | None = None,
    expand_abbreviations: bool = True,
    expand_numbers: bool = True,
    normalize_whitespace: bool = True,
    context: bool = True,
) -> PreparedText:
    """Convert written text into a readable form intended for speech.

    Abbreviation and unit expansion runs before number verbalization so numeric
    context remains available to :mod:`abbr2words` guards.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    detected = False
    resolved_language = language
    if detect_language:
        detector_impl = detector or lingua_detector(tuple(allowed_languages or ()))
        resolved_language = detector_impl(text)
        detected = True
    language_code = normalize_language(resolved_language)

    stages: list[PreparationStage] = []
    current = text

    if expand_abbreviations:
        after = abbr2words(
            current,
            lang=language_code,
            context=context,
            annotations=annotations,
        )
        current = _run_stage(stages, "abbreviations", current, after)

    if expand_numbers:
        after = normalize_numbers(current, language=language_code)
        current = _run_stage(stages, "numbers", current, after)

    if normalize_whitespace:
        after = normalize_spacing(current)
        current = _run_stage(stages, "whitespace", current, after)

    source = "detected" if detected else "configured"
    spans = (
        LanguageSpan(start=0, end=len(current), language=language_code, source=source),
    ) if current else ()

    return PreparedText(
        source_text=text,
        clean_text=text,
        spoken_text=current,
        language=language_code,
        stages=tuple(stages),
        language_spans=spans,
    )


prepare_text = prepare


__all__ = ["prepare", "prepare_text", "normalize_spacing"]
