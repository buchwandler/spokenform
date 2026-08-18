"""Generated-text casing helpers."""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Final

from .language import base_language
from .mapping import Replacement

_SPANISH_OPENING_PREFIX_CHARS: Final[frozenset[str]] = frozenset(
    {'"', "'", "(", "[", "{", "¡", "¿", "«"}
)
_SPANISH_NUMERIC_RULE_MARKERS: Final[tuple[str, ...]] = (
    ".currency",
    ".date",
    ".number",
    ".ordinal",
    ".quantity",
    ".time",
    "sequence.coordinate",
    "sequence.countdown",
    "sequence.currency",
    "sequence.decade",
    "sequence.duration",
    "sequence.fraction",
    "sequence.height",
    "sequence.math",
    "sequence.percent",
    "sequence.sports",
    "sequence.year",
)
_SPANISH_GENERATED_START_RE: Final = re.compile(
    r"""^\s*(?:(?:"|'|\(|\[|\{|¡|¿|«)\s*)*(?:[$€£]|[+\-−]?\d|√)""",
)
_SPANISH_NUMERIC_SEGMENT_RE: Final = re.compile(r"""^\s*(?:[$€£]|[+\-−]?\d|√|[.,]\d)""")


def capitalize_generated_sentence_start(
    *,
    source: str,
    start: int,
    replacement: str,
    language: str,
) -> str:
    """Capitalize generated Spanish numeric text when it starts the input."""
    if base_language(language) != "es" or not _is_start_of_input_position(source, start):
        return replacement
    return _capitalize_first_alphabetic(replacement)


def capitalize_generated_numeric_replacements(
    source: str,
    replacements: tuple[Replacement, ...],
    *,
    language: str,
) -> tuple[Replacement, ...]:
    """Capitalize Spanish structured numeric replacements at start of input."""
    if base_language(language) != "es":
        return replacements

    updated: list[Replacement] = []
    for item in replacements:
        text = item.text
        if _is_structured_numeric_rule(item.rule) and _source_segment_starts_numeric(
            source, item.start
        ):
            text = capitalize_generated_sentence_start(
                source=source,
                start=item.start,
                replacement=text,
                language=language,
            )
        updated.append(item if text == item.text else replace(item, text=text))
    return tuple(updated)


def capitalize_generated_input_start(*, source: str, replacement: str, language: str) -> str:
    """Capitalize whole-result Spanish output when the source starts numeric."""
    if base_language(language) != "es" or not _SPANISH_GENERATED_START_RE.match(source):
        return replacement
    return capitalize_generated_sentence_start(
        source=source,
        start=0,
        replacement=replacement,
        language=language,
    )


def _is_start_of_input_position(source: str, start: int) -> bool:
    prefix = source[:start].lstrip()
    return not prefix or all(character in _SPANISH_OPENING_PREFIX_CHARS for character in prefix)


def _capitalize_first_alphabetic(text: str) -> str:
    for index, character in enumerate(text):
        if character.isalpha():
            return f"{text[:index]}{character.upper()}{text[index + 1 :]}"
    return text


def _is_structured_numeric_rule(rule: str | None) -> bool:
    value = (rule or "").casefold()
    return any(marker in value for marker in _SPANISH_NUMERIC_RULE_MARKERS)


def _source_segment_starts_numeric(source: str, start: int) -> bool:
    return bool(_SPANISH_NUMERIC_SEGMENT_RE.match(source[start:]))


__all__ = [
    "capitalize_generated_input_start",
    "capitalize_generated_numeric_replacements",
    "capitalize_generated_sentence_start",
]
