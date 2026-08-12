"""Pinned Proteno data discovery, validation, and projection."""

from __future__ import annotations

import hashlib
import html
import pickle
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.request import urlopen

PROTENO_REPOSITORY = "https://github.com/amazon-science/proteno"
PROTENO_RAW_BASE = "https://raw.githubusercontent.com/amazon-science/proteno"
PROTENO_COMMIT = "8839501abaf50eeccbe21a2397cefa118eae9660"
PROTENO_DATASET_COMMIT = PROTENO_COMMIT
PROTENO_LANGUAGES = ("en", "es")
PROTENO_LANGUAGE_DIRS = {"en": "English", "es": "Spanish"}
PROTENO_TO_SPOKENFORM = {"en": "en_US", "es": "es"}
PROTENO_LICENSE = "CC BY-SA 3.0 Unported"
PROTENO_DATASET_COUNTS = {"en": 24_760, "es": 4_791}


@dataclass(frozen=True, slots=True)
class ProtenoFile:
    """Immutable metadata for one file in the pinned upstream snapshot."""

    relative_path: str
    git_blob_sha: str
    size: int


PROTENO_FILES: dict[str, dict[str, ProtenoFile]] = {
    "en": {
        "unnorm": ProtenoFile(
            "data/English/unnorm_list.pkl",
            "f49e38f4a8b6238221b0ddb54e955bda8df2257d",
            1_793_844,
        ),
        "norm": ProtenoFile(
            "data/English/norm_list.pkl",
            "fd55268f042da5698fbb430270efdc00a53d0169",
            1_805_607,
        ),
        "license": ProtenoFile(
            "data/English/LICENSE.txt",
            "604209a804632b6e5274005a22293976d07c3099",
            22_240,
        ),
    },
    "es": {
        "unnorm": ProtenoFile(
            "data/Spanish/unnorm_list.pkl",
            "58c613ce5be2af193983b39a07875fa17e4b58b4",
            928_166,
        ),
        "norm": ProtenoFile(
            "data/Spanish/norm_list.pkl",
            "cbe40d2b3a90c1e069b72e7fc8069c0d8e519808",
            1_185_832,
        ),
        "license": ProtenoFile(
            "data/Spanish/LICENSE.txt",
            "604209a804632b6e5274005a22293976d07c3099",
            22_240,
        ),
    },
}


@dataclass(frozen=True, slots=True)
class ProtenoCase:
    """One projected Proteno sentence pair.

    ``index`` is the one-based absolute position in the upstream list.  It is
    deliberately not renumbered after language, split, case, or limit filters.
    """

    proteno_language: str
    index: int
    split: str
    source_tokens: tuple[str, ...]
    original_text: str
    normalized_text: str
    has_normalization: bool

    @property
    def case_id(self) -> str:
        return f"{self.proteno_language}:{self.index:05d}"

    @property
    def case_kind(self) -> str:
        return "normalization" if self.has_normalization else "identity"


@dataclass(frozen=True, slots=True)
class ProtenoExclusion:
    """A local, auditable record for data not evaluated as Spokenform output."""

    id: str
    language: str
    index: int
    split: str
    reason: str
    diagnostic: str

    def as_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "language": self.language,
            "index": self.index,
            "split": self.split,
            "reason": self.reason,
            "diagnostic": self.diagnostic,
        }


def selected_languages(language: str | None = None) -> tuple[str, ...]:
    """Return both supported languages or one validated language."""
    if language is None:
        return PROTENO_LANGUAGES
    if language not in PROTENO_LANGUAGES:
        raise ValueError(f"Unsupported Proteno language: {language}")
    return (language,)


def cache_path(cache_dir: Path | str = ".cache/proteno") -> Path:
    """Return the commit-scoped cache root."""
    return Path(cache_dir) / PROTENO_COMMIT


def data_path(
    language: str, kind: str = "unnorm", cache_dir: Path | str = ".cache/proteno"
) -> Path:
    """Return one validated cache path."""
    if language not in PROTENO_LANGUAGES:
        raise ValueError(f"Unsupported Proteno language: {language}")
    if kind not in PROTENO_FILES[language]:
        raise ValueError(f"Unsupported Proteno file kind: {kind}")
    return (
        cache_path(cache_dir)
        / PROTENO_LANGUAGE_DIRS[language]
        / Path(PROTENO_FILES[language][kind].relative_path).name
    )


def _raw_url(file: ProtenoFile) -> str:
    return f"{PROTENO_RAW_BASE}/{PROTENO_COMMIT}/{file.relative_path}"


def git_blob_sha(payload: bytes) -> str:
    """Calculate the SHA of a Git blob containing ``payload``."""
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def verify_payload(payload: bytes, metadata: ProtenoFile) -> None:
    """Reject bytes that do not exactly match pinned Git object metadata."""
    actual_size = len(payload)
    if actual_size != metadata.size:
        raise ValueError(
            f"Proteno file size mismatch for {metadata.relative_path}: "
            f"expected {metadata.size}, got {actual_size}"
        )
    actual_sha = git_blob_sha(payload)
    if actual_sha != metadata.git_blob_sha:
        raise ValueError(
            f"Proteno Git blob SHA mismatch for {metadata.relative_path}: "
            f"expected {metadata.git_blob_sha}, got {actual_sha}"
        )


def _download(file: ProtenoFile, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(_raw_url(file), timeout=60) as response:  # noqa: S310 - pinned HTTPS URL
        payload = response.read()
    verify_payload(payload, file)
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


def ensure_data(
    languages: tuple[str, ...],
    *,
    cache_dir: Path | str = ".cache/proteno",
    offline: bool = False,
    accept_license: bool = False,
    refresh: bool = False,
) -> Path:
    """Ensure selected data and duplicated upstream licenses exist locally."""
    flat_languages: tuple[str, ...] = tuple(
        selected_languages(language)[0] for language in languages
    )
    root = cache_path(cache_dir)
    needed: list[tuple[str, str]] = []
    for language in flat_languages:
        for kind in ("unnorm", "norm", "license"):
            destination = data_path(language, kind, cache_dir)
            if refresh or not destination.is_file():
                needed.append((language, kind))
                continue
            try:
                verify_payload(destination.read_bytes(), PROTENO_FILES[language][kind])
            except ValueError:
                destination.unlink(missing_ok=True)
                needed.append((language, kind))
    if needed and offline:
        absent = ", ".join(f"{language}/{kind}" for language, kind in needed)
        raise FileNotFoundError(f"Offline Proteno cache is missing: {absent}")
    if needed and not accept_license:
        raise PermissionError(
            "Proteno data is CC BY-SA 3.0 Unported; pass --accept-license before downloading."
        )
    for language, kind in needed:
        _download(PROTENO_FILES[language][kind], data_path(language, kind, cache_dir))
    return root


class _PrimitiveUnpickler(pickle.Unpickler):
    """Unpickler that refuses globals and persistent references."""

    def find_class(self, module: str, name: str) -> object:
        if (module, name) in {
            ("numpy.core.multiarray", "scalar"),
            ("numpy", "dtype"),
        }:
            try:
                if module == "numpy.core.multiarray":
                    from numpy.core.multiarray import scalar

                    return scalar
                from numpy import dtype

                return dtype
            except ImportError as exc:
                raise pickle.UnpicklingError(
                    "Pinned English Proteno data requires NumPy to decode numpy.str_ values"
                ) from exc
        raise pickle.UnpicklingError(f"Proteno pickle attempted class loading: {module}.{name}")

    def persistent_load(self, pid: object) -> object:
        raise pickle.UnpicklingError("Persistent pickle references are not allowed")


def _load_pickle(path: Path) -> object:
    try:
        with path.open("rb") as handle:
            return _primitiveize(_PrimitiveUnpickler(handle).load())
    except (EOFError, pickle.UnpicklingError) as exc:
        raise ValueError(f"Unable to safely load Proteno pickle {path}: {exc}") from exc


def _primitiveize(value: object) -> object:
    """Convert the one observed upstream NumPy string scalar to plain text."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return (
            str(value)
            if type(value).__module__ == "numpy" and type(value).__name__ == "str_"
            else value
        )
    if isinstance(value, list):
        return [_primitiveize(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_primitiveize(item) for item in value)
    raise pickle.UnpicklingError(
        f"Proteno pickle contained unsupported primitive value: {type(value).__name__}"
    )


def _string_sequence(value: object, *, path: Path, label: str) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise ValueError(f"{label} entry in {path} must be a sequence of strings")
    return tuple(value)


def _validate_source(value: object, path: Path) -> tuple[tuple[str, ...], ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"Proteno source payload {path} must be a list or tuple")
    return tuple(_string_sequence(item, path=path, label="source") for item in value)


def _validate_normalized(value: object, path: Path) -> tuple[str | tuple[str, ...], ...]:
    if not isinstance(value, (list, tuple)):
        raise ValueError(f"Proteno normalized payload {path} must be a list or tuple")
    normalized: list[str | tuple[str, ...]] = []
    for item in value:
        if isinstance(item, str):
            normalized.append(item)
        else:
            normalized.append(_string_sequence(item, path=path, label="normalized"))
    return tuple(normalized)


def load_pair(
    language: str,
    *,
    cache_dir: Path | str = ".cache/proteno",
    validate_count: bool = True,
) -> tuple[tuple[tuple[str, ...], ...], tuple[str | tuple[str, ...], ...]]:
    """Load and validate one source/target pair from the local cache."""
    source_path = data_path(language, "unnorm", cache_dir)
    target_path = data_path(language, "norm", cache_dir)
    source = _validate_source(_load_pickle(source_path), source_path)
    target = _validate_normalized(_load_pickle(target_path), target_path)
    if len(source) != len(target):
        raise ValueError(
            f"Proteno pair length mismatch for {language}: source count {len(source)}, "
            f"target count {len(target)}; source={source_path}; target={target_path}"
        )
    if validate_count and len(source) != PROTENO_DATASET_COUNTS[language]:
        raise ValueError(
            f"Proteno documented count mismatch for {language}: "
            f"expected {PROTENO_DATASET_COUNTS[language]}, got {len(source)}; "
            f"source={source_path}; target={target_path}"
        )
    return source, target


class _SpanishProjectionParser(HTMLParser):
    """Strictly project the released Spanish annotation markup."""

    _known = {"error", "lang"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._stack: list[tuple[str, str | None]] = []
        self._parts: list[str] = []

    def _inside(self, tag: str) -> bool:
        return any(name == tag for name, _ in self._stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        if tag not in self._known:
            raise ValueError(f"Unknown Spanish Proteno tag: <{tag}>")
        if self._inside(tag):
            raise ValueError(f"Nested Spanish Proteno <{tag}> tags are not supported")
        values = {key: value for key, value in attrs}
        if tag == "error":
            if values.get("what") is None:
                raise ValueError("Spanish Proteno <error> tag is missing required what")
            if any(key != "what" for key in values):
                raise ValueError("Spanish Proteno <error> tag has unknown attributes")
            what = html.unescape(values["what"] or "")
            self._stack.append((tag, what))
            if not self._inside("lang"):
                self._parts.append(what)
        else:
            self._stack.append((tag, None))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        if not self._stack or self._stack[-1][0] != tag:
            raise ValueError(f"Malformed Spanish Proteno markup: unexpected </{tag}>")
        self._stack.pop()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        raise ValueError(f"Self-closing Spanish Proteno tag is not supported: <{tag}/>")

    def handle_data(self, data: str) -> None:
        if self._inside("lang") or self._inside("error"):
            return
        self._parts.append(data)

    def finish(self) -> str:
        if self._stack:
            raise ValueError(f"Malformed Spanish Proteno markup: unclosed <{self._stack[-1][0]}>")
        return minimal_text(" ".join(self._parts))


def project_spanish(text: str) -> str:
    """Project Spanish ``error`` and ``lang`` annotations to expected speech."""
    parser = _SpanishProjectionParser()
    try:
        parser.feed(text)
        parser.close()
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError(f"Malformed Spanish Proteno markup: {exc}") from exc
    return parser.finish()


_NO_SPACE_BEFORE = frozenset(".,;:!?%)]}»”’")
_NO_SPACE_AFTER = frozenset("([{«“")
_NO_SPACE_AROUND = frozenset({"/", "-", "–", "—", "'", "’"})
_CURRENCY = frozenset("$€£")


def detokenize(tokens: tuple[str, ...] | list[str]) -> str:
    """Conservatively reconstruct written surface text from Proteno tokens."""
    pieces: list[str] = []
    for position, token in enumerate(tokens):
        if not token:
            continue
        if not pieces:
            pieces.append(token)
            continue
        previous = pieces[-1][-1:]
        next_token = next((candidate for candidate in tokens[position + 1 :] if candidate), "")
        decimal_or_time = token in {".", ":"} and previous.isdigit() and next_token[:1].isdigit()
        after_decimal = (
            previous in {".", ":"} and pieces[-1][-2:-1].isdigit() and token[:1].isdigit()
        )
        no_space = (
            token in _NO_SPACE_BEFORE
            or token in _NO_SPACE_AROUND
            or previous in _NO_SPACE_AFTER
            or previous in _NO_SPACE_AROUND
            or previous in _CURRENCY
            or decimal_or_time
            or after_decimal
            or (token == "." and len(previous) == 1 and previous.isalpha())
            or (previous == "." and len(token) == 1 and token.isalpha())
        )
        if no_space:
            pieces[-1] += token
        else:
            pieces.append(token)
    return minimal_text(" ".join(pieces))


def minimal_text(text: str) -> str:
    """Normalize only surrounding and repeated whitespace."""
    return " ".join(text.split())


_URL_RE = re.compile(r"(?:https?://|www\.)\S+|\b[\w.-]+\.[A-Za-z]{2,}(?:/\S*)?", re.IGNORECASE)
_CONTROL_MARKERS = frozenset({"<self>", "</self>", "<copy>", "</copy>"})


def _check_english_markers(text: str) -> None:
    for marker in _CONTROL_MARKERS:
        if marker in text.casefold():
            raise ValueError(f"Unhandled English Proteno control marker: {marker}")


def _normalized_text(language: str, value: str | tuple[str, ...]) -> str:
    if isinstance(value, str):
        text = minimal_text(value)
    else:
        text = detokenize(value)
    if language == "en":
        _check_english_markers(text)
    else:
        text = project_spanish(text)
    return text


def split_name(index: int, total: int) -> str:
    """Return the documented floor-60%-training partition for a row index."""
    train_end = int(total * 0.60)
    return "train" if index < train_end else "test"


def split_policy(total_by_language: dict[str, int]) -> dict[str, object]:
    return {
        "train_fraction": 0.6,
        "rounding": "floor",
        "train_end": {language: int(total * 0.60) for language, total in total_by_language.items()},
    }


def load_cases_with_exclusions(
    languages: tuple[str, ...],
    *,
    cache_dir: Path | str = ".cache/proteno",
    split: str = "all",
    case_id: str | None = None,
    limit: int | None = None,
    validate_count: bool = True,
) -> tuple[tuple[ProtenoCase, ...], tuple[ProtenoExclusion, ...]]:
    """Load projected cases and explicit adapter exclusions in stable order."""
    if split not in {"all", "train", "test"}:
        raise ValueError(f"Unsupported Proteno split: {split}")
    if limit is not None and limit < 0:
        raise ValueError("Proteno limit must be non-negative")
    cases: list[ProtenoCase] = []
    exclusions: list[ProtenoExclusion] = []
    for language in selected_languages() if not languages else tuple(languages):
        selected_languages(language)
        source, target = load_pair(language, cache_dir=cache_dir, validate_count=validate_count)
        total = len(source)
        for zero_index, (source_tokens, target_value) in enumerate(
            zip(source, target, strict=True)
        ):
            index = zero_index + 1
            row_split = split_name(zero_index, total)
            identifier = f"{language}:{index:05d}"
            if split != "all" and split != row_split:
                continue
            if case_id is not None and identifier != case_id:
                continue
            original = detokenize(source_tokens)
            try:
                expected = _normalized_text(language, target_value)
            except ValueError as exc:
                exclusions.append(
                    ProtenoExclusion(
                        identifier, language, index, row_split, "adapter_error", str(exc)
                    )
                )
                continue
            if _URL_RE.search(original) or _URL_RE.search(expected):
                exclusions.append(
                    ProtenoExclusion(
                        identifier,
                        language,
                        index,
                        row_split,
                        "upstream_ignored_url",
                        "URL or web address remains after projection",
                    )
                )
                continue
            cases.append(
                ProtenoCase(
                    language,
                    index,
                    row_split,
                    source_tokens,
                    original,
                    expected,
                    minimal_text(original) != minimal_text(expected),
                )
            )
            if limit is not None and len(cases) >= limit:
                # The input order is deterministic, so this does not affect IDs.
                break
        if limit is not None and len(cases) >= limit:
            break
    return tuple(cases), tuple(exclusions)


def load_cases(
    languages: tuple[str, ...],
    *,
    cache_dir: Path | str = ".cache/proteno",
    split: str = "all",
    case_id: str | None = None,
    limit: int | None = None,
    validate_count: bool = True,
) -> tuple[ProtenoCase, ...]:
    """Load projected cases, discarding only explicit adapter exclusions."""
    cases, _ = load_cases_with_exclusions(
        languages,
        cache_dir=cache_dir,
        split=split,
        case_id=case_id,
        limit=limit,
        validate_count=validate_count,
    )
    return cases


__all__ = [
    "PROTENO_COMMIT",
    "PROTENO_DATASET_COMMIT",
    "PROTENO_DATASET_COUNTS",
    "PROTENO_FILES",
    "PROTENO_LANGUAGE_DIRS",
    "PROTENO_LANGUAGES",
    "PROTENO_LICENSE",
    "PROTENO_RAW_BASE",
    "PROTENO_REPOSITORY",
    "PROTENO_TO_SPOKENFORM",
    "ProtenoCase",
    "ProtenoExclusion",
    "ProtenoFile",
    "cache_path",
    "data_path",
    "detokenize",
    "ensure_data",
    "git_blob_sha",
    "load_cases",
    "load_cases_with_exclusions",
    "load_pair",
    "minimal_text",
    "project_spanish",
    "selected_languages",
    "split_name",
    "split_policy",
    "verify_payload",
]
