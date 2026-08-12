"""Compare two local Proteno benchmark result directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _read_summary(directory: Path) -> dict[str, Any]:
    return json.loads((directory / "summary.json").read_text(encoding="utf-8"))


def _failure_ids(directory: Path) -> set[str]:
    path = directory / "failures.jsonl"
    if not path.is_file():
        return set()
    return {
        json.loads(line)["id"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def compare_runs(before: Path | str, after: Path | str) -> dict[str, Any]:
    """Return requested metric and stable case-ID deltas."""
    before_dir = Path(before)
    after_dir = Path(after)
    before_summary = _read_summary(before_dir)
    after_summary = _read_summary(after_dir)
    before_failures = _failure_ids(before_dir)
    after_failures = _failure_ids(after_dir)
    fields = (
        "semantic_failure_count",
        "speech_exact_equivalent_count",
        "literal_exact_count",
        "identity_mutation_count",
        "normalization_unchanged_miss_count",
    )
    return {
        "before": str(before_dir),
        "after": str(after_dir),
        "summary_delta": {
            field: after_summary.get(field, 0) - before_summary.get(field, 0) for field in fields
        },
        "case_delta": {
            "resolved": sorted(before_failures - after_failures),
            "new_failures": sorted(after_failures - before_failures),
            "remaining": sorted(before_failures & after_failures),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args(argv)
    print(json.dumps(compare_runs(args.before, args.after), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["compare_runs"]
