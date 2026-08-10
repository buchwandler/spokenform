"""Command-line entry point for the diagnostic PolyNorm benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

from .polynorm_data import POLYNORM_LOCALES, ensure_data, load_cases, selected_locales
from .polynorm_eval import evaluate_and_write


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate Spokenform against pinned PolyNorm-Bench data.")
    parser.add_argument("--accept-license", action="store_true", help="Allow downloading CC BY-NC-ND data.")
    parser.add_argument("--offline", action="store_true", help="Use only the local pinned cache.")
    parser.add_argument("--locale", choices=POLYNORM_LOCALES)
    parser.add_argument("--category")
    parser.add_argument("--case", dest="case_id", help="Case identifier such as en-US:1.")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--refresh", action="store_true", help="Redownload selected pinned files.")
    parser.add_argument("--download-only", action="store_true")
    parser.add_argument("--show-failures", choices=("none", "all"), default="none")
    parser.add_argument("--cache-dir", type=Path, default=Path(".cache/polynorm-bench"))
    parser.add_argument("--results-dir", type=Path, default=Path("benchmark-results/polynorm"))
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    locales = selected_locales(args.locale)
    ensure_data(
        locales,
        cache_dir=args.cache_dir,
        offline=args.offline,
        accept_license=args.accept_license,
        refresh=args.refresh,
    )
    if args.download_only:
        print(f"Cached PolyNorm data for {', '.join(locales)}")
        return 0
    cases = load_cases(
        locales,
        cache_dir=args.cache_dir,
        category=args.category,
        case_id=args.case_id,
        limit=args.limit,
    )
    output_dir, summary = evaluate_and_write(cases, output_root=args.results_dir)
    print(f"PolyNorm cases: {summary['cases']}")
    print(f"Results: {output_dir}")
    if args.show_failures == "all":
        failures_path = output_dir / "failures.md"
        print(failures_path.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
