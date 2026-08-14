"""Compare two local PolyNorm benchmark result directories."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .compare_common import ensure_compatible
from .failure_reporting import FAILURE_FAMILIES


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


def _rows(directory: Path) -> dict[str, dict[str, Any]]:
    path = directory / "rows.jsonl"
    if not path.is_file():
        path = directory / "failures.jsonl"
    if not path.is_file():
        return {}
    return {
        row["id"]: row
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
        for row in (json.loads(line),)
    }


def _failed(row: dict[str, Any] | None) -> bool:
    return bool(row and (row.get("error") or row.get("semantic_failure")))


def _diff_rows(
    before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {
        key: []
        for key in (
            "fixed",
            "regressed",
            "unchanged_failure",
            "newly_changed_but_still_wrong",
            "presentation_only_change",
        )
    }
    for case_id in sorted(set(before) | set(after)):
        old, new = before.get(case_id), after.get(case_id)
        if old is None or new is None:
            continue
        old_failed, new_failed = _failed(old), _failed(new)
        payload = {
            "id": case_id,
            "old_actual": old.get("actual", ""),
            "new_actual": new.get("actual", ""),
            "expected": new.get("expected", old.get("expected", "")),
            "old_speech_wer": old.get("speech_wer", 0.0),
            "new_speech_wer": new.get("speech_wer", 0.0),
            "old_primary_rule": old.get("primary_rule"),
            "new_primary_rule": new.get("primary_rule"),
            "old_winning_span": old.get("winning_span"),
            "new_winning_span": new.get("winning_span"),
            "old_profile": old.get("profile"),
            "new_profile": new.get("profile"),
        }
        if old_failed and not new_failed:
            result["fixed"].append(payload)
        elif not old_failed and new_failed:
            result["regressed"].append(payload)
        elif old_failed and new_failed:
            if new.get("presentation_only") or (
                old.get("speech_exact_equivalent") and new.get("speech_exact_equivalent")
            ):
                result["presentation_only_change"].append(payload)
            elif old.get("actual") != new.get("actual"):
                result["newly_changed_but_still_wrong"].append(payload)
            else:
                result["unchanged_failure"].append(payload)
    return result


def compare_runs(
    before: Path | str, after: Path | str, *, allow_incompatible: bool = False
) -> dict[str, Any]:
    """Return aggregate and case-id failure deltas for two benchmark runs."""
    before_dir = Path(before)
    after_dir = Path(after)
    before_summary = _read_summary(before_dir)
    after_summary = _read_summary(after_dir)
    identity = ensure_compatible(
        before_summary, after_summary, allow_incompatible=allow_incompatible
    )
    before_failures = _failure_ids(before_dir)
    after_failures = _failure_ids(after_dir)
    diffs = _diff_rows(_rows(before_dir), _rows(after_dir))
    return {
        "before": str(before_dir),
        "after": str(after_dir),
        "identity": identity,
        "summary_delta": {
            "semantic_failure_count": after_summary["semantic_failure_count"]
            - before_summary["semantic_failure_count"],
            "speech_exact_equivalent_count": after_summary["speech_exact_equivalent_count"]
            - before_summary["speech_exact_equivalent_count"],
            "literal_exact_count": after_summary["literal_exact_count"]
            - before_summary["literal_exact_count"],
        },
        "failure_family_delta": {
            family: after_summary.get("failure_families", {}).get(family, 0)
            - before_summary.get("failure_families", {}).get(family, 0)
            for family in FAILURE_FAMILIES
            if (
                after_summary.get("failure_families", {}).get(family, 0)
                or before_summary.get("failure_families", {}).get(family, 0)
            )
        },
        "case_delta": {
            "resolved": sorted(before_failures - after_failures),
            "new_failures": sorted(after_failures - before_failures),
            "remaining": sorted(before_failures & after_failures),
        },
        "regression_delta": {
            "resolved_count": len(before_failures - after_failures),
            "new_failure_count": len(after_failures - before_failures),
            "remaining_count": len(before_failures & after_failures),
        },
        "diff_classification": diffs,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument(
        "--allow-incompatible",
        action="store_true",
        help="Allow intentional cross-profile or cross-dataset comparisons.",
    )
    args = parser.parse_args(argv)
    print(
        json.dumps(
            compare_runs(args.before, args.after, allow_incompatible=args.allow_incompatible),
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["compare_runs"]
