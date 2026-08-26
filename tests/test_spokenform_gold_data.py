from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from benchmarks import spokenform_gold_data as data


def _write_archive(
    path: Path,
    *,
    traversal: bool = False,
    release_format: str = "v2",
    schema_version: str = "2.0.0",
    corpus_file: str = "corpus.jsonl",
) -> None:
    root = "spokenform-gold-fixture/"
    release_module = f"""from pathlib import Path
import hashlib
import json

def build_release(**kwargs):
    root = Path(kwargs['out_root'])
    root.mkdir(parents=True)
    payload = b'fixture-release'
    (root / 'payload.txt').write_bytes(payload)
    captured = {{
        key: [str(value) for value in value] if key == 'data_paths' else str(value)
        for key, value in kwargs.items()
    }}
    (root / 'build-kwargs.json').write_text(json.dumps(captured), encoding='utf-8')
    digest = hashlib.sha256(payload).hexdigest()
    manifest = {{
        'benchmark_version': '0.2.0-exp',
        'format': {release_format!r},
        'schema_version': {schema_version!r},
        'corpus_file': {corpus_file!r},
        'record_files': ['corpus.jsonl'],
        'split_registry': None,
        'file_hashes': {{'payload.txt': digest}},
    }}
    (root / 'manifest.json').write_text(json.dumps(manifest), encoding='utf-8')

def verify_release(*args, **kwargs):
    root = Path(args[0] if args else kwargs['gold_root'])
    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))
    actual = hashlib.sha256((root / 'payload.txt').read_bytes()).hexdigest()
    if actual != manifest['file_hashes']['payload.txt']:
        raise ValueError('bad fixture release')
    return {{
        'manifest': manifest,
        'manifest_hash': hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest(),
    }}
"""
    files = {
        "spokenform_gold/__init__.py": "__version__ = '0.2.0'\n",
        "spokenform_gold/scoring.py": "\n",
        "spokenform_gold/release.py": release_module,
        "spokenform_gold/benchmark.py": "from .release import verify_release\n",
        "data/corpus.jsonl": '{"schema_version":"2.0.0","id":"fixture"}\n',
        "schemas/.keep": "",
        "sources/manifest.json": "{}\n",
        "taxonomy/.keep": "",
        "pyproject.toml": "[project]\nname='fixture'\n",
        "LICENSE": "fixture\n",
        "LICENSE-DATA": "fixture\n",
    }
    with zipfile.ZipFile(path, "w") as archive:
        for relative, content in files.items():
            archive.writestr(root + relative, content)
        if traversal:
            archive.writestr("../../escape.txt", "escape")


def test_first_download_cache_hit_refresh_and_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    archive = tmp_path / "fixture.zip"
    _write_archive(archive)
    calls: list[str] = []

    def download(url: str, destination: Path) -> None:
        calls.append(url)
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(data, "_download", download)
    release = data.ensure_data(cache_dir=tmp_path / "cache")
    assert release == data.release_path(tmp_path / "cache")
    metadata = json.loads(data.metadata_path(tmp_path / "cache").read_text(encoding="utf-8"))
    assert metadata["source_commit"] == data.SPOKENFORM_GOLD_COMMIT
    assert metadata["release_format"] == "v2"
    assert metadata["gold_schema_version"] == "2.0.0"
    assert metadata["corpus_file"] == "corpus.jsonl"
    assert (release / "manifest.json").is_file()
    build_kwargs = json.loads((release / "build-kwargs.json").read_text(encoding="utf-8"))
    assert Path(build_kwargs["data_paths"][0]).as_posix().endswith("/source/data/corpus.jsonl")
    assert "registry_path" not in build_kwargs

    def unexpected_download(url: str, destination: Path) -> None:
        raise AssertionError("cache hit used the network")

    monkeypatch.setattr(data, "_download", unexpected_download)
    assert data.ensure_data(cache_dir=tmp_path / "cache") == release

    monkeypatch.setattr(data, "_download", download)
    assert data.ensure_data(cache_dir=tmp_path / "cache", refresh=True) == release
    assert len(calls) == 2


@pytest.mark.parametrize(
    ("release_kwargs", "message"),
    [
        ({"release_format": "v1"}, "not a v2 corpus release"),
        ({"schema_version": "1.0.0"}, "unexpected schema version"),
        ({"corpus_file": "records.jsonl"}, "unexpected corpus file"),
    ],
)
def test_cached_invalid_release_shape_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    release_kwargs: dict[str, str],
    message: str,
) -> None:
    archive = tmp_path / "fixture.zip"
    _write_archive(archive, **release_kwargs)

    def download(url: str, destination: Path) -> None:
        destination.write_bytes(archive.read_bytes())

    monkeypatch.setattr(data, "_download", download)
    with pytest.raises(ValueError, match=message):
        data.ensure_data(cache_dir=tmp_path / "cache")


def test_offline_missing_cache_has_actionable_message(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Offline.*Spokenform Gold.*commit"):
        data.ensure_data(cache_dir=tmp_path / "cache", offline=True)


def test_safe_extract_rejects_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    _write_archive(archive, traversal=True)
    with pytest.raises(ValueError, match="unsafe|escapes"):
        data._safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "escape.txt").exists()
