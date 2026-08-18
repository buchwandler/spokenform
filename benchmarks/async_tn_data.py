"""Pinned data acquisition and parsing for the Async TN benchmark."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

SOURCE_REPO = "https://huggingface.co/spaces/async-vocie-ai/text-to-speech-normalization-benchmark"
SOURCE_COMMIT = "516dfbf54c8f85db865b65de4272b1f4280ad1dd"
SOURCE_LICENSE = "Apache-2.0"
SOURCE_RAW_BASE = f"{SOURCE_REPO}/resolve/{SOURCE_COMMIT}"

ENGLISH_SUITE = "english"
MULTILINGUAL_SUITE = "multilingual"
SUITES = (ENGLISH_SUITE, MULTILINGUAL_SUITE)

ENGLISH_SOURCE_FILE = "data/sentences.json"
MULTILINGUAL_SOURCE_FILE = "data/multilingual-sentences.json"
REFERENCE_FILES = {
    ENGLISH_SUITE: ("data/overview.json", "data/categories.json"),
    MULTILINGUAL_SUITE: (
        "data/multilingual-overview.json",
        "data/multilingual-categories.json",
    ),
}
SOURCE_FILES = (
    ENGLISH_SOURCE_FILE,
    MULTILINGUAL_SOURCE_FILE,
    "data/overview.json",
    "data/categories.json",
    "data/multilingual-overview.json",
    "data/multilingual-categories.json",
)
SOURCE_LANGUAGES = ("en", "de", "es", "fr", "it", "pt")
SOURCE_TO_SPOKENFORM = {
    "en": "en_US",
    "de": "de",
    "es": "es",
    "fr": "fr",
    "it": "it",
    "pt": "pt",
}
ASYNC_TN_TO_SPOKENFORM = SOURCE_TO_SPOKENFORM


@dataclass(frozen=True, slots=True)
class AsyncTNUnit:
    """One source annotation with validated source coordinates."""

    index: int
    text: str
    category: str
    source_start: int
    source_end: int
    span_source: str = "resolved-exact"

    @property
    def unit_id(self) -> str:
        raise AttributeError("unit_id requires a case_id; use make_unit_id")

    def as_dict(self) -> dict[str, object]:
        return {
            "index": self.index,
            "text": self.text,
            "category": self.category,
            "source_start": self.source_start,
            "source_end": self.source_end,
            "span_source": self.span_source,
        }


@dataclass(frozen=True, slots=True)
class AsyncTNCase:
    """One evaluable English or multilingual sentence."""

    case_id: str
    suite: str
    source_language: str
    spokenform_language: str
    original_text: str
    normalized_text: str
    units: tuple[AsyncTNUnit, ...]
    categories: tuple[str, ...]
    source_sentence_id: str | None = None

    def unit_id(self, index: int) -> str:
        return make_unit_id(self.case_id, index)

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "suite": self.suite,
            "source_language": self.source_language,
            "spokenform_language": self.spokenform_language,
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "units": [unit.as_dict() for unit in self.units],
            "categories": list(self.categories),
            "source_sentence_id": self.source_sentence_id,
        }


@dataclass(frozen=True, slots=True)
class AsyncTNExclusion:
    """A source record that is retained for explicit quarantine accounting."""

    case_id: str
    suite: str
    language: str
    reason: str
    detail: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "case_id": self.case_id,
            "suite": self.suite,
            "language": self.language,
            "reason": self.reason,
            "detail": self.detail,
        }


def make_case_id(suite: str, source_id: object, language: str | None = None) -> str:
    """Build a stable ID that is independent of selection and iteration filters."""
    if suite == ENGLISH_SUITE:
        return f"english:{source_id}"
    if suite == MULTILINGUAL_SUITE and language is not None:
        return f"multilingual:{language}:{source_id}"
    raise ValueError(f"unsupported suite or missing language: {suite!r}")


def make_unit_id(case_id: str, index: int) -> str:
    return f"{case_id}:unit:{index}"


def spokenform_language(source_language: str) -> str:
    try:
        return SOURCE_TO_SPOKENFORM[source_language]
    except KeyError as exc:
        raise ValueError(f"unsupported Async TN language {source_language!r}") from exc


def cache_path(cache_dir: Path | str = ".cache/async-tn") -> Path:
    return Path(cache_dir) / SOURCE_COMMIT


def data_path(relative_path: str, *, cache_dir: Path | str = ".cache/async-tn") -> Path:
    if relative_path not in SOURCE_FILES:
        raise ValueError(f"unsupported Async TN source file {relative_path!r}")
    return cache_path(cache_dir) / relative_path


def _raw_url(relative_path: str) -> str:
    return f"{SOURCE_RAW_BASE}/{relative_path}"


def file_sha256(path: Path | str) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_json(payload: bytes, relative_path: str) -> object:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in Async TN source {relative_path}") from exc
    if relative_path.endswith("sentences.json") and not isinstance(value, list):
        raise ValueError(f"Async TN sentence source must be a JSON list: {relative_path}")
    return value


def _download(relative_path: str, destination: Path) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(_raw_url(relative_path), timeout=60) as response:  # noqa: S310
        payload = response.read()
    _validate_json(payload, relative_path)
    with NamedTemporaryFile(
        mode="wb",
        dir=destination.parent,
        prefix=f"{destination.name}.",
        suffix=".part",
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(payload)
    try:
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {"sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)}


def _metadata_path(cache_dir: Path | str) -> Path:
    return cache_path(cache_dir) / "metadata.json"


def _load_metadata(cache_dir: Path | str) -> dict[str, object]:
    path = _metadata_path(cache_dir)
    if not path.is_file():
        return {
            "benchmark": "async_tn",
            "source_repo": SOURCE_REPO,
            "source_commit": SOURCE_COMMIT,
            "license": SOURCE_LICENSE,
            "files": {},
        }
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid Async TN cache metadata: {path}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("files", {}), dict):
        raise ValueError(f"invalid Async TN cache metadata: {path}")
    return value


def _write_metadata(cache_dir: Path | str, files: dict[str, dict[str, object]]) -> None:
    path = _metadata_path(cache_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "benchmark": "async_tn",
        "source_repo": SOURCE_REPO,
        "source_commit": SOURCE_COMMIT,
        "license": SOURCE_LICENSE,
        "files": dict(sorted(files.items())),
    }
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _required_files(suites: Sequence[str]) -> tuple[str, ...]:
    selected = tuple(suites)
    result: list[str] = []
    for suite in selected:
        if suite not in SUITES:
            raise ValueError(f"unsupported Async TN suite {suite!r}; choose from {SUITES}")
        result.append(ENGLISH_SOURCE_FILE if suite == ENGLISH_SUITE else MULTILINGUAL_SOURCE_FILE)
        result.extend(REFERENCE_FILES[suite])
    return tuple(dict.fromkeys(result))


def required_files(suites: Sequence[str]) -> tuple[str, ...]:
    """Return canonical source and reference files for selected suites."""
    return _required_files(suites)


def ensure_data(
    suites: Sequence[str] = SUITES,
    *,
    cache_dir: Path | str = ".cache/async-tn",
    offline: bool = False,
    refresh: bool = False,
) -> Path:
    """Ensure selected source and reference files exist in the commit cache."""
    if offline and refresh:
        raise ValueError("--offline and --refresh cannot be used together")
    root = cache_path(cache_dir)
    root.mkdir(parents=True, exist_ok=True)
    metadata = _load_metadata(cache_dir)
    recorded = metadata.get("files", {})
    files: dict[str, dict[str, object]] = {
        str(key): dict(value) for key, value in recorded.items() if isinstance(value, dict)
    }
    required = _required_files(suites)
    missing: list[str] = []
    for relative_path in required:
        path = data_path(relative_path, cache_dir=cache_dir)
        if refresh or not path.is_file():
            missing.append(relative_path)
            continue
        actual = {"sha256": file_sha256(path), "bytes": path.stat().st_size}
        expected = files.get(relative_path)
        if expected is not None and expected != actual:
            raise ValueError(f"Async TN cache hash mismatch for {relative_path}")
        _validate_json(path.read_bytes(), relative_path)
        files[relative_path] = actual
    if missing and offline:
        raise FileNotFoundError("Offline Async TN cache is missing: " + ", ".join(missing))
    for relative_path in missing:
        files[relative_path] = _download(
            relative_path, data_path(relative_path, cache_dir=cache_dir)
        )
    _write_metadata(cache_dir, files)
    return root


def _record_id(payload: Mapping[str, object], position: int, *, multilingual: bool = False) -> str:
    for key in ("row_index", "sentence_id", "id", "index"):
        value = payload.get(key)
        if isinstance(value, (str, int)) and str(value):
            return str(value)
    return f"row-{position}"


def _unit_payloads(payload: Mapping[str, object]) -> object:
    return payload.get("units")


def _find_occurrences(source: str, text: str, start: int) -> list[tuple[int, int]]:
    result: list[tuple[int, int]] = []
    cursor = start
    while True:
        found = source.find(text, cursor)
        if found < 0:
            return result
        result.append((found, found + len(text)))
        cursor = found + max(len(text), 1)


def _resolve_units(
    original: str, raw_units: object, *, case_id: str, suite: str, language: str
) -> tuple[tuple[AsyncTNUnit, ...], AsyncTNExclusion | None]:
    if not isinstance(raw_units, list) or not raw_units:
        return (), AsyncTNExclusion(case_id, suite, language, "missing-unit-annotations")
    resolved: list[AsyncTNUnit] = []
    cursor = 0
    for index, raw_unit in enumerate(raw_units):
        if not isinstance(raw_unit, dict) or not isinstance(raw_unit.get("text"), str):
            return (), AsyncTNExclusion(
                case_id, suite, language, "invalid-source-record", f"invalid unit at index {index}"
            )
        text = raw_unit["text"]
        category = raw_unit.get("norm_category", raw_unit.get("category"))
        if not isinstance(category, str) or not category:
            return (), AsyncTNExclusion(
                case_id,
                suite,
                language,
                "invalid-source-record",
                f"missing category at unit {index}",
            )
        start = raw_unit.get("start", raw_unit.get("source_start"))
        end = raw_unit.get("end", raw_unit.get("source_end"))
        span_source = "resolved-exact"
        if isinstance(start, int) and isinstance(end, int):
            if 0 <= start <= end <= len(original) and original[start:end] == text:
                resolved_start, resolved_end = start, end
                span_source = "upstream"
            else:
                candidates = _find_occurrences(original, text, cursor)
                if len(candidates) != 1:
                    reason = (
                        "unit-source-span-not-found"
                        if not candidates
                        else "unit-source-span-ambiguous"
                    )
                    return (), AsyncTNExclusion(case_id, suite, language, reason)
                resolved_start, resolved_end = candidates[0]
        else:
            candidates = _find_occurrences(original, text, cursor)
            if not candidates:
                return (), AsyncTNExclusion(case_id, suite, language, "unit-source-span-not-found")
            remaining_same_text = sum(
                isinstance(next_unit, dict) and next_unit.get("text") == text
                for next_unit in raw_units[index:]
            )
            if len(candidates) > remaining_same_text:
                return (), AsyncTNExclusion(case_id, suite, language, "unit-source-span-ambiguous")
            resolved_start, resolved_end = candidates[0]
        if resolved and resolved_start < resolved[-1].source_end:
            return (), AsyncTNExclusion(case_id, suite, language, "unit-source-span-overlap")
        resolved.append(
            AsyncTNUnit(index, text, category, resolved_start, resolved_end, span_source)
        )
        cursor = resolved_end
    return tuple(resolved), None


def _parse_case(
    payload: object, *, suite: str, language: str, position: int, source_id: str | None = None
) -> tuple[AsyncTNCase | None, AsyncTNExclusion | None]:
    if not isinstance(payload, dict):
        case_id = make_case_id(
            suite, source_id or f"row-{position}", language if suite == MULTILINGUAL_SUITE else None
        )
        return None, AsyncTNExclusion(
            case_id, suite, language, "invalid-source-record", "record is not an object"
        )
    source_id = source_id or _record_id(payload, position)
    case_id = make_case_id(suite, source_id, language if suite == MULTILINGUAL_SUITE else None)
    original = payload.get("original_text")
    normalized = payload.get("normalized_text")
    if not isinstance(original, str) or not isinstance(normalized, str):
        return None, AsyncTNExclusion(
            case_id, suite, language, "invalid-source-record", "missing sentence text"
        )
    units, exclusion = _resolve_units(
        original, _unit_payloads(payload), case_id=case_id, suite=suite, language=language
    )
    if exclusion is not None:
        return None, exclusion
    raw_categories = payload.get("categories")
    categories = (
        tuple(str(value) for value in raw_categories if isinstance(value, str))
        if isinstance(raw_categories, list)
        else ()
    )
    if not categories:
        categories = tuple(dict.fromkeys(unit.category for unit in units))
    return (
        AsyncTNCase(
            case_id,
            suite,
            language,
            spokenform_language(language),
            original,
            normalized,
            units,
            categories,
            source_id,
        ),
        None,
    )


def parse_english(payload: object) -> tuple[tuple[AsyncTNCase, ...], tuple[AsyncTNExclusion, ...]]:
    """Parse English sentence JSON while quarantining malformed records."""
    if not isinstance(payload, list):
        raise ValueError("English Async TN source must be a JSON list")
    cases: list[AsyncTNCase] = []
    exclusions: list[AsyncTNExclusion] = []
    for position, record in enumerate(payload, 1):
        case, exclusion = _parse_case(record, suite=ENGLISH_SUITE, language="en", position=position)
        if case is not None:
            cases.append(case)
        if exclusion is not None:
            exclusions.append(exclusion)
    return tuple(cases), tuple(exclusions)


def parse_multilingual(
    payload: object, *, languages: Iterable[str] | None = None
) -> tuple[tuple[AsyncTNCase, ...], tuple[AsyncTNExclusion, ...]]:
    """Parse sentence records containing a language map."""
    if not isinstance(payload, list):
        raise ValueError("Multilingual Async TN source must be a JSON list")
    selected = set(languages) if languages is not None else set(SOURCE_LANGUAGES)
    cases: list[AsyncTNCase] = []
    exclusions: list[AsyncTNExclusion] = []
    for position, record in enumerate(payload, 1):
        if not isinstance(record, dict) or not isinstance(record.get("languages"), dict):
            source_id = (
                _record_id(record, position) if isinstance(record, dict) else f"row-{position}"
            )
            exclusions.append(
                AsyncTNExclusion(
                    make_case_id(MULTILINGUAL_SUITE, source_id, "unknown"),
                    MULTILINGUAL_SUITE,
                    "unknown",
                    "invalid-source-record",
                    "missing languages map",
                )
            )
            continue
        source_id = _record_id(record, position, multilingual=True)
        for language, language_payload in record["languages"].items():
            if language not in SOURCE_TO_SPOKENFORM:
                exclusions.append(
                    AsyncTNExclusion(
                        make_case_id(MULTILINGUAL_SUITE, source_id, language),
                        MULTILINGUAL_SUITE,
                        language,
                        "unsupported-language",
                    )
                )
                continue
            if language not in selected:
                continue
            case, exclusion = _parse_case(
                language_payload,
                suite=MULTILINGUAL_SUITE,
                language=language,
                position=position,
                source_id=source_id,
            )
            if case is not None:
                cases.append(case)
            if exclusion is not None:
                exclusions.append(exclusion)
    return tuple(cases), tuple(exclusions)


def load_cases(
    suite: str, *, cache_dir: Path | str = ".cache/async-tn", languages: Iterable[str] | None = None
) -> tuple[tuple[AsyncTNCase, ...], tuple[AsyncTNExclusion, ...]]:
    """Load parsed cases from a commit-scoped cache."""
    if suite not in SUITES:
        raise ValueError(f"unsupported Async TN suite {suite!r}")
    path = data_path(
        ENGLISH_SOURCE_FILE if suite == ENGLISH_SUITE else MULTILINGUAL_SOURCE_FILE,
        cache_dir=cache_dir,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return (
        parse_english(payload)
        if suite == ENGLISH_SUITE
        else parse_multilingual(payload, languages=languages)
    )


def filter_cases(
    cases: Iterable[AsyncTNCase],
    *,
    language: str | None = None,
    category: str | None = None,
    case_id: str | None = None,
    limit: int | None = None,
) -> tuple[AsyncTNCase, ...]:
    """Apply filters after parsing, preserving source-derived IDs."""
    if limit is not None and limit < 0:
        raise ValueError("limit must be non-negative")
    selected = [
        case
        for case in cases
        if (language is None or case.source_language == language)
        and (
            category is None or category.casefold() in {item.casefold() for item in case.categories}
        )
        and (case_id is None or case.case_id == case_id)
    ]
    return tuple(selected[:limit] if limit is not None else selected)


def iter_cases(
    suite: str,
    *,
    cache_dir: Path | str = ".cache/async-tn",
    language: str | None = None,
    category: str | None = None,
    case_id: str | None = None,
    limit: int | None = None,
) -> Iterator[AsyncTNCase]:
    cases, _ = load_cases(suite, cache_dir=cache_dir, languages=(language,) if language else None)
    yield from filter_cases(
        cases, language=language, category=category, case_id=case_id, limit=limit
    )


def source_metadata(
    cache_dir: Path | str = ".cache/async-tn",
    *,
    files: Iterable[str] | None = None,
) -> dict[str, object]:
    """Return commit and selected file-hash provenance for a populated cache."""
    metadata = _load_metadata(cache_dir)
    recorded = metadata.get("files", {})
    selected = set(files) if files is not None else None
    file_metadata = {
        str(path): value for path, value in recorded.items() if selected is None or path in selected
    }
    return {
        "benchmark": "async_tn",
        "source_repo": SOURCE_REPO,
        "source_commit": SOURCE_COMMIT,
        "license": SOURCE_LICENSE,
        "files": file_metadata,
    }


__all__ = [
    "ASYNC_TN_TO_SPOKENFORM",
    "AsyncTNCase",
    "AsyncTNExclusion",
    "AsyncTNUnit",
    "ENGLISH_SOURCE_FILE",
    "ENGLISH_SUITE",
    "MULTILINGUAL_SOURCE_FILE",
    "MULTILINGUAL_SUITE",
    "REFERENCE_FILES",
    "SOURCE_COMMIT",
    "SOURCE_FILES",
    "SOURCE_LANGUAGES",
    "SOURCE_LICENSE",
    "SOURCE_REPO",
    "SOURCE_TO_SPOKENFORM",
    "SUITES",
    "cache_path",
    "data_path",
    "ensure_data",
    "required_files",
    "file_sha256",
    "filter_cases",
    "iter_cases",
    "load_cases",
    "make_case_id",
    "make_unit_id",
    "parse_english",
    "parse_multilingual",
    "source_metadata",
    "spokenform_language",
]
