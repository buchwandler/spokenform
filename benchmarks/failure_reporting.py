"""Shared benchmark failure-family and regression reporting helpers."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable
from typing import Any

FAILURE_FAMILIES = (
    "acronym",
    "year",
    "date",
    "quantity-ambiguity",
    "product-false-positive",
    "version-protected",
    "roman",
    "ticker",
    "identifier",
    "score",
    "protected-literal",
    "dataset-quarantine",
    "unrecognized",
    "other",
)


def failure_family(row: dict[str, Any]) -> str:
    """Classify one diagnostic row without changing the upstream category."""
    if row.get("quarantine") is not None:
        return "dataset-quarantine"
    category = str(row.get("canonical_category", row.get("category", ""))).casefold()
    rule = str(row.get("primary_rule") or row.get("source_rule") or "").casefold()
    source = str(row.get("original_text", ""))
    if "url" in category or "email" in category or ".url" in rule or ".email" in rule:
        return "protected-literal"
    if "version" in category or ".version" in rule:
        return "version-protected"
    if "ticker" in category or ".ticker" in rule:
        return "ticker"
    if "roman" in category or ".roman" in rule:
        return "roman"
    if "score" in category or "sports" in rule or "chained-score" in rule:
        return "score"
    if "date" in category or ".date" in rule:
        return "date"
    if "year" in category or ".year" in rule:
        return "year"
    if "quantity" in rule or "unit" in category:
        return "quantity-ambiguity"
    if any(marker in rule for marker in ("acronym", "initialism", "abbr")):
        return "acronym"
    if any(marker in rule for marker in ("product", "plate", "vin", "serial", "isbn")):
        if re.search(r"\b(?:registration|model|product|part|tag|identifier)\b", source, re.I):
            return "product-false-positive"
        return "identifier"
    if any(marker in category for marker in ("product", "license plate", "serial", "isbn")):
        return "identifier"
    if row.get("error"):
        return "unrecognized"
    return "other"


def failure_family_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Count diagnostic families for rows that are not fully successful."""
    failed = (
        row
        for row in rows
        if row.get("error") or row.get("semantic_failure") or row.get("presentation_only")
    )
    counts = Counter(failure_family(row) for row in failed)
    return {family: counts[family] for family in FAILURE_FAMILIES if counts[family]}


def ownership_for_rule(rule: str | None, *, protected: bool = False) -> str:
    """Classify runtime rule ownership for adapters without source categories."""
    value = (rule or "").casefold()
    if protected or ".url" in value or ".email" in value or ".version" in value:
        return "protected"
    if not value:
        return "unrecognized"
    if any(marker in value for marker in ("abbr", "acronym", "initialism")):
        return "owned"
    if any(marker in value for marker in ("year", "date", "time", "quantity", "reference")):
        return "owned"
    if value.startswith("sequence."):
        return "extended-candidate"
    return "downstream"


def outcome_for_row(row: dict[str, Any]) -> str:
    """Return an explicit diagnostic outcome without changing pass/fail gates."""
    if row.get("quarantine") is not None:
        return str(row.get("quarantine", {}).get("classification", "questionable-target"))
    if row.get("error"):
        return "runtime-error"
    if row.get("presentation_only"):
        return "presentation-only"
    if row.get("protected") or row.get("ownership") == "protected":
        return "protected-by-profile"
    if row.get("semantic_failure"):
        return "semantic-mismatch"
    return "pass"


def diagnostic_aggregates(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, int]]:
    """Return stable failure counts by rule, phase, ownership, and family."""
    values = tuple(rows)
    failed = tuple(
        row
        for row in values
        if row.get("error") or row.get("semantic_failure") or row.get("presentation_only")
    )
    dimensions = {
        "by_rule": Counter(str(row.get("primary_rule") or "unrecognized") for row in failed),
        "by_phase": Counter(str(row.get("failure_phase") or "unrecognized") for row in failed),
        "by_ownership": Counter(str(row.get("ownership") or ownership_for_rule(row.get("primary_rule"))) for row in failed),
        "by_ambiguity_family": Counter(failure_family(row) for row in failed),
    }
    return {name: dict(sorted(counts.items())) for name, counts in dimensions.items()}


def reason_code(reason: str) -> str:
    """Map free-form exclusion text to a stable quarantine code."""
    value = reason.casefold()
    if "source" in value or "missing" in value or "absent" in value:
        return "source-incomplete"
    if "adapter" in value:
        return "adapter-error"
    if "ground" in value or "target" in value or "unrelated" in value:
        return "malformed-ground-truth"
    return "questionable-target"


__all__ = [
    "FAILURE_FAMILIES",
    "failure_family",
    "failure_family_counts",
    "diagnostic_aggregates",
    "ownership_for_rule",
    "outcome_for_row",
    "reason_code",
]
