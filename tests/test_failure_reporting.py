from types import SimpleNamespace

from benchmarks.failure_reporting import (
    outcome_for_row,
    ownership_for_rule,
    rank_provenance,
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
