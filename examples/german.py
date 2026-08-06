#!/usr/bin/env python3
"""Prepare German written text for speech with optional spaCy annotations."""

from __future__ import annotations

import argparse
import json
import sys

from spokenform import prepare

TEXT = "Prof. Klein bringt am 14.05.2026 um 18:20 Uhr 2 kg Äpfel für 12,80 EUR mit."


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("text", nargs="?", default=TEXT, help="German text to prepare")
    parser.add_argument(
        "--spacy-model",
        help="Installed spaCy model, for example de_core_news_sm",
    )
    parser.add_argument(
        "--no-context",
        action="store_true",
        help="Disable context-aware abbreviation expansion",
    )
    parser.add_argument("--json", action="store_true", help="Print the structured result")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the German example."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8")

    args = _parser().parse_args(argv)
    prepared = prepare(
        args.text,
        language="de",
        context=not args.no_context,
        spacy_model=args.spacy_model,
    )

    if args.json:
        print(json.dumps(prepared.to_dict(), ensure_ascii=False, indent=2))
    else:
        print("=== Source ===")
        print(prepared.source_text)
        print("\n=== Spoken form ===")
        print(prepared.spoken_text)
        print("\n=== Changes ===")
        print(prepared.render_changes())
        if prepared.warnings:
            print("\n=== Warnings ===")
            print("\n".join(prepared.warnings))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
