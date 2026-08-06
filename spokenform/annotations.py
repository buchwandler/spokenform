"""Provider-neutral annotation adapters."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from abbr2words import TokenAnnotation as AbbrTokenAnnotation

from .models import TokenAnnotation


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
                text=text,
                pos=getattr(token, "pos_", None) or None,
                tag=getattr(token, "tag_", None) or None,
                lemma=getattr(token, "lemma_", None) or None,
                language=getattr(token, "lang_", None) or None,
            )
        )
    return tuple(annotations)


def validate_annotations(
    text: str,
    annotations: Iterable[TokenAnnotation],
) -> tuple[TokenAnnotation, ...]:
    """Validate and materialize source-aligned annotations.

    Annotation spans must be ordered, non-overlapping, inside ``text``, and match
    ``annotation.text`` when that optional value is supplied.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    materialized = tuple(annotations)
    previous_end = 0
    for index, annotation in enumerate(materialized):
        if not isinstance(annotation, TokenAnnotation):
            raise TypeError(f"Annotation {index} must be a TokenAnnotation")
        start = annotation.start
        end = annotation.end
        if (
            isinstance(start, bool)
            or isinstance(end, bool)
            or not isinstance(start, int)
            or not isinstance(end, int)
        ):
            raise TypeError(f"Annotation {index} offsets must be integers")
        if start < 0 or end <= start or end > len(text):
            raise ValueError(
                f"Annotation {index} range ({start}, {end}) is outside a non-empty "
                f"span within 0..{len(text)}"
            )
        if start < previous_end:
            raise ValueError(f"Annotation {index} overlaps or is out of order")
        for name in ("text", "pos", "tag", "lemma", "language"):
            value = getattr(annotation, name)
            if value is not None and not isinstance(value, str):
                raise TypeError(f"Annotation {index} {name} must be a string or None")
        if annotation.text is not None and text[start:end] != annotation.text:
            raise ValueError(
                f"Annotation {index} text {annotation.text!r} does not match "
                f"source slice {text[start:end]!r}"
            )
        previous_end = end
    return materialized


def remap_annotations_for_replacements(
    annotations: Iterable[TokenAnnotation] | None,
    replacements: Iterable[tuple[int, int, int]],
) -> tuple[TokenAnnotation, ...] | None:
    """Map annotations through ordered source replacements.

    Each replacement is ``(start, end, output_length)`` in the original source.
    Annotations overlapping a replaced range are omitted because their lexical
    evidence no longer describes the transformed text.
    """
    if annotations is None:
        return None

    ordered = tuple(sorted(replacements, key=lambda item: (item[0], item[1])))
    remapped: list[TokenAnnotation] = []
    for annotation in annotations:
        if any(
            start < annotation.end and annotation.start < end
            for start, end, _ in ordered
        ):
            continue

        def map_boundary(position: int) -> int:
            delta = 0
            for start, end, output_length in ordered:
                if end <= position:
                    delta += output_length - (end - start)
                else:
                    break
            return position + delta

        remapped.append(
            TokenAnnotation(
                start=map_boundary(annotation.start),
                end=map_boundary(annotation.end),
                text=annotation.text,
                pos=annotation.pos,
                tag=annotation.tag,
                lemma=annotation.lemma,
                language=annotation.language,
            )
        )
    return tuple(remapped)


def spacy_annotations(text: str, nlp: Any) -> tuple[TokenAnnotation, ...]:
    """Run an existing spaCy-compatible pipeline and convert its tokens."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    doc = nlp(text)
    doc_text = getattr(doc, "text", text)
    if doc_text != text:
        raise ValueError("spaCy-compatible pipeline returned a document for different text")
    return validate_annotations(text, annotations_from_spacy(doc))


def to_abbr2words_annotations(
    annotations: Iterable[TokenAnnotation] | None,
) -> tuple[AbbrTokenAnnotation, ...] | None:
    """Adapt public annotations to the internal abbr2words contract.

    The dependency currently consumes only source offsets, POS, and tags. The
    richer provider-neutral model remains the type exposed to callers.
    """
    if annotations is None:
        return None
    return tuple(
        AbbrTokenAnnotation(
            start=int(annotation.start),
            end=int(annotation.end),
            pos=getattr(annotation, "pos", None),
            tag=getattr(annotation, "tag", None),
        )
        for annotation in annotations
    )


__all__ = [
    "TokenAnnotation",
    "annotations_from_spacy",
    "remap_annotations_for_replacements",
    "spacy_annotations",
    "to_abbr2words_annotations",
    "validate_annotations",
]
