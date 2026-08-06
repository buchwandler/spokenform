#!/usr/bin/env python3
"""Load an English spaCy model and supply aligned lexical annotations."""

from __future__ import annotations

import argparse

from spokenform import prepare


def main() -> int:
    """Run the spaCy-backed English example."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default="en_core_web_sm",
        help="Name or path accepted by spacy.load()",
    )
    parser.add_argument("text", nargs="?", default="The board is 2 in. wide.")
    args = parser.parse_args()

    prepared = prepare(
        args.text,
        language="en",
        spacy_model=args.model,
        strict=True,
    )
    print(prepared.spoken_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
