"""Command-line interface for :mod:`spokenform`."""

from __future__ import annotations

import argparse
import json
import sys

from .api import prepare
from .config import InterpretationMode, RecognitionDomain, SequenceFallbackMode
from .evidence import LexicalEvidenceProvider
from .language import base_language


def _load_lexhint(
    language: str, *, variant: str, dataset_version: str | None
) -> LexicalEvidenceProvider:
    """Load an explicitly requested installed Lexhint artifact without downloading."""
    try:
        from lexhint import Lexicon
    except ImportError as exc:
        raise RuntimeError("--lexhint requires the spokenform[lexhint] extra") from exc
    return Lexicon(
        base_language(language),
        variant=variant,
        dataset_version=dataset_version,
    )


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
    parser.add_argument(
        "--interpretation-mode",
        choices=tuple(mode.value for mode in InterpretationMode),
        default=InterpretationMode.CONTEXTUAL.value,
        help="Context evidence policy (default: contextual)",
    )
    parser.add_argument(
        "--sequence-fallback",
        choices=tuple(mode.value for mode in SequenceFallbackMode),
        default=SequenceFallbackMode.PRESERVE.value,
        help="Residual sequence fallback policy (default: preserve)",
    )
    parser.add_argument(
        "--disable-domain",
        action="append",
        choices=tuple(domain.value for domain in RecognitionDomain),
        default=[],
        help="Disable one semantic recognition domain; repeatable",
    )
    parser.add_argument(
        "--only-domain",
        action="append",
        choices=tuple(domain.value for domain in RecognitionDomain),
        default=None,
        help="Allow only one semantic recognition domain; repeatable",
    )
    parser.add_argument("--no-abbreviations", action="store_true")
    parser.add_argument("--no-structured", action="store_true")
    parser.add_argument("--no-numbers", action="store_true")
    parser.add_argument("--keep-whitespace", action="store_true")
    parser.add_argument("--normalize-literals", action="store_true")
    parser.add_argument(
        "--lexhint", action="store_true", help="Use an installed Lexhint runtime artifact"
    )
    parser.add_argument("--lexhint-variant", default="runtime", help="Lexhint artifact variant")
    parser.add_argument(
        "--lexhint-dataset-version", help="Require a specific Lexhint dataset version"
    )
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
        choices=("known-only", "conservative-unknown", "spell-unknown"),
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
        "--registered-acronyms",
        choices=("expand", "spell"),
        default="expand",
        help="Whether registered initialisms use their expansion or source letters",
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

    try:
        lexical_evidence = (
            _load_lexhint(
                args.lang,
                variant=args.lexhint_variant,
                dataset_version=args.lexhint_dataset_version,
            )
            if args.lexhint
            else None
        )
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        parser.error(str(exc))

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
        registered_acronym_mode=args.registered_acronyms,
        interpretation_mode=args.interpretation_mode,
        disabled_domains=set(args.disable_domain),
        allowed_domains=args.only_domain,
        sequence_fallback_mode=args.sequence_fallback,
        strict=args.strict,
        normalize_literals=args.normalize_literals,
        lexical_evidence=lexical_evidence,
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
