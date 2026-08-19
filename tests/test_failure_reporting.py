from types import SimpleNamespace

from benchmarks.failure_reporting import (
    diagnostic_aggregates,
    failure_family,
    failure_gap_type,
    oracle_aggregates,
    oracle_gap_type,
    outcome_for_row,
    ownership_for_rule,
    rank_provenance,
    risk_tier_for_row,
 )


def _edit(rule: str, stage: str, start: int, end: int, source: str = "value"):
    return SimpleNamespace(
        rule=rule,
        stage=stage,
        source_start=start,
        source_end=end,
        source=source,
    )


def test_semantic_provenance_outranks_incidental_symbol_cleanup() -> None:
    diagnostics = rank_provenance(
        (
            _edit("symbol.remove", "symbols", 4, 5, ":"),
            _edit("sequence.time", "structured", 0, 4, "12:30"),
        ),
        semantic_failure=True,
        presentation_only=False,
    )

    assert diagnostics["primary_rule"] == "sequence.time"
    assert diagnostics["secondary_rules"] == ["symbol.remove"]
    assert diagnostics["reason_code"] == "semantic-rule"


def test_cleanup_only_failure_is_reported_as_unrecognized() -> None:
    diagnostics = rank_provenance(
        (_edit("symbol.remove", "symbols", 3, 4, "."),),
        semantic_failure=True,
        presentation_only=False,
    )

    assert diagnostics["primary_rule"] is None
    assert diagnostics["secondary_rules"] == ["symbol.remove"]
    assert diagnostics["failure_phase"] == "unrecognized"
    assert diagnostics["reason_code"] == "unrecognized-semantic-material"


def test_abbreviation_provenance_is_dependency_owned() -> None:
    diagnostics = rank_provenance(
        (_edit("abbr:initialism", "abbreviations", 0, 3, "NASA"),),
        semantic_failure=False,
        presentation_only=False,
    )

    assert diagnostics["reason_code"] == "dependency-initialism"
    assert ownership_for_rule(diagnostics["primary_rule"]) == "dependency-abbr2words"


def test_outcome_buckets_keep_dependency_and_profile_failures_separate() -> None:
    assert outcome_for_row({"error": "RuntimeError"}) == "runtime-error"
    assert outcome_for_row({"ownership": "dependency-abbr2words", "semantic_failure": True}) == (
        "dependency-mismatch"
    )
    assert outcome_for_row({"ownership": "protected", "semantic_failure": True}) == (
        "protected-by-profile"
    )
    assert outcome_for_row({"ownership": "unsupported", "semantic_failure": True}) == (
        "unsupported"
    )


def test_risk_tiers_distinguish_safe_contextual_and_high_risk_followups() -> None:
    assert risk_tier_for_row({"primary_rule": "en.currency", "semantic_failure": True}) == "low"
    assert risk_tier_for_row({"primary_rule": "sequence.year", "semantic_failure": True}) == (
        "medium"
    )
    assert risk_tier_for_row({"primary_rule": "abbr:initialism", "semantic_failure": True}) == (
        "high"
    )
    assert risk_tier_for_row({"presentation_only": True, "semantic_failure": False}) == "low"


def test_oracle_helpers_keep_policy_and_selection_separate() -> None:
    selection = {
        "ownership": "owned",
        "semantic_failure": True,
        "oracle_scorable": True,
        "oracle_truncated": False,
        "ambiguous_component_count": 1,
        "selector_regret": 0.25,
        "oracle_speech_equivalent": True,
        "oracle_literal_exact": True,
        "combinations_evaluated": 3,
        "actual_speech_wer": 0.25,
        "oracle_speech_wer": 0.0,
    }
    selection_without_full_recovery = {
        "ownership": "owned",
        "semantic_failure": True,
        "oracle_scorable": True,
        "oracle_truncated": False,
        "ambiguous_component_count": 1,
        "selector_regret": 0.5,
        "oracle_speech_equivalent": False,
        "oracle_literal_exact": False,
        "combinations_evaluated": 2,
        "actual_speech_wer": 0.5,
        "oracle_speech_wer": 0.25,
    }
    policy = {
        "ownership": "protected",
        "oracle_scorable": True,
        "oracle_truncated": False,
        "ambiguous_component_count": 1,
        "selector_regret": 0.5,
        "oracle_speech_equivalent": True,
        "oracle_literal_exact": True,
        "combinations_evaluated": 2,
        "actual_speech_wer": 0.5,
        "oracle_speech_wer": 0.0,
    }

    assert oracle_gap_type(selection) == "selection"
    assert oracle_gap_type(policy) == "policy"
    aggregates = oracle_aggregates(
        (selection, selection_without_full_recovery, policy)
    )
    assert aggregates["cases"] == 3
    assert aggregates["eligible_cases"] == 2
    assert aggregates["eligible_semantic_failure_count"] == 2
    assert aggregates["selection_gap_count"] == 2
    assert aggregates["selection_gap_rate"] == 1.0
    assert aggregates["fully_recoverable_selection_gap_count"] == 1
    assert aggregates["fully_recoverable_selection_gap_rate"] == 0.5
    assert aggregates["selection_gap_rate_numerator"] == 2
    assert aggregates["selection_gap_rate_denominator"] == 2

def test_failure_family_splits_other_from_runtime_provenance() -> None:
    assert failure_family({"category": "Time", "primary_rule": "en.time"}) == "time"
    assert failure_family({"category": "Currency", "primary_rule": "sequence.currency"}) == (
        "currency"
    )
    assert failure_family({"category": "Scientific", "primary_rule": "sequence.scientific"}) == (
        "scientific"
    )
    assert failure_family({"category": "Identifier", "primary_rule": "sequence.isbn"}) == "isbn"
    assert failure_family({"failure_phase": "unrecognized", "semantic_failure": True}) == (
        "unrecognized"
    )


def test_failure_gap_type_uses_oracle_and_ownership_evidence() -> None:
    assert failure_gap_type({"oracle_gap_type": "selection", "semantic_failure": True}) == (
        "selection-gap"
    )
    assert failure_gap_type({"failure_phase": "structured_rendering"}) == "rendering-gap"
    assert failure_gap_type({"failure_phase": "unrecognized"}) == "recognition-gap"
    assert failure_gap_type({"ownership": "dependency-abbr2words"}) == "dependency-gap"
    assert failure_gap_type({"ownership": "protected"}) == "policy-gap"


def test_diagnostic_aggregates_include_gap_type() -> None:
    result = diagnostic_aggregates(
        (
            {"semantic_failure": True, "failure_phase": "unrecognized"},
            {"semantic_failure": True, "failure_phase": "structured_rendering"},
        )
    )
    assert result["by_gap_type"] == {
        "recognition-gap": 1,
        "rendering-gap": 1,
    }
