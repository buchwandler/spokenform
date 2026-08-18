"""Command-line entry point for the Async TN benchmark."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections.abc import Iterable
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .async_tn_data import (
    ENGLISH_SUITE,
    MULTILINGUAL_SUITE,
    SOURCE_COMMIT,
    SOURCE_LANGUAGES,
    SUITES,
    cache_path,
    data_path,
    ensure_data,
    filter_cases,
    load_cases,
    required_files,
    source_metadata,
)
from .async_tn_eval import BENCHMARK_PROFILES, evaluate_cases
from .candidate_oracle import MAX_COMPONENT_PATHS, MAX_GLOBAL_COMBINATIONS
from .compare_common import with_configuration_hash

FAILURE_MODES = ("none", "semantic", "all")


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not-installed"


def _source_commit() -> str | None:
    try:
        completed = subprocess.run(
            ("git", "rev-parse", "HEAD"), capture_output=True, check=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return completed.stdout.strip() or None


def _non_negative_float(value: str) -> float:
    try:
        result = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if result < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Spokenform against the pinned Async Voice TTS benchmark."
    )
    parser.add_argument("--suite", choices=("english", "multilingual", "all"), default="all")
    parser.add_argument("--language", choices=SOURCE_LANGUAGES)
    parser.add_argument("--category")
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--profile", choices=BENCHMARK_PROFILES, default="default")
    parser.add_argument("--normalize-literals", action="store_true")
    parser.add_argument("--speech-wer-threshold", type=_non_negative_float)
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/async-tn"))
    parser.add_argument("--results-dir", type=Path, default=Path("benchmark-results/async-tn"))
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--show-failures", choices=FAILURE_MODES, default="none")
    parser.add_argument("--report", choices=("html", "none"), default="html")
    parser.add_argument(
        "--candidate-oracle",
        action="store_true",
        help="Measure structured-candidate selection headroom and write oracle artifacts.",
    )
    return parser


def _selected_suites(suite: str) -> tuple[str, ...]:
    return SUITES if suite == "all" else (suite,)


def _load_selected_cases(args: argparse.Namespace) -> tuple[list[Any], list[dict[str, Any]]]:
    if args.limit is not None and args.limit < 0:
        raise ValueError("--limit must be non-negative")
    if args.suite == ENGLISH_SUITE and args.language is not None:
        raise ValueError("--language is only valid with --suite multilingual or all")
    cases: list[Any] = []
    exclusions: list[dict[str, Any]] = []
    for suite in _selected_suites(args.suite):
        parsed_cases, parsed_exclusions = load_cases(
            suite,
            cache_dir=args.cache_dir,
            languages=(args.language,) if suite == MULTILINGUAL_SUITE and args.language else None,
        )
        cases.extend(parsed_cases)
        exclusions.extend(item.as_dict() for item in parsed_exclusions)
    cases = list(
        filter_cases(
            cases,
            language=args.language,
            category=args.category,
            case_id=args.case_id,
            limit=args.limit,
        )
    )
    return cases, exclusions


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _reference(cache_dir: Path, suites: tuple[str, ...]) -> dict[str, Any]:
    from .async_tn_data import REFERENCE_FILES

    payload: dict[str, Any] = {
        "schema_version": 1,
        "benchmark": "async_tn",
        "source_commit": SOURCE_COMMIT,
        "methodology": "upstream-published-audio-llm-judge",
        "comparable_to_spokenform_directly": False,
        "english": {},
        "multilingual": {},
    }
    for suite in suites:
        target = payload[suite]
        for relative_path in REFERENCE_FILES[suite]:
            key = Path(relative_path).stem
            target[key] = json.loads(
                data_path(relative_path, cache_dir=cache_dir).read_text(encoding="utf-8")
            )
    return payload


def _failure_markdown(rows: Iterable[dict[str, Any]], units: Iterable[dict[str, Any]]) -> str:
    failed_rows = [row for row in rows if row.get("error") or not row.get("speech_equivalent")]
    failed_units = [
        row
        for row in units
        if row.get("outcome") not in {"correct-transform", "identity-preserved"}
    ]
    lines = [
        "# Async TN failures",
        "",
        f"- Failed sentences: {len(failed_rows):,}",
        f"- Failed units: {len(failed_units):,}",
        "",
    ]
    for row in failed_rows:
        lines.extend(
            [
                f"## {row['case_id']}",
                f"- Suite: `{row['suite']}`",
                f"- Language: `{row['source_language']}`",
                f"- Original: `{row['original_text']}`",
                f"- Expected: `{row['expected']}`",
                f"- Actual: `{row['actual']}`",
                f"- Outcome: `{row['outcome']}`",
                f"- Speech WER: `{row['speech_wer']:.4f}`",
                f"- Failure family: `{row.get('failure_family')}`",
                f"- Ownership: `{row.get('ownership')}`",
                f"- Risk tier: `{row.get('risk_tier')}`",
                "",
            ]
        )
    return "\n".join(lines)


def evaluate_and_write(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    suites = _selected_suites(args.suite)
    ensure_data(suites, cache_dir=args.cache_dir, offline=args.offline, refresh=args.refresh)
    if args.download_only:
        print(f"Async TN cache: {cache_path(args.cache_dir)}")
        return cache_path(args.cache_dir), {"download_only": True}
    cases, exclusions = _load_selected_cases(args)
    profile = "extended" if args.normalize_literals else args.profile
    summary, rows, units, failures = evaluate_cases(
        cases,
        profile=profile,
        normalize_literals=args.normalize_literals or None,
        candidate_oracle=args.candidate_oracle,
    )
    metadata = source_metadata(args.cache_dir, files=required_files(suites))
    configuration = {
        "suite": args.suite,
        "languages": [args.language] if args.language else list(SOURCE_LANGUAGES),
        "category": args.category,
        "case_id": args.case_id,
        "limit": args.limit,
        "profile": profile,
        "normalize_literals": summary["normalize_literals"],
        "speech_wer_threshold": args.speech_wer_threshold,
        "oracle_categories_passed_to_prepare": False,
        "candidate_oracle_enabled": args.candidate_oracle,
        "candidate_oracle_schema_version": 1 if args.candidate_oracle else None,
        "max_component_paths": MAX_COMPONENT_PATHS if args.candidate_oracle else None,
        "max_global_combinations": MAX_GLOBAL_COMBINATIONS if args.candidate_oracle else None,
    }
    environment = dict(summary["environment"])
    environment.update(
        {
            "dataset_repository": metadata["source_repo"],
            "dataset_commit": SOURCE_COMMIT,
            "locale_mapping": {
                language: "en_US" if language == "en" else language for language in SOURCE_LANGUAGES
            },
            "spokenform_source_commit": _source_commit(),
            "configuration": configuration,
        }
    )
    summary["environment"] = with_configuration_hash(environment)
    summary.update(
        {
            "run_id": _run_id(),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "dataset_commit": SOURCE_COMMIT,
            "source": metadata,
            "selected_exclusions": len(exclusions),
            "quarantine": {
                "cases": len(exclusions),
                "units": summary["counts"]["units_quarantined"],
                "reasons": dict(sorted(_count_reasons(exclusions).items())),
            },
        }
    )
    summary["counts"]["excluded_cases"] = len(exclusions)
    summary["counts"]["source_cases"] = len(cases) + len(exclusions)
    summary["counts"]["selected_cases"] = len(cases)
    run_dir = args.results_dir / summary["run_id"]
    run_dir.mkdir(parents=True, exist_ok=False)
    _write_jsonl(run_dir / "rows.jsonl", rows)
    _write_jsonl(run_dir / "units.jsonl", units)
    selected_failures = list(failures)
    if args.speech_wer_threshold is not None:
        selected_failures = [
            row for row in selected_failures if row["speech_wer"] > args.speech_wer_threshold
        ]
    if args.show_failures == "semantic":
        selected_failures = [
            row for row in selected_failures if row["semantic_failure"] or row["error"]
        ]
    _write_jsonl(run_dir / "failures.jsonl", selected_failures)
    _write_jsonl(run_dir / "exclusions.jsonl", exclusions)
    (run_dir / "failures.md").write_text(
        _failure_markdown(selected_failures, units), encoding="utf-8"
    )
    reference = _reference(args.cache_dir, suites)
    (run_dir / "reference.json").write_text(
        json.dumps(reference, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.candidate_oracle and "candidate_oracle" in summary:
        (run_dir / "oracle_summary.json").write_text(
            json.dumps(
                {
                    "benchmark": summary["benchmark"],
                    "profile": profile,
                    "generated_at": summary["created_at"],
                    "identity": {
                        "benchmark": summary["benchmark"],
                        "dataset_commit": summary["dataset_commit"],
                        "spokenform_source_commit": summary["environment"][
                            "spokenform_source_commit"
                        ],
                        "abbr2words_version": summary["environment"]["abbr2words_version"],
                        "num2words_version": summary["environment"]["num2words_version"],
                        "profile": profile,
                        "config_hash": summary["environment"]["config_hash"],
                        "candidate_oracle_schema_version": 1,
                        "max_component_paths": MAX_COMPONENT_PATHS,
                        "max_global_combinations": MAX_GLOBAL_COMBINATIONS,
                    },
                    "candidate_oracle": summary["candidate_oracle"],
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    if args.report == "html":
        from .async_tn_report import render_report

        render_report(summary, rows, units, reference, run_dir / "report.html")
    if args.show_failures != "none":
        print((run_dir / "failures.md").read_text(encoding="utf-8"))
    print(f"Async TN source: {SOURCE_COMMIT}")
    print(f"Async TN suite: {args.suite}")
    print(f"Async TN profile: {profile}")
    print(f"Cases: {len(cases):,} selected / {len(cases) + len(exclusions):,} source")
    print(f"Units: {summary['counts']['units_total']:,} total")
    print(f"Scorable: {summary['counts']['units_scorable']:,}")
    print(f"Quarantined: {summary['counts']['units_quarantined']:,}")
    print(
        f"Sentence speech-equivalent: {summary['sentence_metrics']['speech_equivalent'] / len(rows) * 100 if rows else 0:.2f}%"
    )
    print(f"Unit speech-equivalent: {summary['unit_metrics']['accuracy'] * 100:.2f}%")
    print(f"Results: {run_dir}")
    return run_dir, summary


def _count_reasons(records: Iterable[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        reason = str(record["reason"])
        counts[reason] = counts.get(reason, 0) + 1
    return counts


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        evaluate_and_write(args)
    except (FileNotFoundError, PermissionError, ValueError) as exc:
        raise SystemExit(f"Async TN error: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["evaluate_and_write", "main"]
