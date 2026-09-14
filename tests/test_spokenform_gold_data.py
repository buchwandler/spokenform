from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from benchmarks import spokenform_gold_data as data


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_release_archive(
    path: Path,
    *,
    release_format: str = "v2",
    schema_version: str = "2.0.0",
    corpus_file: str = "corpus.jsonl",
    traversal: bool = False,
) -> bytes:
    root = "spokenform-gold-v0.2.0-exp/"
    payload = b"fixture-payload"
    corpus = b'{"schema_version":"2.0.0","id":"fixture"}\n'
    manifest = {
        "benchmark_version": "0.2.0-exp",
        "format": release_format,
        "schema_version": schema_version,
        "corpus_file": corpus_file,
        "record_files": ["corpus.jsonl"],
        "split_registry": None,
        "file_hashes": {"payload.txt": _sha256(payload), "corpus.jsonl": _sha256(corpus)},
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(root + "payload.txt", payload)
        archive.writestr(root + "corpus.jsonl", corpus)
        archive.writestr(root + "manifest.json", json.dumps(manifest))
        if traversal:
            archive.writestr("../../escape.txt", "escape")
    return json.dumps(manifest).encode()


def _write_runtime_archive(path: Path) -> None:
    root = "gold-runtime/"
    release_module = """import hashlib\nimport json\nfrom pathlib import Path\n\ndef verify_release(root):\n    manifest = json.loads((Path(root) / 'manifest.json').read_text())\n    for name, expected in manifest['file_hashes'].items():\n        if hashlib.sha256((Path(root) / name).read_bytes()).hexdigest() != expected:\n            raise ValueError('bad fixture release')\n    return {'manifest': manifest, 'manifest_hash': hashlib.sha256((Path(root) / 'manifest.json').read_bytes()).hexdigest()}\n"""
    files = {
        "spokenform_gold/__init__.py": "__version__ = '0.2.0'\n",
        "spokenform_gold/scoring.py": "\n",
        "spokenform_gold/release.py": release_module,
        "spokenform_gold/benchmark.py": "from .release import verify_release\n",
        "sources/manifest.json": "{}\n",
        "taxonomy/.keep": "",
        "pyproject.toml": "[project]\nname='fixture'\n",
        "LICENSE": "fixture\n",
        "LICENSE-DATA": "fixture\n",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for relative, content in files.items():
            archive.writestr(root + relative, content)


def _patch_pin(
    monkeypatch: pytest.MonkeyPatch, release_archive: Path, manifest: bytes, runtime_archive: Path
) -> None:
    monkeypatch.setattr(data, "SPOKENFORM_GOLD_TAG", "v0.2.0-exp")
    monkeypatch.setattr(data, "SPOKENFORM_GOLD_RELEASE_VERSION", "0.2.0-exp")
    monkeypatch.setattr(data, "SPOKENFORM_GOLD_ASSET", "spokenform-gold-v0.2.0-exp.zip")
    monkeypatch.setattr(
        data, "SPOKENFORM_GOLD_ARCHIVE_SHA256", _sha256(release_archive.read_bytes())
    )
    monkeypatch.setattr(data, "SPOKENFORM_GOLD_RELEASE_MANIFEST_SHA256", _sha256(manifest))
    monkeypatch.setattr(data, "SPOKENFORM_GOLD_RUNTIME_SOURCE_REF", "v0.2.0-exp")
    monkeypatch.setattr(data, "SPOKENFORM_GOLD_ARCHIVE_URL", "https://example.invalid/release.zip")
    monkeypatch.setattr(data, "SPOKENFORM_GOLD_RUNTIME_URL", "https://example.invalid/runtime.zip")


def test_first_download_cache_hit_refresh_and_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release_archive = tmp_path / "release.zip"
    manifest = _write_release_archive(release_archive)
    runtime_archive = tmp_path / "runtime.zip"
    _write_runtime_archive(runtime_archive)
    _patch_pin(monkeypatch, release_archive, manifest, runtime_archive)
    calls: list[str] = []

    def download(url: str, destination: Path) -> None:
        calls.append(url)
        destination.write_bytes(
            runtime_archive.read_bytes() if "runtime" in url else release_archive.read_bytes()
        )

    monkeypatch.setattr(data, "_download", download)
    release = data.ensure_data(cache_dir=tmp_path / "cache")
    assert release == data.release_path(tmp_path / "cache")
    metadata = json.loads(data.metadata_path(tmp_path / "cache").read_text(encoding="utf-8"))
    assert metadata["tag"] == "v0.2.0-exp"
    assert metadata["release_format"] == "v2"
    assert metadata["gold_schema_version"] == "2.0.0"
    assert (release / "manifest.json").is_file()

    monkeypatch.setattr(data, "_download", lambda *_args: pytest.fail("cache hit used the network"))
    assert data.ensure_data(cache_dir=tmp_path / "cache") == release
    monkeypatch.setattr(data, "_download", download)
    assert data.ensure_data(cache_dir=tmp_path / "cache", refresh=True) == release
    assert len(calls) == 4


@pytest.mark.parametrize(
    ("release_kwargs", "message"),
    [
        ({"release_format": "v1"}, "not a v2 corpus release"),
        ({"schema_version": "1.0.0"}, "unexpected schema version"),
        ({"corpus_file": "records.jsonl"}, "unexpected corpus file"),
    ],
)
def test_cached_invalid_release_shape_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, release_kwargs: dict[str, str], message: str
) -> None:
    archive = tmp_path / "fixture.zip"
    manifest = _write_release_archive(archive, **release_kwargs)
    runtime = tmp_path / "runtime.zip"
    _write_runtime_archive(runtime)
    _patch_pin(monkeypatch, archive, manifest, runtime)

    def download(url: str, destination: Path) -> None:
        destination.write_bytes(runtime.read_bytes() if "runtime" in url else archive.read_bytes())

    monkeypatch.setattr(data, "_download", download)
    with pytest.raises(ValueError, match=message):
        data.ensure_data(cache_dir=tmp_path / "cache")


def test_offline_missing_cache_has_actionable_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(data, "SPOKENFORM_GOLD_TAG", "v0.2.0-exp")
    with pytest.raises(FileNotFoundError, match="Offline.*Spokenform Gold.*v0.2.0-exp"):
        data.ensure_data(cache_dir=tmp_path / "cache", offline=True)


def test_safe_extract_rejects_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    _write_release_archive(archive, traversal=True)
    with pytest.raises(ValueError, match="unsafe|escapes"):
        data._safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "escape.txt").exists()
