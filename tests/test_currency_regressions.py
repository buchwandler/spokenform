from __future__ import annotations

import pytest

from spokenform import iter_structured_replacements, prepare


@pytest.mark.parametrize(
    ("source", "expected", "fragment"),
    [
        ("Es kostet € 1.500.", "Es kostet eintausendfünfhundert Euro.", "€ 1.500"),
        (
            "Der Preis beträgt $19,95.",
            "Der Preis beträgt neunzehn Dollar fünfundneunzig.",
            "$19,95",
        ),
        ("Die Gebühr beträgt £12.50.", "Die Gebühr beträgt zwölf Pfund fünfzig.", "£12.50"),
    ],
)
def test_german_currency_before_sentence_period_is_claimed_atomically(
    source: str, expected: str, fragment: str
) -> None:
    result = prepare(source, language="de_DE", use_spacy=False)
    assert result.spoken_text == expected
    edits = [edit for edit in result.source_replacements if edit.rule == "de.currency"]
    assert any(edit.source == fragment for edit in edits)


def test_german_currency_does_not_backtrack_to_partial_amount() -> None:
    result = prepare("Der Preis beträgt $19,95.", language="de_DE", use_spacy=False)
    assert not any(
        edit.rule == "de.currency" and edit.source == "$19" for edit in result.source_replacements
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("12,50 EUR", "zwölf Euro fünfzig Cent"),
        ("EUR 12,50", "zwölf Euro fünfzig Cent"),
        ("-1,25 EUR", "minus ein Euro fünfundzwanzig Cent"),
        ("0,05 EUR", "null Euro fünf Cent"),
    ],
)
def test_reviewed_german_euro_contract_remains_stable(source: str, expected: str) -> None:
    assert prepare(source, language="de_DE", use_spacy=False).spoken_text == expected


def test_reviewed_german_chf_contract_is_a_currency_match() -> None:
    result = prepare("CHF 12,80", language="de_DE", use_spacy=False)
    assert result.spoken_text == "zwölf Komma acht null Schweizer Franken"
    assert any(edit.rule == "de.currency" for edit in result.source_replacements)


def test_german_exchange_rate_owns_the_complete_span() -> None:
    result = prepare("Der Wechselkurs ist 1€ = $1.10.", language="de_DE", use_spacy=False)
    assert result.spoken_text == "Der Wechselkurs ist ein Euro gleich ein Dollar zehn."
    assert any(
        edit.rule == "sequence.exchange-rate" and edit.source == "1€ = $1.10"
        for edit in result.source_replacements
    )
    assert not any(edit.rule == "de.currency" for edit in result.source_replacements)


@pytest.mark.parametrize(
    ("source", "language"),
    [("1€ = $1.10", "de_DE"), ("1.2 USD to EUR", "en_US"), ("17.09 MXN/USD", "es_MX")],
)
def test_exchange_rate_outranks_ordinary_currency(source: str, language: str) -> None:
    result = prepare(source, language=language, use_spacy=False)
    assert any(
        edit.rule == "sequence.exchange-rate" and edit.source == source
        for edit in result.source_replacements
    )


def test_english_exchange_rate_uses_decimal_rate_not_cash_minor_units() -> None:
    output = prepare(
        "The exchange rate is 1.2 USD to EUR.", language="en_US", use_spacy=False
    ).spoken_text
    assert output == "The exchange rate is one point two U S dollars to euros."
    assert "twenty cents" not in output
    assert " EUR" not in output


def test_mexican_spanish_exchange_rate_is_localized() -> None:
    output = prepare(
        "El cambio es de 17.09 MXN/USD.", language="es_MX", use_spacy=False
    ).spoken_text
    assert output == "El cambio es de diecisiete punto cero nueve pesos por dólar."
    assert " per " not in output
    assert "dólares estadounidenses" not in output


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("₩50,000 (won).", "Cincuenta mil wones."),
        ("₫1,000,000 (dong).", "Un millón de dongs."),
        ("₮50,000 (tugrik).", "Cincuenta mil tugriks."),
    ],
)
def test_mexican_spanish_extended_currency_morphology(source: str, expected: str) -> None:
    result = prepare(source, language="es_MX", use_spacy=False)
    assert result.spoken_text == expected
    assert any(edit.rule == "es.currency" for edit in result.source_replacements)


def test_currency_parenthetical_gloss_is_consumed_only_when_redundant() -> None:
    assert prepare("₩50,000 (won).", language="es_MX", use_spacy=False).spoken_text == (
        "Cincuenta mil wones."
    )
    budget = prepare("₩50,000 (budget).", language="es_MX", use_spacy=False).spoken_text
    assert "(budget)" in budget


@pytest.mark.parametrize("source", ["$1,23,45", "€1.2.3", "₫1,000,00"])
def test_malformed_currency_has_no_partial_structured_currency_edit(source: str) -> None:
    replacements = iter_structured_replacements(
        source, language="de_DE" if source.startswith(("$", "€")) else "es_MX"
    )
    assert not any(edit.rule and edit.rule.endswith(".currency") for edit in replacements)
