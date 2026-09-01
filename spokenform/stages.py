"""Small helpers shared by the explicit preparation stages."""

from __future__ import annotations

from collections.abc import Callable

from .mapping import OffsetMap, Replacement, apply_replacements, resolve_replacements
from .models import PreparationStage, ReservedSpan, TextEdit, make_stage


def apply_stage(
    stages: list[PreparationStage],
    name: str,
    text: str,
    transform: Callable[[str], str],
    restore: Callable[[str], str] | None = None,
) -> str:
    """Apply one deterministic stage and retain its before/after provenance."""
    after = transform(text)
    restore_text = restore or (lambda value: value)
    stages.append(make_stage(name, restore_text(text), restore_text(after)))
    return after


def apply_replacement_stage(
    stages: list[PreparationStage],
    name: str,
    text: str,
    replacements: tuple[Replacement, ...],
    *,
    protected_values: tuple[str, ...] = (),
    protected_placeholders: tuple[str, ...] = (),
    language: str | None = None,
    reserved: tuple[ReservedSpan, ...] = (),
) -> str:
    """Apply exact replacements while keeping protected sentinels internal.

    Replacement coordinates are defined against the visible stage input. The
    returned continuation value retains private-use sentinels so later stages
    cannot rewrite protected values.
    """
    visible_before = _restore(text, protected_values, protected_placeholders)
    visible_replacements = resolve_replacements(
        tuple(
            Replacement(
                item.start,
                item.end,
                item.text,
                item.kind,
                item.language or language,
                item.rule,
                item.specificity,
                item.recognition_domain,
                item.recognition_evidence,
                item.evidence_source,
                item.evidence_score,
                item.evidence_cues,
            )
            for item in replacements
        ),
        source_length=len(visible_before),
    )
    visible_after, mapped_edits, _ = apply_replacements(
        visible_before, visible_replacements, stage=name
    )
    edits = tuple(
        TextEdit(
            start=item.start,
            end=item.end,
            source=visible_before[item.start : item.end],
            replacement=item.text,
            stage=name,
        )
        for item in visible_replacements
    )
    stages.append(
        PreparationStage(
            name=name,
            before=visible_before,
            after=visible_after,
            edits=edits,
            mapped_edits=mapped_edits,
            reserved=reserved,
        )
    )

    internal = map_visible_replacements_to_internal(
        text,
        visible_replacements,
        protected_values,
        protected_placeholders,
    )
    after, _, _ = apply_replacements(text, tuple(internal), stage=name)
    return after


def map_visible_replacements_to_internal(
    text: str,
    replacements: tuple[Replacement, ...],
    protected_values: tuple[str, ...],
    protected_placeholders: tuple[str, ...] = (),
) -> tuple[Replacement, ...]:
    """Translate visible-stage replacements to protected working-text offsets."""
    restoration = _restoration_map(text, protected_values, protected_placeholders)
    internal = tuple(
        Replacement(
            *restoration.map_output_span(item.start, item.end),
            item.text,
            item.kind,
            item.language,
            item.rule,
            item.specificity,
            item.recognition_domain,
            item.recognition_evidence,
            item.evidence_source,
            item.evidence_score,
            item.evidence_cues,
        )
        for item in replacements
    )
    return resolve_replacements(internal, source_length=len(text))


def map_internal_protected_spans_to_visible(
    text: str,
    protected_values: tuple[str, ...],
    protected_placeholders: tuple[str, ...] = (),
) -> tuple[tuple[int, int], ...]:
    """Return protected sentinel spans in the restored visible text."""
    restoration = _restoration_map(text, protected_values, protected_placeholders)
    placeholders = set(
        protected_placeholders
        or tuple(chr(0xE000 + index) for index in range(len(protected_values)))
    )
    return tuple(
        restoration.map_source_span(index, index + 1)
        for index, character in enumerate(text)
        if character in placeholders
    )


def _restore(
    text: str,
    values: tuple[str, ...],
    placeholders: tuple[str, ...] = (),
) -> str:
    result = text
    actual_placeholders = placeholders or tuple(chr(0xE000 + index) for index in range(len(values)))
    for placeholder, value in zip(actual_placeholders, values, strict=True):
        result = result.replace(placeholder, value)
    return result


def _restoration_map(
    text: str,
    values: tuple[str, ...],
    placeholders: tuple[str, ...] = (),
) -> OffsetMap:
    actual_placeholders = placeholders or tuple(chr(0xE000 + index) for index in range(len(values)))
    replacements_by_placeholder = dict(zip(actual_placeholders, values, strict=True))
    replacements = tuple(
        Replacement(index, index + 1, replacements_by_placeholder[character])
        for index, character in enumerate(text)
        if character in replacements_by_placeholder
    )
    return OffsetMap.from_replacements(
        len(text),
        replacements,
        output_length=len(_restore(text, values, actual_placeholders)),
    )


__all__ = [
    "apply_stage",
    "apply_replacement_stage",
    "map_internal_protected_spans_to_visible",
    "map_visible_replacements_to_internal",
]
