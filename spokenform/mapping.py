"""Deterministic source/output offset mapping for normalization stages."""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any

from .models import MappedEdit


@dataclass(frozen=True, slots=True)
class Replacement:
    """One non-overlapping replacement in input coordinates."""

    start: int
    end: int
    text: str
    kind: str = "replacement"
    language: str | None = None
    rule: str | None = None

    def validate(self, source_length: int) -> None:
        if self.start < 0 or self.end < self.start or self.end > source_length:
            raise ValueError(f"Invalid replacement range ({self.start}, {self.end})")


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
        source_left: list[int] = []
        source_right: list[int] = []
        for position in range(source_length + 1):
            containing = next(
                (
                    replacement
                    for replacement in replacements
                    if replacement.start <= position <= replacement.end
                    and replacement.start < replacement.end
                ),
                None,
            )
            insertion = next(
                (
                    replacement
                    for replacement in replacements
                    if replacement.start == replacement.end == position
                ),
                None,
            )
            if insertion is not None:
                output_start = _output_start(position, replacements)
                source_left.append(output_start)
                source_right.append(output_start + len(insertion.text))
            elif containing is not None:
                output_start = _output_start(containing.start, replacements)
                output_end = output_start + len(containing.text)
                if position == containing.end:
                    source_left.append(output_end)
                    source_right.append(output_end)
                else:
                    source_left.append(output_start)
                    source_right.append(output_end)
            else:
                mapped = position + sum(
                    len(replacement.text) - (replacement.end - replacement.start)
                    for replacement in replacements
                    if replacement.end <= position
                )
                source_left.append(mapped)
                source_right.append(mapped)

        output_left: list[int] = []
        output_right: list[int] = []
        for position in range(output_length + 1):
            containing = next(
                (
                    replacement
                    for replacement in replacements
                    if _output_start(replacement.start, replacements)
                    <= position
                    <= _output_start(replacement.start, replacements) + len(replacement.text)
                ),
                None,
            )
            if containing is not None:
                output_start = _output_start(containing.start, replacements)
                output_end = output_start + len(containing.text)
                if position == output_end:
                    output_left.append(containing.end)
                    output_right.append(containing.end)
                else:
                    output_left.append(containing.start)
                    output_right.append(containing.end)
            else:
                source_position = position
                for replacement in replacements:
                    output_end = _output_start(replacement.start, replacements) + len(
                        replacement.text
                    )
                    if output_end <= position:
                        source_position += (replacement.end - replacement.start) - len(
                            replacement.text
                        )
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


def _output_start(source_position: int, replacements: tuple[Replacement, ...]) -> int:
    return source_position + sum(
        len(replacement.text) - (replacement.end - replacement.start)
        for replacement in replacements
        if replacement.end < source_position
        or (replacement.end == source_position and replacement.start < source_position)
    )


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
        key=lambda item: (item[1].start, -(item[1].end - item[1].start), item[0]),
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


__all__ = [
    "OffsetMap",
    "Replacement",
    "apply_replacements",
    "replacements_from_diff",
    "resolve_replacements",
]
