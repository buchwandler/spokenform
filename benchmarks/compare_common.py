"""Small shared helpers for benchmark run comparisons."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any


def configuration_hash(configuration: dict[str, Any]) -> str:
    """Return a stable hash for settings that affect normalization."""
    payload = json.dumps(
        configuration, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def with_configuration_hash(environment: dict[str, Any]) -> dict[str, Any]:
    """Add a stable configuration hash to an environment fingerprint."""
    enriched = dict(environment)
    configuration = dict(enriched.get("configuration", {}))
    configuration["config_hash"] = configuration_hash(configuration)
    enriched["configuration"] = configuration
    enriched["config_hash"] = configuration["config_hash"]
    return enriched


def report_identity(summary: dict[str, Any]) -> dict[str, Any]:
    """Extract comparable identity fields from a benchmark summary."""
    environment = summary.get("environment", {})
    configuration = environment.get("configuration", {})
    return {
        "benchmark": summary.get("benchmark"),
        "dataset_repository": environment.get("dataset_repository"),
        "dataset_commit": summary.get("dataset_commit", environment.get("dataset_commit")),
        "spokenform_source_commit": environment.get("spokenform_source_commit"),
        "spokenform_version": environment.get("spokenform_version"),
        "abbr2words_version": environment.get("abbr2words_version"),
        "num2words_version": environment.get("num2words_version"),
        "locale_mapping": environment.get("locale_mapping"),
        "profile": summary.get("profile", configuration.get("profile")),
        "config_hash": environment.get("config_hash", configuration.get("config_hash")),
    }


def identity_mismatches(before: dict[str, Any], after: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Return fields that make a before/after comparison unsafe."""
    mismatches: dict[str, dict[str, Any]] = {}
    for field in (
        "benchmark",
        "dataset_repository",
        "dataset_commit",
        "locale_mapping",
        "profile",
        "config_hash",
    ):
        old, new = before.get(field), after.get(field)
        if old is None and new is None:
            continue
        if old != new:
            mismatches[field] = {"before": old, "after": new}
    return mismatches


def ensure_compatible(
    before_summary: dict[str, Any],
    after_summary: dict[str, Any],
    *,
    allow_incompatible: bool = False,
) -> dict[str, Any]:
    """Validate run identity, optionally allowing an intentional comparison."""
    before = report_identity(before_summary)
    after = report_identity(after_summary)
    mismatches = identity_mismatches(before, after)
    if mismatches and not allow_incompatible:
        fields = ", ".join(sorted(mismatches))
        raise ValueError(
            "incompatible benchmark runs; mismatched identity fields: "
            f"{fields}. Pass allow_incompatible=True only for an intentional cross-profile comparison."
        )
    return {
        "compatible": not mismatches,
        "overridden": bool(mismatches and allow_incompatible),
        "mismatches": mismatches,
        "before": before,
        "after": after,
    }


def load_run(path: str | Path) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    root = Path(path)
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))
    rows_path = root / "rows.jsonl"
    rows = tuple(
        json.loads(line)
        for line in rows_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    return summary, rows


def compare_runs(before: str | Path, after: str | Path) -> dict[str, Any]:
    """Compare stable sentence IDs and outcome/class counts between runs."""
    before_summary, before_rows = load_run(before)
    after_summary, after_rows = load_run(after)
    before_sentences = {row["id"]: row for row in before_rows if "record_type" not in row}
    after_sentences = {row["id"]: row for row in after_rows if "record_type" not in row}
    before_failures = {
        case_id
        for case_id, row in before_sentences.items()
        if row.get("error") or not row.get("speech_exact") or row.get("presentation_only")
    }
    after_failures = {
        case_id
        for case_id, row in after_sentences.items()
        if row.get("error") or not row.get("speech_exact") or row.get("presentation_only")
    }

    def outcome_counts(rows: tuple[dict[str, Any], ...]) -> dict[str, int]:
        return dict(Counter(row["normalization_outcome"] for row in rows if row.get("record_type") == "span"))

    def class_counts(rows: tuple[dict[str, Any], ...]) -> dict[str, dict[str, int]]:
        grouped: dict[str, Counter[str]] = defaultdict(Counter)
        for row in rows:
            if row.get("record_type") == "span":
                grouped[row["semiotic_class"]][row["normalization_outcome"]] += 1
        return {key: dict(sorted(value.items())) for key, value in sorted(grouped.items())}

    def class_delta(
        before_values: dict[str, dict[str, int]], after_values: dict[str, dict[str, int]]
    ) -> dict[str, dict[str, int]]:
        classes = set(before_values) | set(after_values)
        return {
            class_name: delta(
                before_values.get(class_name, {}), after_values.get(class_name, {})
            )
            for class_name in sorted(classes)
        }

    def delta(before_values: dict[str, int], after_values: dict[str, int]) -> dict[str, int]:
        keys = set(before_values) | set(after_values)
        return {key: after_values.get(key, 0) - before_values.get(key, 0) for key in sorted(keys)}

    before_classes = class_counts(before_rows)
    after_classes = class_counts(after_rows)
    return {
        "before": str(before),
        "after": str(after),
        "aggregate_delta": {
            key: after_summary.get(key, 0) - before_summary.get(key, 0)
            for key in (
                "evaluated", "literal_exact", "speech_exact", "speech_exact_equivalent",
                "transform_miss_count", "wrong_transform_count", "identity_mutation_count",
            )
        },
        "outcome_delta": delta(outcome_counts(before_rows), outcome_counts(after_rows)),
        "by_class_before": before_classes,
        "by_class_after": after_classes,
        "by_class_delta": class_delta(before_classes, after_classes),
        "resolved_ids": sorted(before_failures - after_failures),
        "new_failure_ids": sorted(after_failures - before_failures),
        "remaining_failure_ids": sorted(before_failures & after_failures),
    }


__all__ = ["compare_runs", "load_run"]
