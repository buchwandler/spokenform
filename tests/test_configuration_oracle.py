from __future__ import annotations

from benchmarks.configuration_oracle import (
    CONFIGURATION_LATTICE,
    MAX_CONFIGURATIONS,
    analysis_fields,
    analyze_configuration_oracle,
    oracle_aggregates,
)
from spokenform import prepare


def test_configuration_lattice_is_bounded_and_documented() -> None:
    assert len(CONFIGURATION_LATTICE) <= MAX_CONFIGURATIONS
    assert [variant.config_id for variant in CONFIGURATION_LATTICE] == [
        "default",
        "long-number-contextual",
        "acronym-conservative-unknown",
        "acronym-spell-unknown",
        "normalize-literals",
        "long-number-contextual-acronym-conservative",
    ]
    assert CONFIGURATION_LATTICE[4].policy_expansion


def test_configuration_oracle_reports_best_config_and_regret() -> None:
    source = "There are 123456 items."
    baseline = prepare(source, language="en", use_spacy=False)
    analysis = analyze_configuration_oracle(
        source,
        "There are one hundred twenty three thousand four hundred fifty six items.",
        baseline,
        language="en",
    )

    assert analysis.enabled
    assert analysis.scorable
    assert analysis.baseline_config_id == "default"
    assert analysis.best_config_id in {variant.config_id for variant in CONFIGURATION_LATTICE}
    assert analysis.config_regret >= 0.0
    assert analysis.policy_expansion is False
    assert analysis_fields(analysis)["config_oracle_enabled"] is True


def test_configuration_oracle_keeps_policy_expansion_separate() -> None:
    rows = [
        {
            "config_oracle_enabled": True,
            "config_oracle_scorable": True,
            "best_config_id": "default",
            "config_regret": 0.0,
            "config_policy_expansion": False,
        },
        {
            "config_oracle_enabled": True,
            "config_oracle_scorable": True,
            "best_config_id": "normalize-literals",
            "config_regret": 0.5,
            "config_policy_expansion": True,
        },
    ]

    summary = oracle_aggregates(rows)

    assert summary["cases"] == 2
    assert summary["normal_configuration_cases"] == 1
    assert summary["policy_expansion_cases"] == 1
    assert summary["config_regret_sum"] == 0.0
