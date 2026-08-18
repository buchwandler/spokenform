from __future__ import annotations

import json

import pytest

from benchmarks import async_tn as cli
from benchmarks import async_tn_data as data


def _cache(tmp_path):
    root = data.cache_path(tmp_path)
    source = {
        "row_index": 1,
        "original_text": "Pay 5.",
        "normalized_text": "Pay five.",
        "categories": ["cardinal"],
        "units": [{"text": "5", "norm_category": "cardinal"}],
    }
    multilingual = {
        "sentence_id": "one",
        "languages": {
            "de": {
                "original_text": "Am 5.",
                "normalized_text": "Am fünf.",
                "units": [{"text": "5", "norm_category": "cardinal"}],
            }
        },
    }
    values = {
        data.ENGLISH_SOURCE_FILE: [source],
        data.MULTILINGUAL_SOURCE_FILE: [multilingual],
        "data/overview.json": [],
        "data/categories.json": {},
        "data/multilingual-overview.json": [],
        "data/multilingual-categories.json": {},
    }
    for relative_path, value in values.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
    data.ensure_data(
        (data.ENGLISH_SUITE, data.MULTILINGUAL_SUITE), cache_dir=tmp_path, offline=True
    )
    return tmp_path


def test_parser_supports_requested_options():
    args = cli._parser().parse_args(
        [
            "--suite",
            "multilingual",
            "--language",
            "de",
            "--category",
            "date",
            "--case",
            "multilingual:de:one",
            "--limit",
            "2",
            "--profile",
            "extended",
            "--normalize-literals",
            "--speech-wer-threshold",
            "0.2",
            "--offline",
            "--report",
            "none",
            "--show-failures",
            "semantic",
        ]
    )
    assert args.suite == "multilingual"
    assert args.language == "de"
    assert args.profile == "extended"
    assert args.offline
    assert args.report == "none"


def test_english_language_filter_is_rejected(tmp_path):
    args = cli._parser().parse_args(["--suite", "english", "--language", "de"])
    args.cache_dir = tmp_path
    with pytest.raises(ValueError, match="only valid"):
        cli._load_selected_cases(args)


def test_offline_cli_writes_expected_artifacts(tmp_path):
    cache_dir = _cache(tmp_path / "cache")
    args = cli._parser().parse_args(
        [
            "--suite",
            "all",
            "--cache-dir",
            str(cache_dir),
            "--results-dir",
            str(tmp_path / "results"),
            "--offline",
            "--report",
            "none",
            "--limit",
            "2",
        ]
    )
    run_dir, summary = cli.evaluate_and_write(args)
    assert (run_dir / "summary.json").is_file()
    assert (run_dir / "rows.jsonl").is_file()
    assert (run_dir / "units.jsonl").is_file()
    assert (run_dir / "failures.jsonl").is_file()
    assert (run_dir / "exclusions.jsonl").is_file()
    assert (run_dir / "reference.json").is_file()
    assert not (run_dir / "report.html").exists()
    assert summary["environment"]["configuration"]["oracle_categories_passed_to_prepare"] is False


def test_offline_cli_writes_html_report_by_default(tmp_path):
    cache_dir = _cache(tmp_path / "cache")
    args = cli._parser().parse_args(
        [
            "--suite",
            "all",
            "--cache-dir",
            str(cache_dir),
            "--results-dir",
            str(tmp_path / "results"),
            "--offline",
            "--limit",
            "2",
        ]
    )
    run_dir, _ = cli.evaluate_and_write(args)
    assert (run_dir / "report.html").is_file()


def test_offline_cli_writes_oracle_artifacts(tmp_path):
    cache_dir = _cache(tmp_path / "cache")
    args = cli._parser().parse_args(
        [
            "--suite",
            "all",
            "--cache-dir",
            str(cache_dir),
            "--results-dir",
            str(tmp_path / "results"),
            "--offline",
            "--report",
            "none",
            "--limit",
            "2",
            "--candidate-oracle",
        ]
    )
    run_dir, summary = cli.evaluate_and_write(args)
    assert summary["candidate_oracle"]["enabled"] is True
    assert (run_dir / "oracle_summary.json").is_file()


def test_download_only_does_not_evaluate(monkeypatch, tmp_path):
    calls = []

    def fake_ensure(*args, **kwargs):
        calls.append((args, kwargs))
        return data.cache_path(tmp_path)

    monkeypatch.setattr(cli, "ensure_data", fake_ensure)
    args = cli._parser().parse_args(["--download-only", "--report", "none"])
    args.cache_dir = tmp_path
    root, summary = cli.evaluate_and_write(args)
    assert root == data.cache_path(tmp_path)
    assert summary["download_only"]
    assert calls


def test_refresh_and_offline_are_rejected(tmp_path):
    args = cli._parser().parse_args(["--offline", "--refresh", "--report", "none"])
    args.cache_dir = tmp_path
    with pytest.raises(ValueError, match="cannot be used together"):
        cli.evaluate_and_write(args)
