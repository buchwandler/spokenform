"""Command-line interface for :mod:`spokenform`."""

from __future__ import annotations

import argparse
import json
import sys

from .api import prepare


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spokenform",
        description="Convert written text into a readable spoken form.",
    )
    parser.add_argument("text", nargs="*", help="Text to prepare; stdin is used when omitted")
    parser.add_argument("--lang", default="en", help="Language or locale code (default: en)")
    parser.add_argument("--detect-language", action="store_true")
    parser.add_argument("--no-abbreviations", action="store_true")
    parser.add_argument("--no-numbers", action="store_true")
    parser.add_argument("--keep-whitespace", action="store_true")
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--changes", action="store_true", help="Show stage-by-stage changes")
    output.add_argument("--json", action="store_true", help="Emit structured JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""
    parser = _parser()
    args = parser.parse_args(argv)
    source = " ".join(args.text) if args.text else sys.stdin.read()
    if not source:
        parser.error("text is required as an argument or on stdin")

    result = prepare(
        source,
        language=args.lang,
        detect_language=args.detect_language,
        expand_abbreviations=not args.no_abbreviations,
        expand_numbers=not args.no_numbers,
        normalize_whitespace=not args.keep_whitespace,
    )
    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    elif args.changes:
        print(result.render_changes())
    else:
        print(result.spoken_text)
    return 0
