"""Pinned source acquisition and release caching for Spokenform Gold."""

from __future__ import annotations

import importlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from types import ModuleType
from urllib.request import urlopen

SPOKENFORM_GOLD_REPOSITORY = "https://github.com/buchwandler/spokenform-gold"
SPOKENFORM_GOLD_COMMIT = "7b9107a4193475a05f8d2c1eb41e833c9d2c08c5"
SPOKENFORM_GOLD_RELEASE_VERSION = "0.2.0-exp"
SPOKENFORM_GOLD_POLICY_CONTRACT = "v0.3.0"
SPOKENFORM_GOLD_ARCHIVE_URL = (
    f"https://codeload.github.com/buchwandler/spokenform-gold/zip/{SPOKENFORM_GOLD_COMMIT}"
)

_REQUIRED_FILES = (
    "spokenform_gold/benchmark.py",
    "spokenform_gold/release.py",
    "spokenform_gold/scoring.py",
    "data/corpus.jsonl",
    "schemas",
    "sources/manifest.json",
    "taxonomy",
    "pyproject.toml",
    "LICENSE",
    "LICENSE-DATA",
)


def cache_path(cache_dir: Path | str = ".cache/spokenform-gold") -> Path:
    return Path(cache_dir) / SPOKENFORM_GOLD_COMMIT


def source_path(cache_dir: Path | str = ".cache/spokenform-gold") -> Path:
    return cache_path(cache_dir) / "source"


def release_path(cache_dir: Path | str = ".cache/spokenform-gold") -> Path:
    return cache_path(cache_dir) / "release"


def metadata_path(cache_dir: Path | str = ".cache/spokenform-gold") -> Path:
    return cache_path(cache_dir) / "metadata.json"


def _download(url: str, destination: Path) -> None:
    if not url.startswith("https://"):
        raise ValueError("Spokenform Gold source URL must use HTTPS")
    with urlopen(url, timeout=60) as response:  # noqa: S310 - exact pinned HTTPS URL
        payload = response.read()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.part")
    temporary.write_bytes(payload)
    temporary.replace(destination)


def _safe_extract(archive: Path, destination: Path) -> Path:
    """Extract a GitHub ZIP after validating every member path."""
    destination.mkdir(parents=True, exist_ok=True)
    top_levels: set[str] = set()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            name = member.filename.replace("\\", "/")
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or not path.parts:
                raise ValueError(f"unsafe Spokenform Gold archive path: {member.filename!r}")
            mode = member.external_attr >> 16
            if mode and (mode & 0o170000) == 0o120000:
                raise ValueError(f"symlink in Spokenform Gold archive: {member.filename!r}")
            top_levels.add(path.parts[0])
            target = destination.joinpath(*path.parts)
            resolved_destination = destination.resolve()
            if (
                resolved_destination not in target.resolve().parents
                and target.resolve() != resolved_destination
            ):
                raise ValueError(f"archive path escapes destination: {member.filename!r}")
        if len(top_levels) != 1:
            raise ValueError("Spokenform Gold archive must contain one repository root")
        bundle.extractall(destination)  # paths were validated above
    return destination / next(iter(top_levels))


def _validate_source_tree(root: Path) -> None:
    missing = [relative for relative in _REQUIRED_FILES if not (root / relative).exists()]
    if missing:
        raise ValueError("Spokenform Gold source is incomplete; missing " + ", ".join(missing))


def load_gold_module(module_name: str, *, source_root: Path) -> ModuleType:
    """Import a Gold module from one validated repository checkout."""
    _validate_source_tree(source_root)
    for name in tuple(sys.modules):
        if name == "spokenform_gold" or name.startswith("spokenform_gold."):
            del sys.modules[name]
    source_text = str(source_root)
    sys.path[:] = [item for item in sys.path if item != source_text]
    sys.path.insert(0, source_text)
    importlib.invalidate_caches()
    return importlib.import_module(module_name)


def _verify_release(release_root: Path, *, source_root: Path) -> dict[str, object]:
    benchmark = load_gold_module("spokenform_gold.benchmark", source_root=source_root)
    verification = benchmark.verify_release(release_root)
    manifest = verification.get("manifest", {})
    if manifest.get("benchmark_version") != SPOKENFORM_GOLD_RELEASE_VERSION:
        raise ValueError(
            "cached Spokenform Gold release has unexpected benchmark version: "
            f"{manifest.get('benchmark_version')!r}"
        )
    if manifest.get("format") != "v2":
        raise ValueError(
            f"cached Spokenform Gold release is not a v2 corpus release: {manifest.get('format')!r}"
        )
    if manifest.get("schema_version") != "2.0.0":
        raise ValueError(
            "cached Spokenform Gold release has unexpected schema version: "
            f"{manifest.get('schema_version')!r}"
        )
    if manifest.get("corpus_file") != "corpus.jsonl":
        raise ValueError(
            "cached Spokenform Gold release has unexpected corpus file: "
            f"{manifest.get('corpus_file')!r}"
        )
    if manifest.get("record_files") != ["corpus.jsonl"]:
        raise ValueError(
            "cached Spokenform Gold release has unexpected record files: "
            f"{manifest.get('record_files')!r}"
        )
    if manifest.get("split_registry") is not None:
        raise ValueError("cached Spokenform Gold v2 release must not have a split registry")
    return verification


def _metadata(*, verification: dict[str, object], gold_version: str) -> dict[str, object]:
    manifest = verification.get("manifest", {})
    return {
        "benchmark": "spokenform_gold",
        "repository": SPOKENFORM_GOLD_REPOSITORY,
        "source_commit": SPOKENFORM_GOLD_COMMIT,
        "archive_url": SPOKENFORM_GOLD_ARCHIVE_URL,
        "release_version": SPOKENFORM_GOLD_RELEASE_VERSION,
        "spokenform_policy_contract": SPOKENFORM_GOLD_POLICY_CONTRACT,
        "gold_package_version": gold_version,
        "release_manifest_hash": verification["manifest_hash"],
        "release_format": manifest.get("format"),
        "gold_schema_version": manifest.get("schema_version"),
        "corpus_file": manifest.get("corpus_file"),
    }


def _read_metadata(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"invalid Spokenform Gold cache metadata: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"invalid Spokenform Gold cache metadata: {path}")
    return payload


def _cache_is_valid(root: Path) -> bool:
    if not root.is_dir() or not metadata_path(root.parent).is_file():
        return False
    source = root / "source"
    release = root / "release"
    _validate_source_tree(source)
    metadata = _read_metadata(root / "metadata.json")
    if metadata.get("source_commit") != SPOKENFORM_GOLD_COMMIT:
        return False
    if metadata.get("release_version") != SPOKENFORM_GOLD_RELEASE_VERSION:
        return False
    if not (release / "manifest.json").is_file():
        return False
    verification = _verify_release(release, source_root=source)
    return metadata.get("release_manifest_hash") == verification["manifest_hash"]


def _build_cache(target: Path, archive: Path) -> None:
    unpacked = target / "unpacked"
    source = _safe_extract(archive, unpacked)
    _validate_source_tree(source)
    materialized_source = target / "source"
    source.rename(materialized_source)
    release = target / "release"
    release_module = load_gold_module("spokenform_gold.release", source_root=materialized_source)
    release_module.build_release(
        version=SPOKENFORM_GOLD_RELEASE_VERSION,
        data_paths=[str(materialized_source / "data/corpus.jsonl")],
        out_root=release,
        maturity="experimental",
        source_manifest_path=materialized_source / "sources/manifest.json",
    )
    verification = _verify_release(release, source_root=materialized_source)
    package = load_gold_module("spokenform_gold", source_root=materialized_source)
    metadata = _metadata(
        verification=verification,
        gold_version=str(getattr(package, "__version__", "unknown")),
    )
    (target / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def ensure_data(
    *,
    cache_dir: Path | str = ".cache/spokenform-gold",
    offline: bool = False,
    refresh: bool = False,
) -> Path:
    """Ensure and return the verified local Gold release directory."""
    root = cache_path(cache_dir)
    if not refresh:
        try:
            if _cache_is_valid(root):
                return root / "release"
        except (FileNotFoundError, OSError, ValueError, ImportError):
            if offline:
                raise FileNotFoundError(
                    "Offline Spokenform Gold cache is missing or invalid for commit "
                    f"{SPOKENFORM_GOLD_COMMIT}; run online without --offline or use --refresh."
                ) from None
    if offline:
        raise FileNotFoundError(
            "Offline Spokenform Gold cache is missing for commit "
            f"{SPOKENFORM_GOLD_COMMIT}; run once online to populate it."
        )

    root.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=f".{SPOKENFORM_GOLD_COMMIT}.", dir=root.parent))
    archive = temporary_root / "source.zip"
    try:
        _download(SPOKENFORM_GOLD_ARCHIVE_URL, archive)
        _build_cache(temporary_root, archive)
        completed_root = temporary_root
        backup = root.with_name(f".{root.name}.previous")
        if backup.exists():
            shutil.rmtree(backup)
        if root.exists():
            root.replace(backup)
        completed_root.replace(root)
        if backup.exists():
            shutil.rmtree(backup)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    return root / "release"


__all__ = [
    "SPOKENFORM_GOLD_ARCHIVE_URL",
    "SPOKENFORM_GOLD_COMMIT",
    "SPOKENFORM_GOLD_RELEASE_VERSION",
    "SPOKENFORM_GOLD_REPOSITORY",
    "cache_path",
    "ensure_data",
    "load_gold_module",
    "metadata_path",
    "release_path",
    "source_path",
]
