from __future__ import annotations

from spokenform.structured import iter_structured_candidates


def test_iter_structured_candidates_exposes_unresolved_overlaps() -> None:
    candidates = iter_structured_candidates("2 kg", language="fr")

    assert len(candidates) >= 2
    assert [candidate.rule for candidate in candidates] == ["fr.quantity", "fr.number"]


def test_iter_structured_candidates_keeps_duplicate_candidate_order() -> None:
    candidates = iter_structured_candidates("final 3-2", language="en")

    assert [candidate.rule for candidate in candidates] == [
        "sequence.sports",
        "sequence.sports",
    ]
