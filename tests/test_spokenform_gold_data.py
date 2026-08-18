from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from benchmarks import spokenform_gold_data as data


def _write_archive(path: Path, *, traversal: bool = False) -> None:
    root = "spokenform-gold-ba55d631/"
    files = {
        "spokenform_gold/__init__.py": "__version__ = '0.1.0'\n",
        "spokenform_gold/scoring.py": "\n",
        "spokenform_gold/release.py": """from pathlib import Path\nimport hashlib\nimport json\ndef build_release(**kwargs):\n    root = Path(kwargs['out_root'])\n    root.mkdir(parents=True)\n    payload = b'fixture-release'\n    (root / 'payload.txt').write_bytes(payload)\n    digest = hashlib.sha256(payload).hexdigest()\n    (root / 'manifest.json').write_text(json.dumps({'benchmark_version': '0.1.0-exp', 'file_hashes': {'payload.txt': digest}}), encoding='utf-8')\ndef verify_release(*args, **kwargs):\n    root = Path(args[0] if args else kwargs['gold_root'])\n    manifest = json.loads((root / 'manifest.json').read_text(encoding='utf-8'))\n    actual = hashlib.sha256((root / 'payload.txt').read_bytes()).hexdigest()\n    if actual != manifest['file_hashes']['payload.txt']:\n        raise ValueError('bad fixture release')\n    return {'manifest': manifest, 'manifest_hash': hashlib.sha256((root / 'manifest.json').read_bytes()).hexdigest()}\n""",
        "spokenform_gold/benchmark.py": "from .release import verify_release\n",
        "data/dev/.keep": "",
        "data/test/.keep": "",
        "schemas/.keep": "",
        "sources/manifest.json": "{}\n",
        "splits/family_assignments.json": "{}\n",
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
    assert (release / "manifest.json").is_file()

    def unexpected_download(url: str, destination: Path) -> None:
        raise AssertionError("cache hit used the network")

    monkeypatch.setattr(data, "_download", unexpected_download)
    assert data.ensure_data(cache_dir=tmp_path / "cache") == release

    monkeypatch.setattr(data, "_download", download)
    assert data.ensure_data(cache_dir=tmp_path / "cache", refresh=True) == release
    assert len(calls) == 2


def test_offline_missing_cache_has_actionable_message(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Offline.*Spokenform Gold.*commit"):
        data.ensure_data(cache_dir=tmp_path / "cache", offline=True)


def test_safe_extract_rejects_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    _write_archive(archive, traversal=True)
    with pytest.raises(ValueError, match="unsafe|escapes"):
        data._safe_extract(archive, tmp_path / "out")
    assert not (tmp_path / "escape.txt").exists()
