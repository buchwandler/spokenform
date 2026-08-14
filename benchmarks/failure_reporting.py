"""Shared benchmark failure-family and regression reporting helpers."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
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

OWNERSHIP_STATES = (
    "owned",
    "dependency-abbr2words",
    "extended-candidate",
    "protected",
    "downstream",
    "unsupported",
    "questionable-target",
    "external-language",
)

OUTCOME_BUCKETS = (
    "pass",
    "semantic-mismatch",
    "presentation-only",
    "dependency-mismatch",
    "protected-by-profile",
    "extended-candidate",
    "unsupported",
    "external-language",
    "questionable-target",
    "runtime-error",
    "identity-mutation",
)


def _edit_rank(edit: Any, *, protected: bool = False) -> int:
    """Rank an edit by semantic diagnostic value, not replacement size."""
    rule = str(getattr(edit, "rule", "") or "").casefold()
    stage = str(getattr(edit, "stage", "") or "").casefold()
    if protected or any(marker in rule for marker in ("url", "email", "version")):
        return 700
    if stage == "structured" or any(
        marker in rule
        for marker in (
            "sequence.",
            ".date",
            ".time",
            ".year",
            ".ordinal",
            ".quantity",
            ".currency",
            ".reference",
        )
    ):
        return 600
    if any(marker in rule for marker in ("abbr", "acronym", "initialism")):
        return 500
    if stage == "numbers" or any(marker in rule for marker in ("decimal", "number")):
        return 400
    if any(marker in rule or marker in stage for marker in ("symbol", "punctuation")):
        return 200
    if "space" in rule or "whitespace" in stage:
        return 100
    return 300


def rank_provenance(
    edits: Iterable[Any],
    *,
    semantic_failure: bool,
    presentation_only: bool,
    error: bool = False,
    protected_spans: Sequence[Any] = (),
) -> dict[str, Any]:
    """Select truthful benchmark provenance while preserving all rule evidence."""
    candidates = tuple(edit for edit in edits if getattr(edit, "rule", None))
    protected = tuple(protected_spans)

    def overlaps_protected(edit: Any) -> bool:
        start = int(getattr(edit, "source_start", 0))
        end = int(getattr(edit, "source_end", 0))
        return any(
            start < int(getattr(span, "end", 0))
            and int(getattr(span, "start", 0)) < end
            for span in protected
        )

    ranked = sorted(
        candidates,
        key=lambda edit: (
            -_edit_rank(edit, protected=overlaps_protected(edit)),
            -(int(getattr(edit, "source_end", 0)) - int(getattr(edit, "source_start", 0))),
            int(getattr(edit, "source_start", 0)),
        ),
    )
    rules = tuple(dict.fromkeys(str(edit.rule) for edit in ranked))
    winner = ranked[0] if ranked else None
    winner_is_cleanup = winner is not None and _edit_rank(winner) <= 200
    if error:
        primary = None
        reason = "runtime-error"
    elif semantic_failure and (winner is None or winner_is_cleanup):
        primary = None
        reason = "unrecognized-semantic-material"
    elif presentation_only:
        primary = getattr(winner, "rule", None) if winner is not None else None
        reason = "presentation-only"
    elif winner is None:
        primary = None
        reason = "pass"
    else:
        primary = str(getattr(winner, "rule", ""))
        if any(marker in primary.casefold() for marker in ("abbr", "acronym", "initialism")):
            reason = "dependency-initialism"
        elif _edit_rank(winner, protected=overlaps_protected(winner)) >= 600:
            reason = "semantic-rule"
        elif _edit_rank(winner) >= 400:
            reason = "locale-rendering"
        else:
            reason = "presentation-cleanup"
    span = (
        None
        if winner is None
        else {
            "start": int(getattr(winner, "source_start", 0)),
            "end": int(getattr(winner, "source_end", 0)),
            "source": str(getattr(winner, "source", "")),
            "rule": getattr(winner, "rule", None),
        }
    )
    if winner is not None and any(overlaps_protected(edit) for edit in ranked[:1]):
        phase = "protected"
    elif primary is None:
        phase = "runtime_error" if error else "unrecognized"
    elif _edit_rank(winner) >= 600:
        phase = "structured_rendering"
    elif _edit_rank(winner) >= 400:
        phase = "locale_rendering"
    else:
        phase = "downstream_rendering"
    return {
        "primary_rule": primary,
        "secondary_rules": list(rules[1:] if primary is not None else rules),
        "winning_span": span,
        "failure_phase": phase,
        "reason_code": reason,
    }


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
    if any(marker in category for marker in ("initialism", "acronym", "abbreviation")):
        return "acronym"
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
        return "dependency-abbr2words"
    if any(marker in value for marker in ("year", "date", "time", "quantity", "reference")):
        return "owned"
    if value.startswith("sequence."):
        return "extended-candidate"
    return "downstream"


def outcome_for_row(row: dict[str, Any]) -> str:
    """Return an explicit diagnostic outcome without changing pass/fail gates."""
    if row.get("quarantine") is not None:
        return str(row.get("quarantine", {}).get("reason_code", "questionable-target"))
    if row.get("error"):
        return "runtime-error"
    if row.get("case_kind") == "identity" and not row.get("speech_exact_equivalent", True):
        return "identity-mutation"
    if row.get("presentation_only"):
        return "presentation-only"
    ownership = row.get("ownership")
    if row.get("protected") or ownership == "protected":
        return "protected-by-profile"
    if ownership == "external-language":
        return "external-language"
    if ownership == "unsupported":
        return "unsupported"
    if ownership == "extended-candidate" and row.get("semantic_failure"):
        return "extended-candidate"
    if ownership == "dependency-abbr2words" and row.get("semantic_failure"):
        return "dependency-mismatch"
    if ownership == "questionable-target":
        return "questionable-target"
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
        "by_ownership": Counter(
            str(row.get("ownership") or ownership_for_rule(row.get("primary_rule")))
            for row in failed
        ),
        "by_ambiguity_family": Counter(failure_family(row) for row in failed),
        "by_outcome": Counter(outcome_for_row(row) for row in values),
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
    "OWNERSHIP_STATES",
    "OUTCOME_BUCKETS",
    "failure_family",
    "failure_family_counts",
    "diagnostic_aggregates",
    "ownership_for_rule",
    "outcome_for_row",
    "reason_code",
    "rank_provenance",
]
