"""Local data discovery and provenance for the Google TN benchmark."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

from .google_tn_format import GoogleTNCase, SURFACE_POLICY, assemble_case, iter_tsv_sentences

GOOGLE_TN_REPOSITORY = "https://github.com/rwsproat/text-normalization-data"
GOOGLE_TN_LANGUAGE = "en"
GOOGLE_TN_TO_SPOKENFORM = {"en": "en_US"}
GOOGLE_TN_TEST_FILE = "output-00099-of-00100"
GOOGLE_TN_TEST_LINE_LIMIT = 100002
GOOGLE_TN_SPLITS = ("test", "test-full", "all")
_SHARD_RE = re.compile(r"^output-(?P<shard>\d+)-of-(?P<count>\d+)$")


def shard_number(path: str | Path) -> int | None:
    """Return a numeric Google output shard, if the filename has one."""
    match = _SHARD_RE.match(Path(path).name)
    return int(match["shard"]) if match else None


def discover_source_files(data_dir: str | Path, *, split: str = "test") -> tuple[Path, ...]:
    """Discover source files for a supported local split."""
    if split not in GOOGLE_TN_SPLITS:
        raise ValueError(f"unsupported split {split!r}; choose one of {GOOGLE_TN_SPLITS}")
    root = Path(data_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Google TN data directory does not exist: {root}")
    files = tuple(sorted(path for path in root.rglob("output-*") if path.is_file()))
    if split in {"test", "test-full"}:
        selected = tuple(path for path in files if path.name == GOOGLE_TN_TEST_FILE)
        if not selected:
            raise FileNotFoundError(f"Google TN test shard not found: {root / GOOGLE_TN_TEST_FILE}")
        return selected
    if not files:
        raise FileNotFoundError(f"no Google TN output shards found under {root}")
    return files


def _limited_lines(handle: Iterable[str], line_limit: int | None) -> Iterator[str]:
    for line_number, line in enumerate(handle, 1):
        if line_limit is not None and line_number > line_limit:
            break
        yield line


def iter_cases(
    data_dir: str | Path,
    *,
    language: str = GOOGLE_TN_LANGUAGE,
    split: str = "test",
    limit: int | None = None,
    semiotic_class: str | None = None,
    case_id: str | None = None,
) -> Iterator[GoogleTNCase]:
    """Stream cases while applying filters after stable source indexing."""
    if language not in GOOGLE_TN_TO_SPOKENFORM:
        raise ValueError(f"unsupported Google TN language {language!r}")
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative")
    line_limit = GOOGLE_TN_TEST_LINE_LIMIT if split == "test" else None
    yielded = 0
    for source_path in discover_source_files(data_dir, split=split):
        shard = shard_number(source_path)
        with source_path.open("r", encoding="utf-8", newline="") as handle:
            sentences = iter_tsv_sentences(_limited_lines(handle, line_limit))
            for sentence_index, rows in enumerate(sentences):
                case = assemble_case(
                    rows,
                    language=language,
                    source_file=source_path.name,
                    shard=shard,
                    sentence_index=sentence_index,
                )
                if semiotic_class is not None and not any(
                    row.semiotic_class == semiotic_class for row in case.rows
                ):
                    continue
                if case_id is not None and case.case_id != case_id:
                    continue
                yield case
                yielded += 1
                if limit is not None and yielded >= limit:
                    return


def file_sha256(path: str | Path) -> str:
    """Hash the exact source file used by a benchmark run."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_metadata(
    path: str | Path,
    *,
    split: str,
    selected_line_start: int = 1,
    selected_line_end: int | None = None,
) -> dict[str, object]:
    """Return deterministic file-oriented provenance for one source shard."""
    source_path = Path(path)
    if selected_line_end is None:
        selected_line_end = GOOGLE_TN_TEST_LINE_LIMIT if split == "test" else None
    return {
        "dataset_name": "Google TN",
        "dataset_source": GOOGLE_TN_REPOSITORY,
        "language": GOOGLE_TN_LANGUAGE,
        "source_file": source_path.name,
        "source_file_bytes": source_path.stat().st_size,
        "source_file_sha256": file_sha256(source_path),
        "selected_line_start": selected_line_start,
        "selected_line_end": selected_line_end,
        "split": split,
        "shard": shard_number(source_path),
        "surface_policy": SURFACE_POLICY,
        "special_value_policy": "<self>, sil, and <sil> project to written",
    }


__all__ = [
    "GOOGLE_TN_LANGUAGE",
    "GOOGLE_TN_REPOSITORY",
    "GOOGLE_TN_SPLITS",
    "GOOGLE_TN_TEST_FILE",
    "GOOGLE_TN_TEST_LINE_LIMIT",
    "GOOGLE_TN_TO_SPOKENFORM",
    "discover_source_files",
    "file_sha256",
    "iter_cases",
    "shard_number",
    "source_metadata",
]
