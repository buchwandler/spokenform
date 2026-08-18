from __future__ import annotations

import json

from benchmarks.google_tn import main


def test_cli_writes_summary_rows_and_failure_reports(tmp_path, capsys) -> None:
    data_dir = tmp_path / "en_with_types"
    data_dir.mkdir()
    (data_dir / "output-00099-of-00100").write_text(
        "PLAIN\tHello\t<self>\nDATE\t2005\ttwo thousand five\n<eos>\t<eos>\n",
        encoding="utf-8",
    )
    results_dir = tmp_path / "results"
    assert (
        main(
            [
                "--data-dir",
                str(data_dir),
                "--split",
                "test-full",
                "--limit",
                "1",
                "--results-dir",
                str(results_dir),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    run_dir = results_dir / next(path.name for path in results_dir.iterdir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["evaluated"] == 1
    assert summary["provenance"]["configuration"]["oracle_classes_passed_to_prepare"] is False
    assert (run_dir / "rows.jsonl").exists()
    assert (run_dir / "failures.jsonl").exists()
    assert (run_dir / "failures.md").exists()
    assert "Results:" in output


def test_cli_writes_oracle_artifacts_when_requested(tmp_path) -> None:
    data_dir = tmp_path / "en_with_types"
    data_dir.mkdir()
    (data_dir / "output-00099-of-00100").write_text(
        "PLAIN\tHello\t<self>\nDATE\t2005\ttwo thousand five\n<eos>\t<eos>\n",
        encoding="utf-8",
    )
    results_dir = tmp_path / "results"

    assert (
        main(
            [
                "--data-dir",
                str(data_dir),
                "--split",
                "test-full",
                "--limit",
                "1",
                "--candidate-oracle",
                "--results-dir",
                str(results_dir),
            ]
        )
        == 0
    )

    run_dir = results_dir / next(path.name for path in results_dir.iterdir())
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["candidate_oracle"]["enabled"] is True
    assert (run_dir / "oracle_summary.json").exists()
