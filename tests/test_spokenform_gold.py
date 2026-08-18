from __future__ import annotations

import json
import sys
from pathlib import Path

from spokenform import __version__ as SPOKENFORM_VERSION


def _import_gold_helpers():
    spokenform_root = Path(__file__).resolve().parents[1]
    if str(spokenform_root) not in sys.path:
        sys.path.insert(0, str(spokenform_root))
    root = Path(__file__).resolve().parents[2] / "spokenform-gold"
    if str(root) not in sys.path:
        sys.path.append(str(root))
    from spokenform_gold.io import read_json
    from spokenform_gold.release import build_release

    return root, build_release, read_json


def test_gold_benchmark_writes_results(tmp_path):
    gold_root, build_release, read_json = _import_gold_helpers()
    from benchmarks import spokenform_gold as cli

    release_root = tmp_path / "release"
    build_release(
        version="0.2.0-exp",
        data_paths=[str(gold_root / "data/test/sample.jsonl")],
        out_root=release_root,
        maturity="experimental",
        registry_path=gold_root / "splits/family_assignments.json",
    )

    args = cli._parser().parse_args(
        [
            "--gold-root",
            str(release_root),
            "--split",
            "test",
            "--results-dir",
            str(tmp_path / "results"),
        ]
    )
    run_dir, summary = cli.evaluate_and_write(args)
    assert (run_dir / "summary.json").is_file()
    assert (run_dir / "predictions.jsonl").is_file()
    assert (run_dir / "failures.jsonl").is_file()
    persisted = read_json(run_dir / "summary.json")
    assert persisted["spokenform_version"] == SPOKENFORM_VERSION
    assert persisted["spokenform_commit"] != "unknown"
    assert persisted["spokenform_gold_version"] == "0.2.0-exp"
    assert persisted["gold_manifest_hash"]
    assert summary["profile_name"] == "gold-v1"
    assert summary["record_count"] > 0


def test_prepare_gold_record_requires_profile():
    _import_gold_helpers()
    from benchmarks import spokenform_gold as cli

    try:
        cli.prepare_gold_record("Alarm at 08:05.", "en", "en-US", None)
    except ValueError as exc:
        assert "gold-v1" in str(exc)
    else:
        raise AssertionError("prepare_gold_record should reject a missing profile")
