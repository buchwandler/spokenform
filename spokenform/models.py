"""Public data models for prepared speech text."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .mapping import OffsetMap


@dataclass(frozen=True, slots=True)
class TokenAnnotation:
    """Provider-neutral lexical annotation aligned to one input text."""

    start: int
    end: int
    text: str | None = None
    pos: str | None = None
    tag: str | None = None
    lemma: str | None = None
    language: str | None = None


@dataclass(frozen=True, slots=True)
class TextEdit:
    """One edit in a normalization stage.

    Offsets are relative to the input of that stage. This keeps every edit exact
    without pretending that all stages still share the original coordinate space.
    """

    start: int
    end: int
    source: str
    replacement: str
    stage: str


@dataclass(frozen=True, slots=True)
class PreparationStage:
    """The before/after text and edits produced by one stage."""

    name: str
    before: str
    after: str
    edits: tuple[TextEdit, ...] = ()
    mapped_edits: tuple[MappedEdit, ...] = ()

    @property
    def changed(self) -> bool:
        """Return whether this stage changed the text."""
        return self.before != self.after


@dataclass(frozen=True, slots=True)
class MappedEdit:
    """A replacement with source and output coordinates."""

    source_start: int
    source_end: int
    output_start: int
    output_end: int
    source: str
    replacement: str
    stage: str
    language: str | None = None


@dataclass(frozen=True, slots=True)
class PreparedText:
    """Readable spoken text with normalization provenance."""

    source_text: str
    clean_text: str
    spoken_text: str
    language: str
    stages: tuple[PreparationStage, ...] = ()
    mapped_edits: tuple[MappedEdit, ...] = ()
    offset_map: "OffsetMap | None" = None
    warnings: tuple[str, ...] = ()

    @property
    def text(self) -> str:
        """Alias for :attr:`spoken_text`."""
        return self.spoken_text

    @property
    def changed(self) -> bool:
        """Return whether preparation changed the source text."""
        return self.source_text != self.spoken_text

    @property
    def edits(self) -> tuple[TextEdit, ...]:
        """Return the ordered edits from every stage."""
        return tuple(edit for stage in self.stages for edit in stage.edits)

    def render_changes(self) -> str:
        """Render a compact, human-readable stage report."""
        lines = [f"Language: {self.language}", f"Source:   {self.source_text}"]
        for stage in self.stages:
            status = "changed" if stage.changed else "unchanged"
            lines.append(f"[{stage.name}] {status}")
            if stage.changed:
                lines.append(f"  {stage.before}")
                lines.append(f"  → {stage.after}")
        lines.append(f"Spoken:   {self.spoken_text}")
        if self.warnings:
            lines.append("Warnings:")
            lines.extend(f"  - {warning}" for warning in self.warnings)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        return asdict(self)


def diff_edits(before: str, after: str, stage: str) -> tuple[TextEdit, ...]:
    """Build a deterministic edit script between two stage values."""
    if before == after:
        return ()

    edits: list[TextEdit] = []
    matcher = SequenceMatcher(a=before, b=after, autojunk=False)
    for operation, start, end, replacement_start, replacement_end in matcher.get_opcodes():
        if operation == "equal":
            continue
        edits.append(
            TextEdit(
                start=start,
                end=end,
                source=before[start:end],
                replacement=after[replacement_start:replacement_end],
                stage=stage,
            )
        )
    return tuple(edits)


def make_stage(name: str, before: str, after: str) -> PreparationStage:
    """Create a stage and its deterministic edit script."""
    edits = diff_edits(before, after, name)
    from .mapping import apply_replacements, replacements_from_diff

    replacements = replacements_from_diff(before, after, name)
    _, mapped_edits, _ = apply_replacements(before, replacements, stage=name)
    return PreparationStage(
        name=name,
        before=before,
        after=after,
        edits=edits,
        mapped_edits=mapped_edits,
    )
