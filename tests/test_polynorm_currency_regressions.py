from __future__ import annotations

from benchmarks.polynorm_eval import currency_related_failures, is_currency_related_case


def test_currency_related_selection_includes_currency_and_symbol_cardinal_rows() -> None:
    assert is_currency_related_case({"canonical_category": "Currency", "original_text": "12 EUR"})
    assert is_currency_related_case(
        {"canonical_category": "Cardinal", "original_text": "Es kostet € 1.500."}
    )
    assert not is_currency_related_case({"canonical_category": "Cardinal", "original_text": "42"})


def test_currency_gate_excludes_reviewed_quarantine_but_fails_unknown_currency_failure() -> None:
    rows = (
        {
            "id": "de-DE:161",
            "canonical_category": "Currency",
            "original_text": "25,99€",
            "quarantine": {"reason_code": "questionable-target"},
            "semantic_failure": True,
        },
        {
            "id": "de-DE:166",
            "canonical_category": "Cardinal",
            "original_text": "87,50 CHF",
            "quarantine": {"reason_code": "questionable-target"},
            "semantic_failure": True,
        },
        {
            "id": "de-DE:48",
            "canonical_category": "Cardinal",
            "original_text": "Es kostet € 1.500.",
            "quarantine": None,
            "semantic_failure": True,
        },
    )
    assert [row["id"] for row in currency_related_failures(rows)] == ["de-DE:48"]


def test_currency_gate_detects_new_unknown_currency_failure() -> None:
    rows = (
        {
            "id": "es-MX:new",
            "canonical_category": "Currency",
            "original_text": "50 MNT",
            "quarantine": None,
            "semantic_failure": True,
        },
    )
    assert [row["id"] for row in currency_related_failures(rows)] == ["es-MX:new"]
