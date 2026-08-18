"""Compare two compatible Async TN benchmark runs."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from .compare_common import configuration_hash

_REQUIRED_IDENTITY_FIELDS = (
    "benchmark",
    "dataset_repository",
    "dataset_commit",
    "dataset_files",
    "suite",
    "locale_mapping",
    "profile",
    "config_hash",
)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    if not path.is_file():
        return ()
    return tuple(
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    )


def _summary_identity(summary: dict[str, Any]) -> dict[str, Any]:
    environment = summary.get("environment", {})
    configuration = dict(environment.get("configuration", {}))
    source = summary.get("source", {})
    files = source.get("files", {})
    return {
        "benchmark": summary.get("benchmark"),
        "dataset_repository": source.get("source_repo", environment.get("dataset_repository")),
        "dataset_commit": summary.get("dataset_commit", environment.get("dataset_commit")),
        "dataset_files": files,
        "suite": configuration.get("suite"),
        "locale_mapping": environment.get("locale_mapping"),
        "profile": summary.get("profile", configuration.get("profile")),
        "config_hash": environment.get("config_hash") or configuration_hash(configuration),
    }


def ensure_compatible(
    before: dict[str, Any], after: dict[str, Any], *, allow_incompatible: bool = False
) -> dict[str, Any]:
    """Reject changed corpus or evaluation configuration by default."""
    before_identity = _summary_identity(before)
    after_identity = _summary_identity(after)
    mismatches = {
        field: {"before": before_identity.get(field), "after": after_identity.get(field)}
        for field in _REQUIRED_IDENTITY_FIELDS
        if before_identity.get(field) != after_identity.get(field)
    }
    if mismatches and not allow_incompatible:
        raise ValueError(
            "incompatible Async TN runs; mismatched identity fields: "
            + ", ".join(sorted(mismatches))
            + ". Pass --allow-incompatible only for an intentional comparison."
        )
    return {
        "compatible": not mismatches,
        "overridden": bool(mismatches and allow_incompatible),
        "mismatches": mismatches,
        "before": before_identity,
        "after": after_identity,
    }


def _failed(row: dict[str, Any]) -> bool:
    return bool(row.get("error") or not row.get("speech_equivalent", True))


def _group_counts(rows: tuple[dict[str, Any], ...], *fields: str) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})
    for row in rows:
        key = "/".join(str(row.get(field, "unknown")) for field in fields)
        counts[key]["total"] += 1
        counts[key]["correct"] += int(bool(row.get("speech_equivalent")))
    return {key: value for key, value in sorted(counts.items())}


def _delta(
    before: dict[str, dict[str, int]], after: dict[str, dict[str, int]]
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for key in sorted(set(before) | set(after)):
        result[key] = {
            field: after.get(key, {}).get(field, 0) - before.get(key, {}).get(field, 0)
            for field in ("total", "correct")
        }
    return result


def compare_runs(
    before: Path | str, after: Path | str, *, allow_incompatible: bool = False
) -> dict[str, Any]:
    """Return stable case, unit, language, and category deltas."""
    before_dir, after_dir = Path(before), Path(after)
    before_summary, after_summary = (
        _read_json(before_dir / "summary.json"),
        _read_json(after_dir / "summary.json"),
    )
    identity = ensure_compatible(
        before_summary, after_summary, allow_incompatible=allow_incompatible
    )
    before_rows = {
        row["id"]: row
        for row in _read_jsonl(before_dir / "rows.jsonl")
        if row.get("record_type") == "sentence" or "record_type" not in row
    }
    after_rows = {
        row["id"]: row
        for row in _read_jsonl(after_dir / "rows.jsonl")
        if row.get("record_type") == "sentence" or "record_type" not in row
    }
    before_units = {row["unit_id"]: row for row in _read_jsonl(before_dir / "units.jsonl")}
    after_units = {row["unit_id"]: row for row in _read_jsonl(after_dir / "units.jsonl")}
    before_failed = {key for key, row in before_rows.items() if _failed(row)}
    after_failed = {key for key, row in after_rows.items() if _failed(row)}
    before_unit_failed = {key for key, row in before_units.items() if _failed(row)}
    after_unit_failed = {key for key, row in after_units.items() if _failed(row)}
    before_languages = tuple(before_units.values())
    after_languages = tuple(after_units.values())
    before_categories = _group_counts(before_languages, "category")
    after_categories = _group_counts(after_languages, "category")
    before_language = _group_counts(before_languages, "source_language")
    after_language = _group_counts(after_languages, "source_language")
    before_language_category = _group_counts(before_languages, "source_language", "category")
    after_language_category = _group_counts(after_languages, "source_language", "category")
    before_quarantine = {key for key, row in before_units.items() if not row.get("scorable", True)}
    after_quarantine = {key for key, row in after_units.items() if not row.get("scorable", True)}
    return {
        "before": str(before_dir),
        "after": str(after_dir),
        "identity": identity,
        "summary_delta": {
            "sentence_speech_equivalent": after_summary.get("sentence_metrics", {}).get(
                "speech_equivalent", 0
            )
            - before_summary.get("sentence_metrics", {}).get("speech_equivalent", 0),
            "unit_correct": after_summary.get("unit_metrics", {}).get("units_correct", 0)
            - before_summary.get("unit_metrics", {}).get("units_correct", 0),
            "unit_scorable": after_summary.get("unit_metrics", {}).get("units_scorable", 0)
            - before_summary.get("unit_metrics", {}).get("units_scorable", 0),
        },
        "language_delta": _delta(before_language, after_language),
        "category_delta": _delta(before_categories, after_categories),
        "language_category_delta": _delta(before_language_category, after_language_category),
        "case_delta": {
            "resolved": sorted(before_failed - after_failed),
            "new_failures": sorted(after_failed - before_failed),
            "remaining": sorted(before_failed & after_failed),
        },
        "unit_delta": {
            "resolved": sorted(before_unit_failed - after_unit_failed),
            "new_failures": sorted(after_unit_failed - before_unit_failed),
            "remaining": sorted(before_unit_failed & after_unit_failed),
        },
        "quarantine_delta": {
            "resolved": sorted(before_quarantine - after_quarantine),
            "new": sorted(after_quarantine - before_quarantine),
            "remaining": sorted(before_quarantine & after_quarantine),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--allow-incompatible", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = compare_runs(args.before, args.after, allow_incompatible=args.allow_incompatible)
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


__all__ = ["compare_runs", "ensure_compatible", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
