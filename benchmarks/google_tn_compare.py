"""Compare two Google TN benchmark result directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .compare_common import compare_runs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare two Google TN benchmark runs.")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args(argv)
    print(
        json.dumps(
            compare_runs(args.before, args.after), ensure_ascii=False, indent=2, sort_keys=True
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
