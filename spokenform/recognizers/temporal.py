"""Temporal sequence rendering helpers owned by the temporal domain."""

from __future__ import annotations

import re

from num2words import num2words

from ..language import base_language, resolve_num2words_language
from ..sequences import SEGMENT_BOUNDARY

_COUNTDOWN_CONTEXT_RE = re.compile(
    r"\b(?:"
    r"countdown(?:\s+(?:is|from))?|"
    r"count(?:ing)?\s+down(?:\s+from)?|"
    r"start(?:s|ed|ing)?|"
    r"begin(?:s|ning)?|"
    r"launch(?:es|ed|ing)?|"
    r"initiat(?:e|es|ed|ing)|"
    r"go"
    r")\s+(?:in\s+)?$",
    re.IGNORECASE,
)


def _cardinal(value: int, language: str) -> str:
    rendered = str(num2words(value, lang=resolve_num2words_language(language)))
    return rendered.replace(" and ", " ") if base_language(language) == "en" else rendered


def countdown_is_plausible(text: str, start: int, language: str) -> bool:
    """Require English countdown wording immediately before a numeric chain."""
    if base_language(language) != "en":
        return False
    prefix = text[max(0, start - 64) : start]
    return bool(_COUNTDOWN_CONTEXT_RE.search(prefix))


def countdown_text(value: str, language: str) -> str:
    """Render a contextual countdown with a generic segment boundary."""
    values = re.split(r"\s*[-–]\s*", value)
    return f" {SEGMENT_BOUNDARY} ".join(_cardinal(int(item), language) for item in values)


__all__ = ["countdown_is_plausible", "countdown_text"]
