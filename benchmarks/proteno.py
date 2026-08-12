"""Command-line entry point for the diagnostic Proteno benchmark."""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from .proteno_data import ensure_data, load_cases_with_exclusions, selected_languages
from .proteno_eval import BENCHMARK_PROFILES, evaluate_and_write


def _non_negative_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a number") from exc
    if not math.isfinite(parsed) or parsed < 0:
        raise argparse.ArgumentTypeError("must be a finite, non-negative number")
    return parsed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate Spokenform against pinned English and Spanish Proteno data."
    )
    parser.add_argument(
        "--accept-license", action="store_true", help="Allow downloading CC BY-SA 3.0 data."
    )
    parser.add_argument("--offline", action="store_true", help="Use only the local pinned cache.")
    parser.add_argument("--language", choices=("en", "es"))
    parser.add_argument("--split", choices=("all", "train", "test"), default="all")
    parser.add_argument("--case", dest="case_id", help="Case identifier such as en:00481.")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--speech-wer-threshold",
        type=_non_negative_float,
        metavar="VALUE",
        help="Persist only failures with Speech WER strictly greater than VALUE.",
    )
    parser.add_argument("--refresh", action="store_true", help="Redownload selected pinned files.")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument(
        "--show-failures",
        choices=("none", "all"),
        default="none",
        help="Print the failure report index after evaluation.",
    )
    parser.add_argument("--profile", choices=BENCHMARK_PROFILES, default="default")
    parser.add_argument(
        "--normalize-literals",
        action="store_true",
        help="Alias for the extended profile; verbalize protected URL/email/version literals.",
    )
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/proteno"))
    parser.add_argument("--results-dir", type=Path, default=Path("benchmark-results/proteno"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    languages = selected_languages(args.language)
    ensure_data(
        languages,
        cache_dir=args.cache_dir,
        offline=args.offline,
        accept_license=args.accept_license,
        refresh=args.refresh,
    )
    if args.download_only:
        print(f"Cached Proteno data for {', '.join(languages)}")
        return 0
    cases, exclusions = load_cases_with_exclusions(
        languages,
        cache_dir=args.cache_dir,
        split=args.split,
        case_id=args.case_id,
        limit=args.limit,
    )
    profile = "extended" if args.normalize_literals else args.profile
    output_dir, summary = evaluate_and_write(
        cases,
        exclusions=exclusions,
        split=args.split,
        output_root=args.results_dir,
        speech_wer_threshold=args.speech_wer_threshold,
        profile=profile,
    )
    print(
        f"Proteno profile: {summary['profile']} (normalize_literals={summary['normalize_literals']})"
    )
    print(f"Proteno cases: {summary['cases']}")
    print(f"Excluded: {summary['excluded_count']}")
    print(f"Results: {output_dir}")
    if args.show_failures == "all":
        print((output_dir / "failures.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
