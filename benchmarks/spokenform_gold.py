"""Command-line entry point for the experimental Spokenform Gold benchmark."""

from __future__ import annotations

import argparse
import importlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from spokenform import __version__ as SPOKENFORM_VERSION
from spokenform import prepare


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Spokenform against an experimental Spokenform Gold release."
    )
    parser.add_argument("--gold-root", required=True, type=Path)
    parser.add_argument("--split")
    parser.add_argument("--language")
    parser.add_argument("--locale")
    parser.add_argument("--category")
    parser.add_argument("--case", action="append", dest="cases")
    parser.add_argument("--profile", default="gold-v1")
    parser.add_argument("--mode", choices=("canonical", "accepted"), default="canonical")
    parser.add_argument(
        "--results-dir",
        type=Path,
        default=Path("benchmark-results/spokenform-gold"),
    )
    parser.add_argument("--show-failures", action="store_true")
    parser.add_argument("--gate", type=float)
    return parser


def _load_gold_benchmark():
    try:
        return importlib.import_module("spokenform_gold.benchmark")
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "spokenform_gold is required for this benchmark. "
            "Install it from the sibling repo or an experimental release checkout."
        ) from exc


def _source_commit() -> str:
    try:
        completed = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return completed.stdout.strip() or "unknown"


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def prepare_gold_record(
    text: str, language: str, locale: str, profile: dict[str, Any] | None = None
) -> str:
    if profile is None or profile.get("name") != "gold-v1":
        raise ValueError("Spokenform benchmark expects the gold-v1 profile")
    prepare_kwargs = dict(profile.get("prepare_kwargs", {}))
    return prepare(text, language=locale, **prepare_kwargs).spoken_text


def evaluate_and_write(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    benchmark = _load_gold_benchmark()
    run_dir = args.results_dir / _run_id()
    summary = benchmark.run_benchmark(
        gold_root=args.gold_root,
        split=args.split,
        language=args.language,
        locale=args.locale,
        category=args.category,
        case_ids=set(args.cases or []),
        prepare=prepare_gold_record,
        results_dir=run_dir,
        mode=args.mode,
        profile_name=args.profile,
        spokenform_version=SPOKENFORM_VERSION,
        spokenform_commit=_source_commit(),
    )
    return run_dir, summary


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    run_dir, summary = evaluate_and_write(args)
    print(
        json.dumps(
            {
                "records": summary["record_count"],
                "mode": summary["mode"],
                "primary_accuracy": summary["summary"]["primary_accuracy"],
                "results_dir": str(run_dir),
                "spokenform_version": summary["spokenform_version"],
                "spokenform_commit": summary["spokenform_commit"],
                "spokenform_gold_version": summary["spokenform_gold_version"],
                "gold_manifest_hash": summary["gold_manifest_hash"],
                "profile": summary["profile_name"],
                "split": summary["split"],
            },
            ensure_ascii=False,
        )
    )
    if args.show_failures:
        print(f"failures={run_dir / 'failures.jsonl'}")
    if args.gate is not None and summary["summary"]["primary_accuracy"] < args.gate:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
