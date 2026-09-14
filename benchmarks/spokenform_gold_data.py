"""Pinned Spokenform Gold release acquisition and verification."""

from __future__ import annotations

import hashlib
import importlib
import json
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from types import ModuleType
from urllib.request import urlopen

_PIN_PATH = Path(__file__).with_name("spokenform_gold_release.json")
RELEASE_PIN = json.loads(_PIN_PATH.read_text(encoding="utf-8"))
SPOKENFORM_GOLD_REPOSITORY = f"https://github.com/{RELEASE_PIN['repository']}"
SPOKENFORM_GOLD_TAG = str(RELEASE_PIN["tag"])
SPOKENFORM_GOLD_RELEASE_VERSION = str(RELEASE_PIN["version"])
SPOKENFORM_GOLD_ASSET = str(RELEASE_PIN["asset"])
SPOKENFORM_GOLD_ARCHIVE_SHA256 = str(RELEASE_PIN["archive_sha256"])
SPOKENFORM_GOLD_RELEASE_MANIFEST_SHA256 = str(RELEASE_PIN["release_manifest_sha256"])
SPOKENFORM_GOLD_RUNTIME_SOURCE_REF = str(RELEASE_PIN["runtime_source_ref"])
SPOKENFORM_GOLD_POLICY_CONTRACT = str(RELEASE_PIN["policy_contract"])
SPOKENFORM_GOLD_COMMIT = SPOKENFORM_GOLD_RUNTIME_SOURCE_REF
SPOKENFORM_GOLD_ARCHIVE_URL = (
    f"{SPOKENFORM_GOLD_REPOSITORY}/releases/download/{SPOKENFORM_GOLD_TAG}/{SPOKENFORM_GOLD_ASSET}"
)
SPOKENFORM_GOLD_RUNTIME_URL = (
    f"{SPOKENFORM_GOLD_REPOSITORY}/archive/refs/tags/{SPOKENFORM_GOLD_RUNTIME_SOURCE_REF}.zip"
)


_REQUIRED_FILES = (
    "spokenform_gold/benchmark.py",
    "spokenform_gold/release.py",
    "spokenform_gold/scoring.py",
    "sources/manifest.json",
    "taxonomy",
    "pyproject.toml",
    "LICENSE",
    "LICENSE-DATA",
)


def cache_path(cache_dir: Path | str = ".cache/spokenform-gold") -> Path:
    return Path(cache_dir) / "releases" / SPOKENFORM_GOLD_TAG / SPOKENFORM_GOLD_ARCHIVE_SHA256[:16]


def source_path(cache_dir: Path | str = ".cache/spokenform-gold") -> Path:
    return Path(cache_dir) / "runtime" / SPOKENFORM_GOLD_RUNTIME_SOURCE_REF


def release_path(cache_dir: Path | str = ".cache/spokenform-gold") -> Path:
    return cache_path(cache_dir) / "release"


def metadata_path(cache_dir: Path | str = ".cache/spokenform-gold") -> Path:
    return cache_path(cache_dir) / "metadata.json"


def _download(url: str, destination: Path) -> None:
    if not url.startswith("https://"):
        raise ValueError("Spokenform Gold URL must use HTTPS")
    with urlopen(url, timeout=60) as response:  # noqa: S310 - exact pinned HTTPS URL
        payload = response.read()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.part")
    temporary.write_bytes(payload)
    temporary.replace(destination)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_extract(archive: Path, destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    top_levels: set[str] = set()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            name = member.filename.replace("\\", "/")
            path = PurePosixPath(name)
            mode = member.external_attr >> 16
            if (
                path.is_absolute()
                or ".." in path.parts
                or not path.parts
                or (mode and (mode & 0o170000) == 0o120000)
            ):
                raise ValueError(f"unsafe Spokenform Gold archive path: {member.filename!r}")
            top_levels.add(path.parts[0])
            target = destination.joinpath(*path.parts)
            if (
                destination.resolve() not in target.resolve().parents
                and target.resolve() != destination.resolve()
            ):
                raise ValueError(f"archive path escapes destination: {member.filename!r}")
        if len(top_levels) != 1:
            raise ValueError("Spokenform Gold archive must contain one repository root")
        bundle.extractall(destination)
    return destination / next(iter(top_levels))


def _validate_source_tree(root: Path) -> None:
    missing = [relative for relative in _REQUIRED_FILES if not (root / relative).exists()]
    if missing:
        raise ValueError(
            "Spokenform Gold runtime source is incomplete; missing " + ", ".join(missing)
        )


def load_gold_module(module_name: str, *, source_root: Path) -> ModuleType:
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
    if SPOKENFORM_GOLD_RELEASE_MANIFEST_SHA256 != _sha256(release_root / "manifest.json"):
        raise ValueError("Spokenform Gold release manifest SHA256 does not match the pin")
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
        raise ValueError("cached Spokenform Gold release has unexpected corpus file")
    if manifest.get("record_files") != ["corpus.jsonl"]:
        raise ValueError("cached Spokenform Gold release has unexpected record files")
    if manifest.get("split_registry") is not None:
        raise ValueError("cached Spokenform Gold v2 release must not have a split registry")
    return verification


def _metadata(verification: dict[str, object], source_root: Path) -> dict[str, object]:
    manifest = verification["manifest"]
    package = load_gold_module("spokenform_gold", source_root=source_root)
    return {
        "benchmark": "spokenform_gold",
        "repository": SPOKENFORM_GOLD_REPOSITORY,
        "tag": SPOKENFORM_GOLD_TAG,
        "runtime_source_ref": SPOKENFORM_GOLD_RUNTIME_SOURCE_REF,
        "release_version": SPOKENFORM_GOLD_RELEASE_VERSION,
        "archive_sha256": SPOKENFORM_GOLD_ARCHIVE_SHA256,
        "release_manifest_hash": verification["manifest_hash"],
        "release_format": manifest.get("format"),
        "gold_schema_version": manifest.get("schema_version"),
        "corpus_file": manifest.get("corpus_file"),
        "gold_package_version": str(getattr(package, "__version__", "unknown")),
    }


def _cache_is_valid(root: Path) -> bool:
    if not root.is_dir() or not (root / "metadata.json").is_file():
        return False
    release = root / "release"
    runtime = root / "runtime"
    metadata = json.loads((root / "metadata.json").read_text(encoding="utf-8"))
    if (
        metadata.get("tag") != SPOKENFORM_GOLD_TAG
        or metadata.get("archive_sha256") != SPOKENFORM_GOLD_ARCHIVE_SHA256
    ):
        return False
    if not release.is_dir() or not runtime.is_dir():
        return False
    _validate_source_tree(runtime)
    _verify_release(release, source_root=runtime)
    return True


def _build_cache(target: Path, release_archive: Path, runtime_archive: Path) -> None:
    release = _safe_extract(release_archive, target / "release-unpacked")
    runtime = _safe_extract(runtime_archive, target / "runtime-unpacked")
    _validate_source_tree(runtime)
    release_target = target / "release"
    runtime_target = target / "runtime"
    release.rename(release_target)
    runtime.rename(runtime_target)
    verification = _verify_release(release_target, source_root=runtime_target)
    (target / "metadata.json").write_text(
        json.dumps(
            _metadata(verification, runtime_target), ensure_ascii=False, indent=2, sort_keys=True
        )
        + "\n",
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
        except (FileNotFoundError, OSError, ValueError, ImportError, json.JSONDecodeError):
            if offline:
                raise FileNotFoundError(
                    "Offline Spokenform Gold cache is missing or invalid for "
                    f"{SPOKENFORM_GOLD_TAG}; run online without --offline or use --refresh."
                ) from None
    if offline:
        raise FileNotFoundError(
            f"Offline Spokenform Gold cache is missing for {SPOKENFORM_GOLD_TAG}; "
            "run once online to populate it."
        )

    root.parent.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=f".{SPOKENFORM_GOLD_TAG}.", dir=root.parent))
    release_archive = temporary_root / "release.zip"
    runtime_archive = temporary_root / "runtime.zip"
    try:
        _download(SPOKENFORM_GOLD_ARCHIVE_URL, release_archive)
        if _sha256(release_archive) != SPOKENFORM_GOLD_ARCHIVE_SHA256:
            raise ValueError("Spokenform Gold release archive SHA256 does not match the pin")
        _download(SPOKENFORM_GOLD_RUNTIME_URL, runtime_archive)
        _build_cache(temporary_root, release_archive, runtime_archive)
        backup = root.with_name(f".{root.name}.previous")
        shutil.rmtree(backup, ignore_errors=True)
        if root.exists():
            root.replace(backup)
        temporary_root.replace(root)
        shutil.rmtree(backup, ignore_errors=True)
    except Exception:
        shutil.rmtree(temporary_root, ignore_errors=True)
        raise
    return root / "release"


__all__ = [
    "RELEASE_PIN",
    "SPOKENFORM_GOLD_ARCHIVE_SHA256",
    "SPOKENFORM_GOLD_ARCHIVE_URL",
    "SPOKENFORM_GOLD_COMMIT",
    "SPOKENFORM_GOLD_ASSET",
    "SPOKENFORM_GOLD_POLICY_CONTRACT",
    "SPOKENFORM_GOLD_RELEASE_MANIFEST_SHA256",
    "SPOKENFORM_GOLD_RELEASE_VERSION",
    "SPOKENFORM_GOLD_REPOSITORY",
    "SPOKENFORM_GOLD_RUNTIME_SOURCE_REF",
    "SPOKENFORM_GOLD_RUNTIME_URL",
    "SPOKENFORM_GOLD_TAG",
    "cache_path",
    "ensure_data",
    "load_gold_module",
    "metadata_path",
    "release_path",
    "source_path",
]
