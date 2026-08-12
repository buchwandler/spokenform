"""Command-line interface for :mod:`spokenform`."""

from __future__ import annotations

import argparse
import json
import sys

from .api import prepare


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spokenform",
        description="Convert one-language written text into a readable spoken form.",
    )
    parser.add_argument("text", nargs="*", help="Text to prepare; stdin is used when omitted")
    parser.add_argument("--lang", default="en", help="Language or locale code (default: en)")
    parser.add_argument(
        "--spacy-model",
        help="Name of an installed spaCy model to use for context-aware expansion",
    )
    parser.add_argument("--no-abbreviations", action="store_true")
    parser.add_argument("--no-structured", action="store_true")
    parser.add_argument("--no-numbers", action="store_true")
    parser.add_argument("--keep-whitespace", action="store_true")
    parser.add_argument(
        "--symbol-mode",
        choices=("none", "remove", "keep"),
        default="none",
        help="Residual punctuation/symbol policy (default: none)",
    )
    parser.add_argument(
        "--keep-symbols",
        default="",
        help="Exact Unicode symbols to retain when --symbol-mode=keep",
    )
    parser.add_argument(
        "--generic-acronyms",
        choices=("known-only", "spell-unknown"),
        default="known-only",
        dest="generic_acronym_mode",
        help="Whether to spell unknown uppercase initialisms",
    )
    parser.add_argument(
        "--generic-acronym-case",
        choices=("upper", "lower"),
        default="upper",
        help="Case for generic grapheme-spaced uppercase acronyms",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Raise on unavailable spaCy models and invalid protected spans",
    )
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
        spacy_model=args.spacy_model,
        expand_abbreviations=not args.no_abbreviations,
        expand_structured=not args.no_structured,
        expand_numbers=not args.no_numbers,
        normalize_whitespace=not args.keep_whitespace,
        symbol_mode=args.symbol_mode,
        keep_symbols=args.keep_symbols,
        generic_acronym_mode=args.generic_acronym_mode.replace("-", "_"),
        generic_acronym_case=args.generic_acronym_case,
        strict=args.strict,
    )
    if args.json:
        # Keep CLI JSON portable when stdout uses a legacy Windows code page.
        print(json.dumps(result.to_dict(), ensure_ascii=True, indent=2))
    elif args.changes:
        print(result.render_changes())
    else:
        print(result.spoken_text)
        for warning in result.warnings:
            print(f"warning: {warning}", file=sys.stderr)
    return 0
