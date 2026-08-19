from __future__ import annotations

import pytest

from spokenform import prepare
from spokenform.diagnostics import trace_structured_candidates


@pytest.mark.parametrize(
    ("source", "domain", "rule"),
    (
        ("H2O", "chemistry", "sequence.formula"),
        ("BRCA2 gene", "biology", "sequence.biomedical"),
        ("final 3-2", "sports", "sequence.sports"),
        ("stock symbol AAPL", "finance", "sequence.ticker"),
        ("123 Main St", "addresses", "sequence.address"),
        ("George VI", "references", "sequence.roman"),
        ("127.0.0.1", "network", "sequence.ipv4"),
        ("https://example.com", "communications", "sequence.url"),
    ),
)
def test_specialist_candidates_report_their_domain(source: str, domain: str, rule: str) -> None:
    result = prepare(source, language="en", use_spacy=False, normalize_literals=True)
    selected = {item.rule: item for item in result.source_replacements}
    assert rule in selected


def test_disabled_chemistry_preserves_formula_span() -> None:
    result = prepare("H2O", use_spacy=False, disabled_domains={"chemistry"})
    assert all(item.rule != "sequence.formula" for item in result.source_replacements)
    assert result.spoken_text == "H2O"


def test_disabled_sports_does_not_fall_back_to_numeric_range() -> None:
    result = prepare("final 3-2", use_spacy=False, disabled_domains={"sports"})
    assert all(item.rule != "sequence.sports" for item in result.source_replacements)
    assert result.spoken_text == "final 3-2"


def test_surface_policy_suppression_is_diagnostic() -> None:
    records = trace_structured_candidates(
        "final 3-2",
        language="en",
        interpretation_mode="surface",
    )
    suppressed = [item for item in records if item.status == "suppressed"]
    assert suppressed
    assert all(item.policy_reason == "context-not-allowed" for item in suppressed)
    assert all(item.domain == "sports" for item in suppressed)


def test_disabling_a_domain_suppresses_its_candidates() -> None:
    records = trace_structured_candidates(
        "H2O",
        language="en",
        disabled_domains={"chemistry"},
    )
    assert any(
        item.status == "suppressed"
        and item.policy_reason == "disabled-domain"
        and item.domain == "chemistry"
        for item in records
    )


def test_countdown_belongs_to_temporal_domain() -> None:
    result = prepare("Countdown 3-2-1", use_spacy=False)
    assert any(item.rule == "sequence.countdown" for item in result.source_replacements)

    sports_disabled = prepare("Countdown 3-2-1", use_spacy=False, disabled_domains={"sports"})
    assert any(item.rule == "sequence.countdown" for item in sports_disabled.source_replacements)

    temporal_disabled = prepare("Countdown 3-2-1", use_spacy=False, disabled_domains={"temporal"})
    assert all(item.rule != "sequence.countdown" for item in temporal_disabled.source_replacements)
    assert temporal_disabled.spoken_text == "Countdown 3-2-1"

    surface = prepare("Countdown 3-2-1", use_spacy=False, interpretation_mode="surface")
    assert all(item.rule != "sequence.countdown" for item in surface.source_replacements)
