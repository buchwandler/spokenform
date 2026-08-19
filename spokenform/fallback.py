"""Conservative orthographic rendering for residual sequence-shaped spans."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from .config import SequenceFallbackMode
from .mapping import Replacement
from .sequences import SequenceRenderPolicy, render_sequence

_SEQUENCE_FALLBACK_RE = re.compile(
    r"(?<!\w)(?:[A-Za-z0-9]+(?:[-–_./:][A-Za-z0-9]+)+|[A-Z]{2,}|[A-Za-z]*\d[A-Za-z0-9]*)(?!\w)"
)

FallbackTraceStatus = Literal["preserved", "spelled"]
SemanticStatus = Literal["unclaimed", "suppressed"]


@dataclass(frozen=True, slots=True)
class SequenceFallbackTrace:
    """Diagnostic decision for one residual sequence-shaped source span."""

    rule: str
    start: int
    end: int
    source: str
    status: FallbackTraceStatus
    semantic_status: SemanticStatus
    action: SequenceFallbackMode
    rendered_text: str | None = None


def _render(value: str, *, language: str) -> str:
    return render_sequence(
        value.replace("–", "-"),
        language=language,
        policy=SequenceRenderPolicy(
            alpha_mode="grapheme_spaced",
            digit_mode="digitwise",
            punctuation_mode="name",
        ),
    )


def iter_sequence_fallback_replacements(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return conservative orthographic replacements for eligible spans."""
    blocked = tuple(protected_ranges)
    replacements: list[Replacement] = []
    for match in _SEQUENCE_FALLBACK_RE.finditer(text):
        if any(match.start() < end and start < match.end() for start, end in blocked):
            continue
        rendered = _render(match.group(0), language=language)
        if rendered == match.group(0):
            continue
        replacements.append(
            Replacement(
                match.start(),
                match.end(),
                rendered,
                "fallback",
                language,
                "fallback.sequence",
            )
        )
    return tuple(replacements)


def trace_sequence_fallback(
    text: str,
    *,
    language: str,
    mode: SequenceFallbackMode = SequenceFallbackMode.PRESERVE,
    protected_ranges: Iterable[tuple[int, int]] = (),
    suppressed_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[SequenceFallbackTrace, ...]:
    """Report residual fallback decisions without assigning semantic ownership."""
    if not isinstance(mode, SequenceFallbackMode):
        mode = SequenceFallbackMode(mode)
    protected = tuple(protected_ranges)
    suppressed = tuple(suppressed_ranges)
    records: list[SequenceFallbackTrace] = []
    for match in _SEQUENCE_FALLBACK_RE.finditer(text):
        if any(match.start() < end and start < match.end() for start, end in protected):
            continue
        rendered = _render(match.group(0), language=language)
        if rendered == match.group(0):
            continue
        semantic_status: SemanticStatus = (
            "suppressed"
            if any(match.start() < end and start < match.end() for start, end in suppressed)
            else "unclaimed"
        )
        spelled = mode is SequenceFallbackMode.SPELL
        records.append(
            SequenceFallbackTrace(
                rule="fallback.sequence",
                start=match.start(),
                end=match.end(),
                source=match.group(0),
                status="spelled" if spelled else "preserved",
                semantic_status=semantic_status,
                action=mode,
                rendered_text=rendered if spelled else None,
            )
        )
    return tuple(records)


__all__ = [
    "FallbackTraceStatus",
    "SemanticStatus",
    "SequenceFallbackTrace",
    "iter_sequence_fallback_replacements",
    "trace_sequence_fallback",
]
