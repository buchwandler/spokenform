"""Provider-neutral annotation adapters."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from abbr2words import TokenAnnotation


def annotations_from_spacy(doc: Iterable[Any]) -> tuple[TokenAnnotation, ...]:
    """Convert a spaCy-like ``Doc`` into source-aligned annotations.

    The adapter imports no spaCy modules and can therefore be used with compatible
    providers or simple test doubles.
    """
    annotations: list[TokenAnnotation] = []
    for token in doc:
        text = str(token.text)
        start = int(token.idx)
        annotations.append(
            TokenAnnotation(
                start=start,
                end=start + len(text),
                pos=getattr(token, "pos_", None) or None,
                tag=getattr(token, "tag_", None) or None,
            )
        )
    return tuple(annotations)


def spacy_annotations(text: str, nlp: Any) -> tuple[TokenAnnotation, ...]:
    """Run an existing spaCy-compatible pipeline and convert its tokens."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    return annotations_from_spacy(nlp(text))


__all__ = ["TokenAnnotation", "annotations_from_spacy", "spacy_annotations"]
