"""Shared benchmark failure-family and regression reporting helpers."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Any

FAILURE_FAMILIES = (
    "acronym",
    "time",
    "currency",
    "exchange-rate",
    "math",
    "scientific",
    "fraction",
    "social-hashtag",
    "social-mention",
    "legal-reference",
    "year",
    "date",
    "quantity-ambiguity",
    "product-false-positive",
    "version-protected",
    "roman",
    "ticker",
    "phone",
    "isbn",
    "iban",
    "mac",
    "vin",
    "biomedical",
    "identifier",
    "code-product",
    "symbol-punctuation",
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

RISK_TIERS = ("low", "medium", "high")

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
            start < int(getattr(span, "end", 0)) and int(getattr(span, "start", 0)) < end
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
    """Classify failures from provenance without changing upstream categories."""
    if row.get("quarantine") is not None:
        return "dataset-quarantine"
    category = str(row.get("canonical_category", row.get("category", ""))).casefold()
    rule = str(row.get("primary_rule") or row.get("source_rule") or "").casefold()
    source = str(row.get("original_text", ""))
    haystack = f"{category} {rule}"
    if (
        row.get("error")
        or row.get("semantic_failure")
    ) and (row.get("failure_phase") == "unrecognized" or category == "unrecognized"):
        return "unrecognized"
    if row.get("ownership") == "protected" or any(
        marker in haystack for marker in ("url", "email", "protected-literal")
    ):
        return "protected-literal"
    if "version" in category or ".version" in rule:
        return "version-protected"
    if any(marker in category for marker in ("initialism", "acronym", "abbreviation")):
        return "acronym"
    if any(marker in rule for marker in ("acronym", "initialism", "abbr")):
        return "acronym"
    if "ticker" in category or ".ticker" in rule:
        return "ticker"
    if "roman" in category or ".roman" in rule:
        return "roman"
    if "score" in category or "sports" in rule or "chained-score" in rule:
        return "score"
    if "exchange-rate" in haystack or "exchange rate" in category:
        return "exchange-rate"
    if "currency" in category or ".currency" in rule:
        return "currency"
    if "time" in category or ".time" in rule:
        return "time"
    if "scientific" in category or ".scientific" in rule:
        return "scientific"
    if "math" in category or "mathematical" in category or ".math" in rule:
        return "math"
    if "fraction" in category or ".fraction" in rule:
        return "fraction"
    if "hashtag" in category or "social-hashtag" in rule:
        return "social-hashtag"
    if "mention" in category or "social-mention" in rule:
        return "social-mention"
    if any(marker in category or marker in rule for marker in ("legal", "reference")):
        return "legal-reference"
    if "date" in category or ".date" in rule:
        return "date"
    if "year" in category or ".year" in rule:
        return "year"
    if "quantity" in rule or "unit" in category:
        return "quantity-ambiguity"
    if ".phone" in rule or "phone" in category:
        return "phone"
    if ".isbn" in rule or "isbn" in category:
        return "isbn"
    if ".iban" in rule or "iban" in category:
        return "iban"
    if ".mac" in rule or "mac address" in category:
        return "mac"
    if ".vin" in rule or " vin" in f" {category}":
        return "vin"
    if "biomedical" in category or ".biomedical" in rule or "biology" in category:
        return "biomedical"
    if any(marker in rule for marker in ("product", "plate", "serial", "code")):
        if re.search(r"\b(?:registration|model|product|part|tag|identifier)\b", source, re.I):
            return "product-false-positive"
        if "product" in rule or "code" in rule:
            return "code-product"
        return "identifier"
    if any(marker in category for marker in ("product", "license plate", "serial")):
        return "identifier"
    if any(marker in category or marker in rule for marker in ("symbol", "punctuation")):
        return "symbol-punctuation"
    if row.get("error") or not row.get("primary_rule") and row.get("semantic_failure"):
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


def risk_tier_for_row(row: dict[str, Any]) -> str:
    """Classify benchmark follow-up risk without changing runtime behavior."""
    haystack = " ".join(
        str(row.get(field, ""))
        for field in (
            "category",
            "canonical_category",
            "primary_rule",
            "source_rule",
            "failure_phase",
            "reason_code",
            "render_mode",
            "ownership",
        )
    ).casefold()
    ownership = str(row.get("ownership") or "").casefold()
    if ownership in {"external-language", "unsupported", "questionable-target"}:
        return "low"
    if any(
        marker in haystack
        for marker in (
            "abbr",
            "acronym",
            "initialism",
            "identifier",
            "isbn",
            "ticker",
            "url",
            "email",
            "version",
            "unrecognized",
            "runtime-error",
            "parse_error",
            "questionable-target",
        )
    ):
        return "high"
    if any(
        marker in haystack
        for marker in (
            "year",
            "decade",
            "range",
            "product",
            "model",
            "plate",
            "vin",
            "biology",
            "biomedical",
            "roman",
            "sports",
            "address",
            "duration",
            "reference",
            "legal",
        )
    ):
        return "medium"
    if row.get("presentation_only") and not row.get("semantic_failure") and not row.get("error"):
        return "low"
    if any(
        marker in haystack
        for marker in (
            "cardinal",
            "currency",
            "date",
            "time",
            "ordinal",
            "quantity",
            "decimal",
            "number",
            "fraction",
            "percent",
            "coordinate",
            "math",
            "structured_rendering",
            "locale_rendering",
        )
    ):
        return "low"
    if row.get("semantic_failure") and not row.get("primary_rule"):
        return "high"
    if row.get("semantic_failure"):
        return "medium"
    return "low"


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
        "by_risk_tier": Counter(
            str(row.get("risk_tier") or risk_tier_for_row(row)) for row in failed
        ),
        "by_ambiguity_family": Counter(failure_family(row) for row in failed),
        "by_gap_type": Counter(failure_gap_type(row) for row in failed),
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


def oracle_gap_type(row: dict[str, Any]) -> str:
    """Classify one oracle-enabled row with conservative ownership gates."""
    if row.get("error"):
        return "runtime-error"
    if row.get("presentation_only") and not row.get("semantic_failure"):
        return "presentation"
    ownership = str(row.get("ownership") or "")
    if row.get("quarantine") is not None or ownership in {
        "protected",
        "downstream",
        "unsupported",
        "questionable-target",
        "external-language",
    }:
        return "policy"
    if ownership == "dependency-abbr2words":
        return "dependency"
    if row.get("oracle_truncated"):
        return "oracle-truncated"
    if not row.get("oracle_scorable", False):
        return "oracle-unscorable"
    if int(row.get("ambiguous_component_count", 0)) == 0:
        return "no-ambiguous-candidates"
    if float(row.get("selector_regret", 0.0)) > 0:
        return "selection"
    return "candidates-no-gain"


def failure_gap_type(row: dict[str, Any]) -> str:
    """Classify actionable ownership and oracle gaps from row evidence."""
    if row.get("error") or row.get("reason_code") == "runtime-error":
        return "runtime-error"
    if row.get("quarantine") is not None:
        reason = str(row.get("quarantine", {}).get("reason_code", ""))
        return "questionable-target" if "questionable" in reason else "external/questionable-target"
    ownership = str(row.get("ownership") or "")
    if row.get("presentation_only") and not row.get("semantic_failure"):
        return "presentation-only"
    if ownership == "protected" or row.get("protected"):
        return "policy-gap"
    if ownership == "dependency-abbr2words":
        return "dependency-gap"
    if ownership == "external-language":
        return "external/questionable-target"
    if ownership == "downstream":
        return "downstream-gap"
    oracle_type = str(row.get("oracle_gap_type") or "")
    if oracle_type == "selection":
        return "selection-gap"
    if oracle_type in {"policy", "presentation"}:
        return "policy-gap"
    phase = str(row.get("failure_phase") or "")
    if phase in {"structured_rendering", "locale_rendering"}:
        return "rendering-gap"
    if phase == "downstream_rendering":
        return "downstream-gap"
    if phase == "unrecognized" or not row.get("primary_rule"):
        return "recognition-gap"
    if phase == "protected":
        return "policy-gap"
    return "rejection-gap" if row.get("recognition_trace") else "other-owned"

def oracle_aggregates(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarize selector headroom with explicit semantic-failure denominators."""
    values = tuple(rows)
    eligible = tuple(
        row
        for row in values
        if oracle_gap_type(row) not in {"dependency", "policy", "presentation", "runtime-error"}
    )
    semantic_failures = tuple(
        row for row in eligible if bool(row.get("semantic_failure", True))
    )
    scorable = tuple(row for row in eligible if row.get("oracle_scorable"))
    regret_sum = sum(float(row.get("selector_regret", 0.0)) for row in scorable)
    eligible_count = len(eligible)
    eligible_semantic_failure_count = len(semantic_failures)
    scorable_count = len(scorable)
    exact_target_count = sum(bool(row.get("oracle_literal_exact")) for row in eligible)
    selection_gap_count = sum(
        oracle_gap_type(row) == "selection" for row in semantic_failures
    )
    fully_recoverable_count = sum(
        oracle_gap_type(row) == "selection" and bool(row.get("oracle_speech_equivalent"))
        for row in semantic_failures
    )
    return {
        "schema_version": 2,
        "enabled": True,
        "cases": len(values),
        "eligible_cases": eligible_count,
        "eligible_semantic_failure_count": eligible_semantic_failure_count,
        "scorable_cases": scorable_count,
        "unscorable_cases": sum(not row.get("oracle_scorable", False) for row in eligible),
        "truncated_cases": sum(bool(row.get("oracle_truncated")) for row in eligible),
        "cases_with_ambiguous_candidates": sum(
            int(row.get("ambiguous_component_count", 0)) > 0 for row in eligible
        ),
        "selection_gap_count": selection_gap_count,
        "selection_gap_rate_numerator": selection_gap_count,
        "selection_gap_rate_denominator": eligible_semantic_failure_count,
        "selection_gap_rate": (
            selection_gap_count / eligible_semantic_failure_count
            if eligible_semantic_failure_count
            else 0.0
        ),
        "fully_recoverable_selection_gap_count": fully_recoverable_count,
        "fully_recoverable_selection_gap_rate_numerator": fully_recoverable_count,
        "fully_recoverable_selection_gap_rate_denominator": eligible_semantic_failure_count,
        "fully_recoverable_selection_gap_rate": (
            fully_recoverable_count / eligible_semantic_failure_count
            if eligible_semantic_failure_count
            else 0.0
        ),
        "actual_speech_wer_sum": sum(float(row.get("actual_speech_wer", 0.0)) for row in scorable),
        "oracle_speech_wer_sum": sum(float(row.get("oracle_speech_wer", 0.0)) for row in scorable),
        "selector_regret_sum": regret_sum,
        "selector_regret_mean": regret_sum / scorable_count if scorable_count else 0.0,
        "candidate_recall_for_exact_target": (
            exact_target_count / eligible_count if eligible_count else 0.0
        ),
        "combinations_evaluated": sum(
            int(row.get("combinations_evaluated", 0)) for row in eligible
        ),
        "max_combinations_for_one_case": max(
            (int(row.get("combinations_evaluated", 0)) for row in eligible),
            default=0,
        ),
    }


__all__ = [
    "FAILURE_FAMILIES",
    "OWNERSHIP_STATES",
    "RISK_TIERS",
    "OUTCOME_BUCKETS",
    "failure_family",
    "failure_family_counts",
    "diagnostic_aggregates",
    "failure_gap_type",
    "oracle_aggregates",
    "oracle_gap_type",
    "ownership_for_rule",
    "outcome_for_row",
    "risk_tier_for_row",
    "reason_code",
    "rank_provenance",
]
