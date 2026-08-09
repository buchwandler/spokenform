from __future__ import annotations

from spokenform import (
    NumberPolicy,
    PreparationConfig,
    iter_structured_replacements,
    normalize_numbers,
    prepare,
)
from spokenform.config import number_policy_for_language


def test_czech_policy_aliases_and_english_policy() -> None:
    for language in ("cs", "cs-cz", "cs_CZ"):
        assert number_policy_for_language(language) is NumberPolicy.STRUCTURED_AND_PLAIN
        assert (
            PreparationConfig.for_kokorog2p(language).number_policy
            is NumberPolicy.STRUCTURED_AND_PLAIN
        )
    assert number_policy_for_language("en") is NumberPolicy.STRUCTURED_AND_PLAIN


def test_czech_ordinary_numbers_and_precision() -> None:
    cases = {
        "0": "nula",
        "1": "jedna",
        "2": "dva",
        "4": "čtyři",
        "5": "pět",
        "11": "jedenáct",
        "21": "dvacet jedna",
        "22": "dvacet dva",
        "25": "dvacet pět",
        "100": "sto",
        "1000": "tisíc",
        "-5": "mínus pět",
        "1,5": "jedna celá pět",
        "1,50": "jedna celá pět nula",
        ",02": "nula celá nula dva",
    }
    for source, expected in cases.items():
        assert prepare(source, language="cs", use_spacy=False).spoken_text == expected


def test_czech_dates_are_validated_and_use_genitive_day_and_month() -> None:
    cases = {
        "29.02.2024": "dvacátého devátého února dva tisíce dvacet čtyři",
        "01/03/2026": "prvního března dva tisíce dvacet šest",
        "2026-05-14": "čtrnáctého května dva tisíce dvacet šest",
        "29.02.2023": "29.02.2023",
        "31/04/2026": "31/04/2026",
    }
    for source, expected in cases.items():
        assert prepare(source, language="cs", use_spacy=False).spoken_text == expected


def test_czech_times_remain_caller_managed_including_invalid_candidates() -> None:
    source = "18:20 09:05 25:99"
    assert prepare(source, language="cs", use_spacy=False).spoken_text == source
    assert normalize_numbers(source, language="cs") == source


def test_czech_quantity_agreement_and_dotted_aliases() -> None:
    cases = {
        "1 h": "jedna hodina",
        "2 h": "dvě hodiny",
        "5 h": "pět hodin",
        "1 kg": "jeden kilogram",
        "2 kg": "dva kilogramy",
        "5 kg": "pět kilogramů",
        "1 l": "jeden litr",
        "2 l": "dva litry",
        "5 l": "pět litrů",
        "1 m": "jeden metr",
        "-2 kg": "mínus dva kilogramy",
        "1,5 kg": "jedna celá pět kilogramů",
        "1 hod.": "jedna hodina.",
        "m": "m",
    }
    for source, expected in cases.items():
        assert prepare(source, language="cs", use_spacy=False).spoken_text == expected


def test_czech_temperature_morphology_is_intentional() -> None:
    cases = {
        "1°C": "jeden stupeň Celsia",
        "2°C": "dva stupně Celsia",
        "4°C": "čtyři stupně Celsia",
        "5°C": "pět stupňů Celsia",
        "-1°C": "mínus jeden stupeň Celsia",
        "-10°F": "mínus deset stupňů Fahrenheita",
        "21°C": "dvacet jedna stupňů Celsia",
        "22°C": "dvacet dva stupňů Celsia",
        "25°C": "dvacet pět stupňů Celsia",
        "1 K": "jeden kelvin",
        "2 K": "dva kelviny",
        "5 K": "pět kelvinů",
    }
    for source, expected in cases.items():
        assert prepare(source, language="cs", use_spacy=False).spoken_text == expected


def test_czech_currencies_use_canonical_id_grammar() -> None:
    cases = {
        "1 Kč": "jedna koruna",
        "2 Kč": "dvě koruny",
        "5 Kč": "pět korun",
        "12,80 Kč": "dvanáct korun a osmdesát haléřů",
        "1 EUR": "jedno euro",
        "2 EUR": "dvě eura",
        "5 EUR": "pět eur",
        "1 USD": "jeden dolar",
        "2 USD": "dva dolary",
        "5 USD": "pět dolarů",
        "1 GBP": "jedna libra šterlinků",
        "2 GBP": "dvě libry šterlinků",
        "5 GBP": "pět liber šterlinků",
        "EUR 1": "jedno euro",
    }
    for source, expected in cases.items():
        assert prepare(source, language="cs", use_spacy=False).spoken_text == expected


def test_czech_extended_units_are_claimed() -> None:
    cases = {
        "2 mm²": "dva milimetry čtvereční",
        "5 cm³": "pět centimetrů krychlových",
        "1 ha": "jeden hektar",
        "2 m/s": "dva metry za sekundu",
        "5 km/h": "pět kilometrů za hodinu",
    }
    for source, expected in cases.items():
        assert prepare(source, language="cs", use_spacy=False).spoken_text == expected


def test_czech_protection_and_structured_safe_plain_pass() -> None:
    source = "https://example.org/2kg dev2@example.org v1.2.3 1.2.3 18:20 25:99 2 kg"
    result = prepare(source, language="cs", use_spacy=False)
    assert result.spoken_text == (
        "https://example.org/2kg dev2@example.org v1.2.3 1.2.3 18:20 25:99 dva kilogramy"
    )


def test_czech_partial_protection_expands_to_whole_quantity() -> None:
    source = "2 kg a 3 kg"
    start = source.index("2 kg") + 2
    result = prepare(source, language="cs", use_spacy=False, protected_spans=[(start, start + 2)])
    assert result.spoken_text == "2 kg a tři kilogramy"


def test_czech_nbsp_and_repeated_source_spans_are_exact() -> None:
    source = "2\u00a0kg a 2\u00a0kg"
    result = prepare(source, language="cs", use_spacy=False)
    assert result.spoken_text == "dva kilogramy a dva kilogramy"
    structured = next(stage for stage in result.stages if stage.name == "structured")
    assert [edit.source for edit in structured.mapped_edits] == ["2\u00a0kg", "2\u00a0kg"]
    assert all(
        source[edit.source_start : edit.source_end] == edit.source for edit in result.source_edits
    )


def test_czech_structured_replacements_are_sorted_and_non_overlapping() -> None:
    source = "14.05.2026 2 kg 2 kg"
    replacements = iter_structured_replacements(source, language="cs")
    assert [(item.start, item.end) for item in replacements] == sorted(
        (item.start, item.end) for item in replacements
    )
    assert all(
        source[item.start : item.end] == source[item.start : item.end] for item in replacements
    )
    assert [(item.rule, item.text) for item in replacements] == [
        ("cs.date", "čtrnáctého května dva tisíce dvacet šest"),
        ("cs.quantity", "dva kilogramy"),
        ("cs.quantity", "dva kilogramy"),
    ]
