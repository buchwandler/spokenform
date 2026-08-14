"""Shared text comparison metrics for diagnostic benchmarks."""

from __future__ import annotations

import string
import unicodedata
from collections.abc import Iterable

from spokenform.sequences import render_letters

SEMANTIC_SYMBOLS = frozenset("$€£%@/°+=#&")


def literal_key(text: str) -> str:
    """Normalize only Unicode and whitespace for literal comparison."""
    normalized = unicodedata.normalize("NFC", text).strip()
    return " ".join(normalized.split())


def speech_key(text: str) -> tuple[str, ...]:
    """Tokenize speech while retaining semantically meaningful symbols."""
    characters: list[str] = []
    for character in unicodedata.normalize("NFC", text).casefold():
        if character in SEMANTIC_SYMBOLS:
            characters.append(character)
        elif unicodedata.category(character).startswith("P") or character in string.punctuation:
            characters.append(" ")
        else:
            characters.append(character)
    return tuple(" ".join("".join(characters).split()).split())


def speech_key_equivalent(text: str, *, language: str = "en") -> tuple[str, ...]:
    """Fold exact localized spoken letter names to their ASCII graphemes."""
    reverse: dict[str, str] = {}
    for character in "abcdefghijklmnopqrstuvwxyz":
        rendered = speech_key(render_letters(character, language=language))
        if len(rendered) == 1:
            reverse.setdefault(rendered[0], character)
    return tuple(reverse.get(token, token) for token in speech_key(text))


def word_error_rate(reference: Iterable[str], hypothesis: Iterable[str]) -> float:
    """Return word-level Levenshtein error rate."""
    reference_words = tuple(reference)
    hypothesis_words = tuple(hypothesis)
    if not reference_words:
        return 0.0 if not hypothesis_words else 1.0
    previous = list(range(len(hypothesis_words) + 1))
    for row, reference_word in enumerate(reference_words, 1):
        current = [row]
        for column, hypothesis_word in enumerate(hypothesis_words, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (reference_word != hypothesis_word),
                )
            )
        previous = current
    return previous[-1] / len(reference_words)


__all__ = [
    "SEMANTIC_SYMBOLS",
    "literal_key",
    "speech_key",
    "speech_key_equivalent",
    "word_error_rate",
]
