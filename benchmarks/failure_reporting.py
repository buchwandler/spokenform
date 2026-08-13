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


__all__ = ["FAILURE_FAMILIES", "failure_family", "failure_family_counts", "reason_code"]
