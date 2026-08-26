"""Deterministic source/output offset mapping for normalization stages."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from abbr2words import ExpansionReplacement

from .models import MappedEdit, PreparationStage, SourceReplacement


@dataclass(frozen=True, slots=True)
class Replacement:
    """One non-overlapping replacement in input coordinates."""

    start: int
    end: int
    text: str
    kind: str = "replacement"
    language: str | None = None
    rule: str | None = None
    specificity: int = 0
    recognition_domain: str | None = None
    recognition_evidence: str | None = None
    evidence_source: str | None = None
    evidence_score: float | None = None
    evidence_cues: tuple[str, ...] = ()

    def validate(self, source_length: int) -> None:
        if self.start < 0 or self.end < self.start or self.end > source_length:
            raise ValueError(f"Invalid replacement range ({self.start}, {self.end})")


@dataclass(frozen=True, slots=True)
class _ReplacementPosition:
    replacement: Replacement
    output_start: int

    @property
    def output_end(self) -> int:
        return self.output_start + len(self.replacement.text)


@dataclass(frozen=True, slots=True)
class OffsetMap:
    """A monotonic mapping over every source and output boundary."""

    source_length: int
    output_length: int
    source_left: tuple[int, ...]
    source_right: tuple[int, ...]
    output_left: tuple[int, ...]
    output_right: tuple[int, ...]
    edits: tuple[MappedEdit, ...] = ()

    @classmethod
    def identity(cls, length: int) -> OffsetMap:
        boundaries = tuple(range(length + 1))
        return cls(length, length, boundaries, boundaries, boundaries, boundaries)

    @classmethod
    def from_replacements(
        cls,
        source_length: int,
        replacements: tuple[Replacement, ...],
        *,
        output_length: int | None = None,
        edits: tuple[MappedEdit, ...] = (),
    ) -> OffsetMap:
        _validate_replacements(source_length, replacements)
        if output_length is None:
            output_length = source_length + sum(
                len(replacement.text) - (replacement.end - replacement.start)
                for replacement in replacements
            )
        positions, source_deltas, output_deltas = _precompute_replacement_positions(
            source_length,
            replacements,
            output_length,
        )
        insertions = {
            position.replacement.start: position
            for position in positions
            if position.replacement.start == position.replacement.end
        }
        non_insertions = tuple(
            position
            for position in positions
            if position.replacement.start < position.replacement.end
        )
        source_left: list[int] = []
        source_right: list[int] = []
        non_insertion_index = 0
        for position in range(source_length + 1):
            while (
                non_insertion_index < len(non_insertions)
                and non_insertions[non_insertion_index].replacement.end < position
            ):
                non_insertion_index += 1
            containing = (
                non_insertions[non_insertion_index]
                if non_insertion_index < len(non_insertions)
                and non_insertions[non_insertion_index].replacement.start <= position
                else None
            )
            insertion = insertions.get(position)
            if insertion is not None:
                source_left.append(insertion.output_start)
                source_right.append(insertion.output_end)
            elif containing is not None:
                replacement = containing.replacement
                if position == replacement.end:
                    source_left.append(containing.output_end)
                    source_right.append(containing.output_end)
                else:
                    source_left.append(containing.output_start)
                    source_right.append(containing.output_end)
            else:
                mapped = position + source_deltas[position]
                source_left.append(mapped)
                source_right.append(mapped)

        output_left: list[int] = []
        output_right: list[int] = []
        output_position_index = 0
        for position in range(output_length + 1):
            while (
                output_position_index < len(positions)
                and positions[output_position_index].output_end < position
            ):
                output_position_index += 1
            containing = (
                positions[output_position_index]
                if output_position_index < len(positions)
                and positions[output_position_index].output_start <= position
                else None
            )
            if containing is not None:
                replacement = containing.replacement
                if position == containing.output_end:
                    output_left.append(replacement.end)
                    output_right.append(replacement.end)
                else:
                    output_left.append(replacement.start)
                    output_right.append(replacement.end)
            else:
                source_position = position + output_deltas[position]
                output_left.append(source_position)
                output_right.append(source_position)

        return cls(
            source_length,
            output_length,
            tuple(source_left),
            tuple(source_right),
            tuple(output_left),
            tuple(output_right),
            edits,
        )

    @classmethod
    def from_boundaries(
        cls,
        source_length: int,
        output_length: int,
        source_left: tuple[int, ...],
        source_right: tuple[int, ...],
        output_left: tuple[int, ...],
        output_right: tuple[int, ...],
        edits: tuple[MappedEdit, ...] = (),
    ) -> OffsetMap:
        return cls(
            source_length,
            output_length,
            source_left,
            source_right,
            output_left,
            output_right,
            edits,
        )

    def source_to_output(self, position: int, *, bias: str = "left") -> int:
        _validate_bias(bias)
        if position < 0 or position > self.source_length:
            raise IndexError(f"Source boundary {position} outside 0..{self.source_length}")
        return (self.source_left if bias == "left" else self.source_right)[position]

    def output_to_source(self, position: int, *, bias: str = "left") -> int:
        _validate_bias(bias)
        if position < 0 or position > self.output_length:
            raise IndexError(f"Output boundary {position} outside 0..{self.output_length}")
        return (self.output_left if bias == "left" else self.output_right)[position]

    def map_source_span(self, start: int, end: int) -> tuple[int, int]:
        return self.source_to_output(start), self.source_to_output(end, bias="right")

    def map_output_span(self, start: int, end: int) -> tuple[int, int]:
        return self.output_to_source(start), self.output_to_source(end, bias="right")

    def compose(self, following: OffsetMap) -> OffsetMap:
        """Compose this map with a map whose source is this map's output."""
        if self.output_length != following.source_length:
            raise ValueError("Cannot compose maps with mismatched coordinates")
        source_left = tuple(
            following.source_to_output(value, bias="left") for value in self.source_left
        )
        source_right = tuple(
            following.source_to_output(value, bias="right") for value in self.source_right
        )
        output_left = tuple(
            self.output_to_source(value, bias="left") for value in following.output_left
        )
        output_right = tuple(
            self.output_to_source(value, bias="right") for value in following.output_right
        )
        return self.from_boundaries(
            self.source_length,
            following.output_length,
            source_left,
            source_right,
            output_left,
            output_right,
            self.edits + following.edits,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_length": self.source_length,
            "output_length": self.output_length,
            "source_left": list(self.source_left),
            "source_right": list(self.source_right),
            "output_left": list(self.output_left),
            "output_right": list(self.output_right),
            "edits": [
                {
                    "source_start": edit.source_start,
                    "source_end": edit.source_end,
                    "output_start": edit.output_start,
                    "output_end": edit.output_end,
                    "source": edit.source,
                    "replacement": edit.replacement,
                    "stage": edit.stage,
                    "language": edit.language,
                    "kind": edit.kind,
                    "rule": edit.rule,
                }
                for edit in self.edits
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OffsetMap:
        """Reconstruct a serialized map for debugging and diagnostics."""
        edits = tuple(MappedEdit(**item) for item in data.get("edits", ()))
        return cls(
            int(data["source_length"]),
            int(data["output_length"]),
            tuple(int(value) for value in data["source_left"]),
            tuple(int(value) for value in data["source_right"]),
            tuple(int(value) for value in data["output_left"]),
            tuple(int(value) for value in data["output_right"]),
            edits,
        )


def apply_replacements(
    source: str,
    replacements: tuple[Replacement, ...],
    *,
    stage: str,
) -> tuple[str, tuple[MappedEdit, ...], OffsetMap]:
    """Apply ordered replacements and return output, edits, and a map."""
    _validate_replacements(len(source), replacements)
    output: list[str] = []
    mapped: list[MappedEdit] = []
    cursor = 0
    output_length = 0
    for replacement in replacements:
        output.append(source[cursor : replacement.start])
        output_length += replacement.start - cursor
        output_start = output_length
        output.append(replacement.text)
        output_length += len(replacement.text)
        mapped.append(
            MappedEdit(
                source_start=replacement.start,
                source_end=replacement.end,
                output_start=output_start,
                output_end=output_length,
                source=source[replacement.start : replacement.end],
                replacement=replacement.text,
                stage=stage,
                language=replacement.language,
                kind=replacement.kind,
                rule=replacement.rule,
            )
        )
        cursor = replacement.end
    output.append(source[cursor:])
    result = "".join(output)
    offset_map = OffsetMap.from_replacements(
        len(source), replacements, output_length=len(result), edits=tuple(mapped)
    )
    return result, tuple(mapped), offset_map


def replacements_from_diff(before: str, after: str, stage: str) -> tuple[Replacement, ...]:
    """Turn a deterministic stage diff into ordered replacements."""
    matcher = SequenceMatcher(a=before, b=after, autojunk=False)
    return tuple(
        Replacement(start, end, after[replacement_start:replacement_end], kind=stage)
        for operation, start, end, replacement_start, replacement_end in matcher.get_opcodes()
        if operation != "equal"
    )


def _validate_replacements(source_length: int, replacements: tuple[Replacement, ...]) -> None:
    previous_end = 0
    for replacement in replacements:
        replacement.validate(source_length)
        if replacement.start < previous_end:
            raise ValueError("Overlapping replacements are not allowed")
        previous_end = replacement.end


def _precompute_replacement_positions(
    source_length: int,
    replacements: tuple[Replacement, ...],
    output_length: int,
) -> tuple[
    tuple[_ReplacementPosition, ...],
    tuple[int, ...],
    tuple[int, ...],
]:
    """Precompute replacement coordinates and cumulative coordinate deltas."""
    strict_events = [0] * (source_length + 1)
    inclusive_events = [0] * (source_length + 1)
    for replacement in replacements:
        delta = len(replacement.text) - (replacement.end - replacement.start)
        inclusive_events[replacement.end] += delta
        if replacement.start < replacement.end:
            strict_events[replacement.end] += delta
        elif replacement.end < source_length:
            strict_events[replacement.end + 1] += delta

    source_deltas = _prefix_sums(strict_events)
    inclusive_deltas = _prefix_sums(inclusive_events)
    positions = tuple(
        _ReplacementPosition(replacement, replacement.start + source_deltas[replacement.start])
        for replacement in replacements
    )

    output_events = [0] * (output_length + 1)
    for position in positions:
        delta = len(position.replacement.text) - (
            position.replacement.end - position.replacement.start
        )
        if position.output_end <= output_length:
            output_events[position.output_end] += -delta
    output_deltas = _prefix_sums(output_events)
    return positions, inclusive_deltas, output_deltas


def _prefix_sums(events: list[int]) -> tuple[int, ...]:
    total = 0
    result: list[int] = []
    for event in events:
        total += event
        result.append(total)
    return tuple(result)


def _validate_bias(bias: str) -> None:
    if bias not in {"left", "right"}:
        raise ValueError("bias must be 'left' or 'right'")


def resolve_replacements(
    replacements: tuple[Replacement, ...],
    *,
    source_length: int,
) -> tuple[Replacement, ...]:
    """Select the highest-priority non-overlapping replacement candidates."""
    for replacement in replacements:
        replacement.validate(source_length)
    ranked = sorted(
        enumerate(replacements),
        key=lambda item: (
            -(_replacement_priority(item[1]) + item[1].specificity),
            item[1].start,
            -(item[1].end - item[1].start),
            item[0],
        ),
    )
    selected: list[Replacement] = []
    for _, candidate in ranked:
        if any(
            candidate.start < existing.end and existing.start < candidate.end
            for existing in selected
        ):
            continue
        selected.append(candidate)
    return tuple(sorted(selected, key=lambda item: (item.start, item.end)))


def _replacement_priority(replacement: Replacement) -> int:
    """Return the documented semantic precedence for candidate conflicts."""
    rule = replacement.rule or ""
    from .precedence import priority_for_rule

    centralized = priority_for_rule(rule)
    if centralized != 20:
        # Local specificity remains a tie-breaker, never a way for a generic
        # recognizer to outrank a named semantic family.
        return centralized * 100
    if rule in {
        "sequence.uuid",
        "sequence.ipv4",
        "sequence.mac",
        "sequence.iban",
        "sequence.isbn",
        "sequence.exchange-rate",
        "sequence.url",
        "sequence.email",
    }:
        return 100
    if rule in {
        "sequence.coordinate",
        "sequence.formula",
        "sequence.compound-unit",
        "sequence.percent",
        "sequence.currency",
        "sequence.currency-magnitude",
        "sequence.biology",
        "sequence.biomedical",
        "sequence.height",
        "sequence.postal",
    }:
        return 90
    if rule in {"sequence.legal", "sequence.sports", "sequence.address"}:
        return 80
    if rule in {"sequence.year-range"}:
        return 76
    if rule.endswith(".date-range") or rule.endswith(".time-range"):
        return 75
    if rule.endswith(".date") or rule.endswith(".time") or rule == "sequence.roman":
        return 70
    if rule in {
        "sequence.fraction",
        "sequence.phone",
        "sequence.version",
        "sequence.hashtag",
        "sequence.mention",
        "sequence.social-hashtag",
        "sequence.social-mention",
        "sequence.numeric-range",
    }:
        return 60
    if ".currency" in rule or ".quantity" in rule or "temperature" in rule:
        return 50
    if rule in {"sequence.acronym", "sequence.ticker"}:
        return 40
    if rule in {"sequence.product", "sequence.plate", "sequence.music"}:
        return 60
    if rule == "sequence.math":
        return 65
    return 0


def convert_abbr_replacements(
    replacements: Iterable[ExpansionReplacement],
    *,
    language: str | None = None,
) -> tuple[Replacement, ...]:
    """Convert exact abbr2words replacements to Spokenform replacements.

    The dependency records are already aligned to the text they received. Keep
    that coordinate system and carry their semantic metadata directly instead
    of reconstructing edits from the expanded text.
    """
    converted: list[Replacement] = []
    for item in replacements:
        text = item.text
        source_surface = item.matched_text
        # Policy A keeps canonical unit identity in the structured stage;
        # lexical mapping carries only source-aligned text and rule provenance.
        # The consumed abbreviation marker belongs to the source span. Do not
        # duplicate it in generated speech when the expansion text includes it.
        if item.kind == "abbreviation" and source_surface.endswith(".") and text.endswith("."):
            text = text[:-1]
        if item.kind == "abbreviation":
            base = (language or "").replace("-", "_").split("_", 1)[0].casefold()
            if base in {"es", "it"} and source_surface[:1].isupper() and text[:1].islower():
                text = text[:1].upper() + text[1:]
            elif base == "fr" and source_surface.casefold() == "m." and text[:1].isupper():
                text = text[:1].lower() + text[1:]
        converted.append(
            Replacement(
                start=item.start,
                end=item.end,
                text=text,
                kind=item.kind,
                language=item.language or language,
                rule=item.rule_id,
            )
        )
    return tuple(converted)


def compose_source_replacements(
    source_text: str,
    output_text: str,
    stages: tuple[PreparationStage, ...],
    stage_maps: tuple[OffsetMap, ...],
) -> tuple[SourceReplacement, ...]:
    """Project stage-local edits into original-source/final-output space.

    A later edit inside text generated by an earlier stage is merged with its
    parent source span. The resulting replacement therefore describes the
    complete final output for that source span instead of exposing stage-local
    coordinates under a global name.
    """
    prefix = OffsetMap.identity(len(source_text))
    projected: list[SourceReplacement] = []
    for index, stage in enumerate(stages):
        suffix = OffsetMap.identity(len(stage.after))
        for following in stage_maps[index + 1 :]:
            suffix = suffix.compose(following)
        for edit in stage.mapped_edits:
            source_start = prefix.output_to_source(edit.source_start, bias="left")
            source_end = prefix.output_to_source(edit.source_end, bias="right")
            output_start = suffix.source_to_output(edit.output_start, bias="left")
            output_end = suffix.source_to_output(edit.output_end, bias="right")
            projected.append(
                SourceReplacement(
                    source_start=source_start,
                    source_end=source_end,
                    output_start=output_start,
                    output_end=output_end,
                    source=source_text[source_start:source_end],
                    replacement=output_text[output_start:output_end],
                    stages=(stage.name,),
                    language=edit.language,
                    kind=edit.kind,
                    rule=edit.rule,
                )
            )
        prefix = prefix.compose(stage_maps[index])

    projected.sort(key=lambda item: (item.source_start, item.source_end, item.output_start))
    merged: list[SourceReplacement] = []
    for item in projected:
        if not merged or (
            item.source_start > merged[-1].source_end and item.output_start > merged[-1].output_end
        ):
            merged.append(item)
            continue
        previous = merged[-1]
        source_start = min(previous.source_start, item.source_start)
        source_end = max(previous.source_end, item.source_end)
        output_start = min(previous.output_start, item.output_start)
        output_end = max(previous.output_end, item.output_end)
        stages_seen = tuple(dict.fromkeys((*previous.stages, *item.stages)))
        merged[-1] = SourceReplacement(
            source_start=source_start,
            source_end=source_end,
            output_start=output_start,
            output_end=output_end,
            source=source_text[source_start:source_end],
            replacement=output_text[output_start:output_end],
            stages=stages_seen,
            language=previous.language if previous.language == item.language else None,
            kind=previous.kind if previous.kind == item.kind else "composed",
            rule=previous.rule if previous.rule == item.rule else None,
        )
    return tuple(merged)


__all__ = [
    "OffsetMap",
    "Replacement",
    "apply_replacements",
    "convert_abbr_replacements",
    "compose_source_replacements",
    "replacements_from_diff",
    "resolve_replacements",
]
