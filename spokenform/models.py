"""Public data models for prepared speech text."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any

from .protection import ProtectedSpan

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
    kind: str = "replacement"
    rule: str | None = None


@dataclass(frozen=True, slots=True)
class SourceReplacement:
    """A replacement projected from original source to final output."""

    source_start: int
    source_end: int
    output_start: int
    output_end: int
    source: str
    replacement: str
    stages: tuple[str, ...]
    language: str | None = None
    kind: str = "replacement"
    rule: str | None = None


@dataclass(frozen=True, slots=True)
class PreparedText:
    """Readable spoken text with normalization provenance."""

    source_text: str
    clean_text: str
    spoken_text: str
    language: str
    stages: tuple[PreparationStage, ...] = ()
    mapped_edits: tuple[MappedEdit, ...] = ()
    source_replacements: tuple[SourceReplacement, ...] = ()
    protected_spans: tuple[ProtectedSpan, ...] = ()
    offset_map: OffsetMap | None = None
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

    @property
    def source_edits(self) -> tuple[SourceReplacement, ...]:
        """Return edits in the documented source-to-final coordinate space."""
        return self.source_replacements

    @property
    def replacements(self) -> tuple[SourceReplacement, ...]:
        """Stable adapter alias for composed source replacements."""
        return self.source_replacements

    @property
    def stage_report(self) -> str:
        """Return the diagnostic stage report for adapter logging."""
        return self.render_changes()

    def map_source_span(self, start: int, end: int) -> tuple[int, int]:
        """Map an original source span to final spoken-text coordinates."""
        if self.offset_map is None:
            raise ValueError("No offset map is available")
        return self.offset_map.map_source_span(start, end)

    def map_output_span(self, start: int, end: int) -> tuple[int, int]:
        """Map a final spoken-text span back to original source coordinates."""
        if self.offset_map is None:
            raise ValueError("No offset map is available")
        return self.offset_map.map_output_span(start, end)

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
        payload = asdict(self)
        payload["source_edits"] = payload["source_replacements"]
        payload["stage_report"] = self.stage_report
        return payload

    def to_adapter_dict(self) -> dict[str, Any]:
        """Return the stable kokorog2p-facing result projection."""
        return {
            "spoken_text": self.spoken_text,
            "language": self.language,
            "source_replacements": [asdict(item) for item in self.source_replacements],
            "offset_map": self.offset_map.to_dict() if self.offset_map is not None else None,
            "warnings": list(self.warnings),
            "protected_spans": [asdict(item) for item in self.protected_spans],
            "stage_report": self.stage_report,
        }


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
