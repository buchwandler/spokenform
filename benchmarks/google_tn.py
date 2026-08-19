"""Command-line entry point for the Google TN diagnostic benchmark."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Literal, cast

from .candidate_oracle import MAX_COMPONENT_PATHS, MAX_GLOBAL_COMBINATIONS
from .google_tn_data import (
    GOOGLE_TN_SPLITS,
    GOOGLE_TN_TEST_LINE_LIMIT,
    GOOGLE_TN_TO_SPOKENFORM,
    discover_source_files,
    iter_cases,
    source_metadata,
)
from .google_tn_eval import BENCHMARK_PROFILES, evaluate

FAILURE_MARKDOWN_MAX_BYTES = 1024 * 1024


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not-installed"


def _source_commit() -> str | None:
    try:
        result = subprocess.run(
            ("git", "rev-parse", "HEAD"), capture_output=True, check=True, text=True
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _non_negative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Spokenform against a local Google TN / NeMo-compatible TSV shard."
    )
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--language", choices=tuple(GOOGLE_TN_TO_SPOKENFORM), default="en")
    parser.add_argument("--split", choices=GOOGLE_TN_SPLITS, default="test")
    parser.add_argument("--class", dest="semiotic_class")
    parser.add_argument("--case", dest="case_id")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--profile", choices=BENCHMARK_PROFILES, default="default")
    parser.add_argument("--normalize-literals", action="store_true")
    parser.add_argument(
        "--long-number-mode",
        choices=("preserve", "contextual", "cardinal"),
        default="preserve",
    )
    parser.add_argument("--speech-wer-threshold", type=_non_negative_float)
    parser.add_argument("--show-failures", choices=("none", "all"), default="none")
    parser.add_argument(
        "--candidate-oracle",
        action="store_true",
        help="Measure structured-candidate selection headroom and write oracle artifacts.",
    )
    parser.add_argument("--results-dir", type=Path, default=Path("benchmark-results/google-tn"))
    return parser


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _failure_entry(failure: dict) -> str:
    lines = [
        f"#### {failure['id']}",
        f"- Classes: `{', '.join(failure['semiotic_classes'])}`",
        f"- Lines: `{failure['line_start']}-{failure['line_end']}`",
        f"- Original: `{failure['original_text']}`",
        f"- Expected: `{failure['expected']}`",
        f"- Actual: `{failure['actual']}`",
        f"- Outcome: `{failure.get('normalization_outcomes', {})}`",
        f"- Speech WER: `{failure['speech_wer']:.4f}`",
        f"- Source rules: `{', '.join(failure.get('source_rules', []))}`",
        "",
    ]
    if failure.get("failed_spans"):
        lines.append("Failed spans:")
        for span in failure["failed_spans"]:
            lines.append(
                f"- `{span['semiotic_class']}` `{span['written']}` → `{span['actual']}` "
                f"({span['normalization_outcome']})"
            )
        lines.append("")
    return "\n".join(lines)


def _write_failure_reports(failures: list[dict], output_dir: Path) -> None:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for failure in failures:
        for semiotic_class in failure["semiotic_classes"]:
            grouped[semiotic_class].append(failure)
    entries: list[tuple[str, str]] = []
    for semiotic_class, class_failures in sorted(grouped.items()):
        current: list[str] = []
        current_bytes = 0
        part = 1
        for failure in class_failures:
            entry = _failure_entry(failure)
            entry_bytes = len(entry.encode("utf-8"))
            if entry_bytes > FAILURE_MARKDOWN_MAX_BYTES:
                raise ValueError(f"failure {failure['id']} exceeds Markdown report size limit")
            if current and current_bytes + entry_bytes > FAILURE_MARKDOWN_MAX_BYTES:
                entries.append((f"{semiotic_class} (part {part})", "\n".join(current)))
                current = []
                current_bytes = 0
                part += 1
            current.append(entry)
            current_bytes += entry_bytes
        if current:
            label = semiotic_class if part == 1 else f"{semiotic_class} (part {part})"
            entries.append((label, "\n".join(current)))
    index = ["# Google TN failures", "", f"- Total failed sentences: {len(failures):,}", ""]
    for report_index, (semiotic_class, body) in enumerate(entries, 1):
        filename = f"failures-{report_index:03d}.md"
        (output_dir / filename).write_text(
            f"# Google TN failures: {semiotic_class}\n\n{body}", encoding="utf-8"
        )
        index.append(f"- [{semiotic_class}]({filename})")
    (output_dir / "failures.md").write_text("\n".join(index) + "\n", encoding="utf-8")


def evaluate_and_write(args: argparse.Namespace) -> tuple[Path, dict]:
    source_files = discover_source_files(args.data_dir, split=args.split)
    cases = iter_cases(
        args.data_dir,
        language=args.language,
        split=args.split,
        limit=args.limit,
        semiotic_class=args.semiotic_class,
        case_id=args.case_id,
    )
    profile_name = "extended" if args.normalize_literals else args.profile
    if profile_name not in BENCHMARK_PROFILES:
        raise AssertionError(f"unsupported profile: {profile_name}")
    profile = cast(Literal["default", "extended"], profile_name)
    summary, rows, failures = evaluate(
        cases,
        profile=profile,
        normalize_literals=args.normalize_literals or None,
        long_number_mode=args.long_number_mode,
        candidate_oracle=args.candidate_oracle,
    )
    run_dir = args.results_dir / _run_id()
    run_dir.mkdir(parents=True, exist_ok=False)
    source_records = [
        source_metadata(
            path,
            split=args.split,
            selected_line_end=GOOGLE_TN_TEST_LINE_LIMIT if args.split == "test" else None,
        )
        for path in source_files
    ]
    summary["provenance"] = {
        "dataset": source_records,
        "spokenform_language": GOOGLE_TN_TO_SPOKENFORM[args.language],
        "spokenform_version": _package_version("spokenform"),
        "spokenform_source_commit": _source_commit(),
        "abbr2words_version": _package_version("abbr2words"),
        "num2words_version": _package_version("num2words"),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "configuration": {
            "language": args.language,
            "split": args.split,
            "profile": profile,
            "use_spacy": False,
            "symbol_mode": "none",
            "normalize_literals": bool(summary["normalize_literals"]),
            "long_number_mode": args.long_number_mode,
            "surface_policy": "field_join_v1",
            "oracle_classes_passed_to_prepare": False,
            "candidate_oracle_enabled": args.candidate_oracle,
            "candidate_oracle_schema_version": 2 if args.candidate_oracle else None,
            "max_component_paths": MAX_COMPONENT_PATHS if args.candidate_oracle else None,
            "max_global_combinations": MAX_GLOBAL_COMBINATIONS if args.candidate_oracle else None,
            "test_line_limit": GOOGLE_TN_TEST_LINE_LIMIT if args.split == "test" else None,
        },
    }
    _write_jsonl(run_dir / "rows.jsonl", list(rows))
    selected_failures = [
        failure
        for failure in failures
        if args.speech_wer_threshold is None or failure["speech_wer"] > args.speech_wer_threshold
    ]
    _write_jsonl(run_dir / "failures.jsonl", selected_failures)
    _write_failure_reports(selected_failures, run_dir)
    (run_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.candidate_oracle and "candidate_oracle" in summary:
        (run_dir / "oracle_summary.json").write_text(
            json.dumps(
                {
                    "benchmark": "Google TN",
                    "profile": profile,
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "identity": {
                        "benchmark": "Google TN",
                        "spokenform_source_commit": summary["provenance"][
                            "spokenform_source_commit"
                        ],
                        "abbr2words_version": summary["provenance"]["abbr2words_version"],
                        "num2words_version": summary["provenance"]["num2words_version"],
                        "profile": profile,
                        "language": args.language,
                        "split": args.split,
                        "candidate_oracle_schema_version": 2,
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
    if args.show_failures == "all":
        print((run_dir / "failures.md").read_text(encoding="utf-8"))
    return run_dir, summary


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output_dir, summary = evaluate_and_write(args)
    print(f"Google TN profile: {summary['profile']}")
    print(f"Google TN cases: {summary['evaluated']}")
    print(f"Results: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
