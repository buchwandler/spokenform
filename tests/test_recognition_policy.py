from __future__ import annotations

from spokenform import InterpretationMode, RecognitionDomain, Replacement
from spokenform.recognition_policy import decide_candidate
from spokenform.structured import iter_structured_candidates

_RECOGNITION_SAMPLES = (
    "1980s 1989 1989-1990 final 3-2",
    "H2O NaCl Al(OH)3",
    "https://example.com a@b.com 127.0.0.1 00:11:22:33:44:55",
    "ISBN 978-0-306-40615-7 UUID 550e8400-e29b-41d4-a716-446655440000",
    "AAPL stock ticker BRCA2 gene Mozart C4 BMW E46",
    "45 kg 50% 1/2 48.8566,2.3522",
    "Section 12(3) #tag @user",
)


def test_production_candidates_have_policy_metadata() -> None:
    candidates = tuple(
        candidate
        for text in _RECOGNITION_SAMPLES
        for candidate in iter_structured_candidates(text, language="en")
    )
    assert candidates
    assert all(candidate.recognition_domain for candidate in candidates)
    assert all(candidate.recognition_evidence for candidate in candidates)


def test_unannotated_candidates_fail_closed_in_surface_mode() -> None:
    decision = decide_candidate(
        Replacement(0, 3, "value"),
        interpretation_mode=InterpretationMode.SURFACE,
        disabled_domains=frozenset(),
    )
    assert decision.enabled is False
    assert decision.reason == "context-not-allowed"


def test_chemistry_is_a_distinct_domain() -> None:
    candidate = next(
        candidate
        for candidate in iter_structured_candidates("H2O", language="en")
        if candidate.rule == "sequence.formula"
    )
    assert candidate.recognition_domain == RecognitionDomain.CHEMISTRY.value
