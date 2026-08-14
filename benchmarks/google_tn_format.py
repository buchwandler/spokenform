"""Parser and source-surface models for Google TN-compatible TSV data."""

from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TextIO

IDENTITY_SENTINELS = frozenset({"<self>", "sil", "<sil>"})
SURFACE_POLICY = "field_join_v1"


@dataclass(frozen=True, slots=True)
class GoogleTNRow:
    """One upstream Google TN written/spoken row."""

    semiotic_class: str
    written: str
    spoken: str
    source_line: int
    source_start: int
    source_end: int

    @property
    def expected_spoken(self) -> str:
        """Return the forward-TN target, treating identity markers as written."""
        return self.written if self.spoken in IDENTITY_SENTINELS else self.spoken

    @property
    def is_identity(self) -> bool:
        return self.spoken in IDENTITY_SENTINELS


@dataclass(frozen=True, slots=True)
class GoogleTNCase:
    """A sentence assembled from one Google TN TSV sentence."""

    language: str
    source_file: str
    shard: int | None
    sentence_index: int
    line_start: int
    line_end: int
    rows: tuple[GoogleTNRow, ...]
    original_text: str
    normalized_text: str

    @property
    def case_id(self) -> str:
        language = _safe_component(self.language)
        if self.shard is not None:
            return f"{language}:{self.shard:03d}:{self.sentence_index:06d}"
        stem = _safe_component(Path(self.source_file).stem or "source")
        return f"{language}:{stem}:{self.sentence_index:06d}"

    @property
    def has_normalization(self) -> bool:
        return any(not row.is_identity for row in self.rows)


def project_spoken(spoken: str, written: str) -> str:
    """Project a row target for forward text normalization."""
    return written if spoken in IDENTITY_SENTINELS else spoken


def _safe_component(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", value).strip("-") or "source"


def _read_lines(source: str | Path | TextIO | Iterable[str]) -> Iterator[str]:
    if isinstance(source, (str, Path)):
        with Path(source).open("r", encoding="utf-8", newline="") as handle:
            yield from handle
        return
    yield from source


def _assemble_rows(rows: tuple[GoogleTNRow, ...]) -> tuple[tuple[GoogleTNRow, ...], str, str]:
    source_parts: list[str] = []
    target_parts: list[str] = []
    offset = 0
    assembled: list[GoogleTNRow] = []
    for index, row in enumerate(rows):
        if index:
            offset += 1
        start = offset
        offset += len(row.written)
        source_parts.append(row.written)
        target_parts.append(row.expected_spoken)
        assembled.append(replace(row, source_start=start, source_end=offset))
    return tuple(assembled), " ".join(source_parts), " ".join(target_parts)


def iter_tsv_sentences(
    source: str | Path | TextIO | Iterable[str], *, strict: bool = True
) -> Iterator[tuple[GoogleTNRow, ...]]:
    """Yield strictly framed Google TN sentences from a UTF-8 text source.

    The parser intentionally preserves unknown classes and does not interpret
    markup or apply NeMo preprocessing.  ``source`` may be a filesystem path,
    an open text stream, or an iterable of already decoded physical lines.
    """
    pending: list[GoogleTNRow] = []
    for line_number, raw_line in enumerate(_read_lines(source), 1):
        line = raw_line.rstrip("\r\n")
        fields = line.split("\t")
        if len(fields) == 2 and tuple(field.strip() for field in fields) == ("<eos>", "<eos>"):
            if not pending:
                raise ValueError(f"line {line_number}: empty Google TN sentence")
            assembled, _, _ = _assemble_rows(tuple(pending))
            yield assembled
            pending.clear()
            continue
        if len(fields) != 3:
            raise ValueError(
                f"line {line_number}: expected 3 tab-separated fields or <eos>\\t<eos>, "
                f"got {len(fields)}"
            )
        semiotic_class, written, spoken = (field.strip() for field in fields)
        if not semiotic_class:
            raise ValueError(f"line {line_number}: semiotic class must not be empty")
        pending.append(
            GoogleTNRow(
                semiotic_class=semiotic_class,
                written=written,
                spoken=spoken,
                source_line=line_number,
                source_start=0,
                source_end=0,
            )
        )
    if pending:
        message = "unterminated Google TN sentence at EOF"
        if strict:
            raise ValueError(message)
        assembled, _, _ = _assemble_rows(tuple(pending))
        yield assembled


def assemble_case(
    rows: Iterable[GoogleTNRow],
    *,
    language: str = "en",
    source_file: str = "",
    shard: int | None = None,
    sentence_index: int = 0,
    line_start: int | None = None,
    line_end: int | None = None,
) -> GoogleTNCase:
    """Build a case and exact source surface from parsed rows."""
    normalized_rows, original_text, normalized_text = _assemble_rows(tuple(rows))
    if not normalized_rows:
        raise ValueError("cannot assemble an empty Google TN case")
    return GoogleTNCase(
        language=language,
        source_file=source_file,
        shard=shard,
        sentence_index=sentence_index,
        line_start=line_start if line_start is not None else normalized_rows[0].source_line,
        line_end=line_end if line_end is not None else normalized_rows[-1].source_line,
        rows=normalized_rows,
        original_text=original_text,
        normalized_text=normalized_text,
    )


__all__ = [
    "GoogleTNCase",
    "GoogleTNRow",
    "IDENTITY_SENTINELS",
    "SURFACE_POLICY",
    "assemble_case",
    "iter_tsv_sentences",
    "project_spoken",
]
