from __future__ import annotations

import pytest

from spokenform import PreparationConfig, Replacement, prepare
from spokenform.config import InterpretationMode
from spokenform.recognition_policy import decide_candidate


def test_allowed_domain_selects_only_the_permitted_family() -> None:
    result = prepare("H2O and 2 kg", use_spacy=False, allowed_domains={"quantities"})
    assert any(item.rule == "en.quantity" for item in result.source_replacements)
    assert all(item.rule != "sequence.formula" for item in result.source_replacements)
    assert "H2O" in result.spoken_text


def test_explicit_allowlist_fails_closed_for_missing_metadata() -> None:
    decision = decide_candidate(
        Replacement(0, 3, "value"),
        interpretation_mode=InterpretationMode.CONTEXTUAL,
        disabled_domains=frozenset(),
        allowed_domains=frozenset({"core"}),
    )
    assert not decision.enabled
    assert decision.reason == "domain-not-allowed"


def test_disabled_domain_overlap_is_rejected() -> None:
    with pytest.raises(ValueError, match="overlap"):
        PreparationConfig(allowed_domains={"chemistry"}, disabled_domains={"chemistry"})


def test_protection_wins_over_domain_allowlisting() -> None:
    result = prepare(
        "H2O", use_spacy=False, allowed_domains={"chemistry"}, protected_spans=[(0, 3)]
    )
    assert result.spoken_text == "H2O"
    assert not result.source_replacements
