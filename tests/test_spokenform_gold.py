from __future__ import annotations

import json
from pathlib import Path

import pytest

from spokenform import __version__ as SPOKENFORM_VERSION


def test_parser_defaults_and_options() -> None:
    from benchmarks import spokenform_gold as cli

    args = cli._parser().parse_args(
        [
            "--cache-dir",
            "/tmp/cache",
            "--offline",
            "--refresh",
            "--download-only",
            "--split",
            "all",
            "--mode",
            "accepted",
            "--report",
            "none",
            "--case",
            "one",
            "--case",
            "two",
        ]
    )
    assert cli._parser().parse_args([]).gold_root is None
    assert cli._parser().parse_args([]).split == "test"
    assert cli._parser().parse_args([]).report == "html"
    assert args.offline and args.refresh and args.download_only
    assert args.split == "all"
    assert args.mode == "accepted"
    assert args.cases == ["one", "two"]


@pytest.mark.parametrize("value", ["nan", "inf", "-1", "1.5"])
def test_gate_rejects_non_finite_or_out_of_range_values(value: str) -> None:
    from benchmarks import spokenform_gold as cli

    with pytest.raises(SystemExit):
        cli._parser().parse_args(["--gate", value])


def test_prepare_gold_record_requires_profile() -> None:
    from benchmarks import spokenform_gold as cli

    with pytest.raises(ValueError, match="gold-v1"):
        cli.prepare_gold_record("Alarm at 08:05.", "en", "en-US", None)


def test_evaluation_writes_enriched_artifacts_without_sibling_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from benchmarks import spokenform_gold as cli

    records = [
        {
            "id": "first",
            "family_id": "family-one",
            "input": "First 1.",
            "expected_output": "First one.",
            "language": "en",
            "locale": "en-US",
            "status": "gold",
            "source": {"benchmark": "spokenform_curated"},
            "units": [{"category": "cardinal"}],
        },
        {
            "id": "second",
            "family_id": "family-two",
            "input": "Second 2.",
            "expected_output": "Second two.",
            "language": "en",
            "locale": "en-US",
            "status": "gold",
            "source": {"benchmark": "spokenform_curated"},
            "units": [{"category": "cardinal"}],
        },
    ]

    class FakeBenchmark:
        @staticmethod
        def run_benchmark(**kwargs: object) -> dict:
            output = Path(kwargs["results_dir"])
            output.mkdir(parents=True)
            summary = {
                "mode": "canonical",
                "records_total": 2,
                "records_scorable": 2,
                "primary_accuracy": 0.5,
                "sentence_canonical_accuracy": 0.5,
                "unit_canonical_accuracy": 0.5,
                "accepted_variant_accuracy": 1.0,
                "no_change_accuracy": 1.0,
                "false_positive_normalization_rate": 0.0,
                "per_category": {
                    "cardinal": {"records": 2, "canonical_matches": 1, "accepted_matches": 2}
                },
                "per_language": {
                    "en": {"records": 2, "canonical_matches": 1, "accepted_matches": 2}
                },
                "per_locale": {
                    "en-US": {"records": 2, "canonical_matches": 1, "accepted_matches": 2}
                },
                "per_status": {
                    "gold": {"records": 2, "canonical_matches": 1, "accepted_matches": 2}
                },
                "ambiguous_count": 0,
                "quarantine_count": 0,
                "excluded_count": 0,
                "record_results": [
                    {
                        "id": "first",
                        "expected_output": "First one.",
                        "prediction": "First one.",
                        "canonical_match": True,
                        "accepted_match": True,
                        "accepted_variants": ["First one."],
                    },
                    {
                        "id": "second",
                        "expected_output": "Second two.",
                        "prediction": "WRONG",
                        "canonical_match": False,
                        "accepted_match": False,
                        "accepted_variants": ["Second two."],
                    },
                ],
            }
            (output / "predictions.jsonl").write_text("", encoding="utf-8")
            (output / "failures.jsonl").write_text("", encoding="utf-8")
            (output / "failures.md").write_text("", encoding="utf-8")
            return {
                "run_id": "run",
                "timestamp_utc": "now",
                "spokenform_version": SPOKENFORM_VERSION,
                "spokenform_commit": "spokenform-commit",
                "spokenform_gold_version": "0.1.0-exp",
                "gold_manifest_hash": "manifest-hash",
                "split": "test",
                "record_count": 2,
                "profile_name": "gold-v1",
                "profile_config": {"name": "gold-v1"},
                "mode": "canonical",
                "summary": summary,
            }

        @staticmethod
        def load_release_records(*args: object, **kwargs: object) -> tuple[dict, list[dict]]:
            return {"manifest_hash": "manifest-hash"}, records

    source = cli.GoldSource(tmp_path / "release", None, "explicit", None, "explicit-root", None)
    monkeypatch.setattr(cli, "_resolve_gold_source", lambda args: source)
    monkeypatch.setattr(cli, "_load_gold_benchmark", lambda source_root=None: FakeBenchmark)
    args = cli._parser().parse_args(
        ["--gold-root", str(source.gold_root), "--results-dir", str(tmp_path / "results")]
    )

    run_dir, summary = cli.evaluate_and_write(args)

    assert (run_dir / "rows.jsonl").is_file()
    assert (run_dir / "report.html").is_file()
    persisted = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (run_dir / "rows.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert persisted["adapter"]["source_mode"] == "explicit-root"
    assert rows[1]["id"] == "second"
    assert rows[1]["expected"] == "Second two."
    assert rows[1]["actual"] == "WRONG"
    assert summary["profile_name"] == "gold-v1"


def test_report_none_skips_html(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from benchmarks import spokenform_gold as cli

    monkeypatch.setattr(cli, "evaluate_and_write", lambda args: (tmp_path, {"download_only": True}))
    args = cli._parser().parse_args(["--report", "none"])
    run_dir, summary = cli.evaluate_and_write(args)
    assert run_dir == tmp_path
    assert summary["download_only"]
