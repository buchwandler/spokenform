import json

import pytest

from benchmarks.polynorm_data import (
    POLYNORM_COMMIT,
    PolyNormCase,
    data_path,
    ensure_data,
    load_cases,
    selected_locales,
)


def _write_cache(root, locale: str = "en-US"):
    path = data_path(locale, root)
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "index": "1",
                "category": "Date",
                "original_text": "2",
                "normalized_text": "two",
            }
        )
        + "\n"
        + json.dumps(
            {
                "index": "2",
                "category": "Cardinal",
                "original_text": "3",
                "normalized_text": "three",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (path.parents[1] / "LICENSE").write_text("CC BY-NC-ND 4.0\n", encoding="utf-8")
    return path


def test_pinned_cache_loads_and_filters_cases(tmp_path) -> None:
    _write_cache(tmp_path)

    cases = load_cases(("en-US",), cache_dir=tmp_path, category="date")

    assert POLYNORM_COMMIT in str(data_path("en-US", tmp_path))
    assert cases == (PolyNormCase("en-US", "1", "Date", "2", "two"),)


def test_selected_locales_rejects_non_overlap() -> None:
    assert selected_locales() == ("de-DE", "en-US", "es-MX", "fr-FR", "it-IT")
    with pytest.raises(ValueError, match="overlap locale"):
        selected_locales("ja-JP")


def test_offline_cache_requires_all_selected_files(tmp_path) -> None:
    _write_cache(tmp_path)

    with pytest.raises(FileNotFoundError, match="missing"):
        ensure_data(("de-DE",), cache_dir=tmp_path, offline=True)


def test_download_requires_explicit_license(tmp_path) -> None:
    with pytest.raises(PermissionError, match="--accept-license"):
        ensure_data(("en-US",), cache_dir=tmp_path)
