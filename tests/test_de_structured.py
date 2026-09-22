import json
from pathlib import Path

import pytest

from spokenform import PreparationConfig, iter_structured_replacements, prepare

PARITY_PATH = Path(__file__).parent / "data" / "de_kokorog2p_parity.json"


def test_german_parity_corpus() -> None:
    for case in json.loads(PARITY_PATH.read_text(encoding="utf-8")):
        result = prepare(case["input"], language="de", use_spacy=False)
        assert result.spoken_text == case["expected"], case["name"]


def test_german_quantity_inventory_and_grammar() -> None:
    cases = {
        "1 kg": "Ein Kilogramm",
        "2 kg": "Zwei Kilogramm",
        "1 Std.": "Eine Stunde.",
        "2 Std.": "Zwei Stunden.",
        "1 Mio.": "Eine Million.",
        "2 Mio.": "Zwei Millionen.",
        "1 kWh": "Eine Kilowattstunde",
        "2 kWh": "Zwei Kilowattstunden",
        "1,0 kg": "Ein Kilogramm",
        "1,5 kg": "Eins Komma fünf Kilogramm",
        "-2 kg": "Minus zwei Kilogramm",
        "2kg": "Zwei Kilogramm",
        "Model5kg": "Model5kg",
    }
    for source, expected in cases.items():
        assert prepare(source, language="de", use_spacy=False).spoken_text == expected


def test_german_extended_quantity_inventory_and_aliases() -> None:
    cases = {
        "1 mm²": "Ein Quadratmillimeter",
        "2 mm²": "Zwei Quadratmillimeter",
        "1 cm²": "Ein Quadratzentimeter",
        "2 cm²": "Zwei Quadratzentimeter",
        "1 m²": "Ein Quadratmeter",
        "2 m²": "Zwei Quadratmeter",
        "1 km²": "Ein Quadratkilometer",
        "2 km²": "Zwei Quadratkilometer",
        "1 ha": "Ein Hektar",
        "2 ha": "Zwei Hektar",
        "1 mm³": "Ein Kubikmillimeter",
        "2 mm³": "Zwei Kubikmillimeter",
        "1 cm³": "Ein Kubikzentimeter",
        "2 cm³": "Zwei Kubikzentimeter",
        "1 m³": "Ein Kubikmeter",
        "2 m³": "Zwei Kubikmeter",
        "1 m/s": "Ein Meter pro Sekunde",
        "2 m/s": "Zwei Meter pro Sekunde",
        "1 km/h": "Ein Kilometer pro Stunde",
        "2 km/h": "Zwei Kilometer pro Stunde",
        "m2": "m2",
        "m3": "m3",
        "cm2": "cm2",
        "cm3": "cm3",
        "1 m2": "Ein Quadratmeter",
        "1 m3": "Ein Kubikmeter",
        "1 cm2": "Ein Quadratzentimeter",
        "1 cm3": "Ein Kubikzentimeter",
    }
    for source, expected in cases.items():
        assert prepare(source, language="de", use_spacy=False).spoken_text == expected, source


def test_german_extended_quantity_near_misses_are_not_rewritten_as_units() -> None:
    cases = {
        "m³": "m³",
        "1 m³x": "Eins m³x",
        "1 m ³": "Ein Meter ³",
        "foo 1 km/hbar": "foo eins km/hbar",
        "1 mm²x": "Eins mm²x",
    }
    for source, expected in cases.items():
        result = prepare(source, language="de", use_spacy=False)
        assert result.spoken_text == expected, source
        assert "Quadrat" not in result.spoken_text
        assert "Kubik" not in result.spoken_text
        assert "pro Stunde" not in result.spoken_text


def test_german_extended_quantity_source_replacements_and_composed_map() -> None:
    source = "1 m³ plus 1 m³"
    result = prepare(source, language="de", use_spacy=False)

    assert result.spoken_text == "Ein Kubikmeter plus ein Kubikmeter"
    assert [
        (item.source_start, item.source_end, item.source, item.replacement, item.rule)
        for item in result.source_replacements
    ] == [
        (0, 4, "1 m³", "Ein Kubikmeter", "de.quantity"),
        (10, 14, "1 m³", "ein Kubikmeter", "de.quantity"),
    ]
    assert all(
        left.source_end <= right.source_start
        for left, right in zip(
            result.source_replacements, result.source_replacements[1:], strict=False
        )
    )
    for item in result.source_replacements:
        assert source[item.source_start : item.source_end] == item.source
        assert result.spoken_text[item.output_start : item.output_end] == item.replacement
        assert result.offset_map is not None
        assert result.offset_map.map_source_span(item.source_start, item.source_end) == (
            item.output_start,
            item.output_end,
        )

    source = "1 m³ then 1 km/h"
    result = prepare(source, language="de", use_spacy=False)
    assert result.spoken_text == "Ein Kubikmeter then ein Kilometer pro Stunde"
    assert [
        (item.source_start, item.source_end, item.source, item.replacement)
        for item in result.source_replacements
    ] == [
        (0, 4, "1 m³", "Ein Kubikmeter"),
        (10, 16, "1 km/h", "ein Kilometer pro Stunde"),
    ]
    assert result.offset_map is not None
    assert result.offset_map.map_source_span(0, 4) == (0, 14)
    assert result.offset_map.map_source_span(10, 16) == (20, 44)


def test_german_structured_values_and_invalid_candidates() -> None:
    cases = {
        "03.01.2026": "Dritte Januar zweitausendsechsundzwanzig",
        "am 3. Tag": "am dritten Tag",
        "der 3. Versuch": "der dritte Versuch",
        "auf die 2. Schiene": "auf die zweite Schiene",
        "14:05": "Vierzehn Uhr fünf",
        "01:00 Uhr": "Ein Uhr",
        "25:99": "25:99",
        "24:00": "24:00",
        "31.02.2026": "31.02.2026",
        "29.02.2025": "29.02.2025",
        "3°C": "Drei Grad Celsius",
        "-1,2 °F": "Minus eins Komma zwei Grad Fahrenheit",
        "12,50 EUR": "Zwölf Euro fünfzig Cent",
        "EUR 12,50": "zwölf Euro fünfzig Cent",
        "1.234 EUR": "Eintausendzweihundertvierunddreißig Euro",
        "CHF 12,80": "zwölf Komma acht null Schweizer Franken",
        ".02": "Null Komma null zwei",
        ",02": "Null Komma null zwei",
        "Lfd. Nr. 12.": "laufende Nummer zwölf.",
        "S. 12": "Seite zwölf",
    }
    for source, expected in cases.items():
        assert prepare(source, language="de", use_spacy=False).spoken_text == expected, source


def test_structured_is_independent_of_lexical_abbreviations() -> None:
    result = prepare(
        "1 Std. 42 kg Prof.",
        language="de",
        use_spacy=False,
        config=PreparationConfig(language="de", expand_abbreviations=False),
    )
    assert result.spoken_text == "Eine Stunde zweiundvierzig Kilogramm Prof."


def test_protected_values_are_unchanged() -> None:
    source = "https://example.org/2kg v1.2.3 dev2@example.org 2 kg"
    result = prepare(source, language="de", use_spacy=False)
    assert "https://example.org/2kg" in result.spoken_text
    assert "v1.2.3" in result.spoken_text
    assert "dev2@example.org" in result.spoken_text
    assert result.spoken_text.endswith("zwei Kilogramm")


def test_structured_replacement_is_one_exact_semantic_edit() -> None:
    replacements = iter_structured_replacements("2 kg 2 kg", language="de")
    assert [(item.start, item.end, item.text, item.rule) for item in replacements] == [
        (0, 4, "Zwei Kilogramm", "de.quantity"),
        (5, 9, "zwei Kilogramm", "de.quantity"),
    ]


def test_cooking_paragraph_golden() -> None:
    source = (
        "Zum 14.05.2026 um 18:20 Uhr ist das Abendessen geplant. Für den\n"
        "Auflauf brauchen wir 1,5 kg Kartoffeln, 500 g Quark, 2 Eier, 1 ltr.\n"
        'Milch und ggf. 3 cm mehr Backpapier. Prof. Klein sagt: "Bitte stelle\n'
        "die Form auf die 2. Schiene, backe alles für 45 Min. und lass es danach\n"
        '1 Min. oder auch 2 Min. ruhen." Die Kosten liegen bei ca. 12,80 EUR\n'
        "zzgl. Pfand."
    )
    expected = (
        "Zum vierzehnten Mai zweitausendsechsundzwanzig um achtzehn Uhr zwanzig ist das Abendessen geplant. Für den\n"
        "Auflauf brauchen wir eins Komma fünf Kilogramm Kartoffeln, fünfhundert Gramm Quark, zwei Eier, ein Liter\n"
        'Milch und gegebenenfalls drei Zentimeter mehr Backpapier. Professor Klein sagt: "Bitte stelle\n'
        "die Form auf die zweite Schiene, backe alles für fünfundvierzig Minuten und lass es danach\n"
        'eine Minute oder auch zwei Minuten ruhen." Die Kosten liegen bei zirka zwölf Euro achtzig Cent\n'
        "zuzüglich Pfand."
    )
    assert prepare(source, language="de", use_spacy=False).spoken_text == expected


def test_german_source_replacements_are_sorted_and_reconstruct_final_text() -> None:
    source = "Prof. 14.05.2026 2 kg 2 kg"
    result = prepare(source, language="de", use_spacy=False)

    assert list(result.source_edits) == sorted(
        result.source_edits,
        key=lambda edit: (edit.source_start, edit.output_start),
    )
    assert all(
        source[edit.source_start : edit.source_end] == edit.source for edit in result.source_edits
    )
    assert all(
        result.spoken_text[edit.output_start : edit.output_end] == edit.replacement
        for edit in result.source_edits
    )
    assert result.source_edits


def test_brief_german_parity_categories() -> None:
    cases = {
        "1 Wh": "Eine Wattstunde",
        "1 mAh": "Eine Milliamperestunde",
        "1 Sek.": "Eine Sekunde.",
        "1 MIN. warten": "Eine Minute warten",
        "1 Ltr. Milch": "Ein Liter Milch",
        "2 STCK. Eier": "Zwei Stück Eier",
        "1 mio. EUR": "Eine Million Euro",
        "2 mrd. EUR": "Zwei Milliarden Euro",
        "1 EUR": "Ein Euro",
        "2 EUR": "Zwei Euro",
        "12.50 EUR": "Zwölf Euro fünfzig Cent",
        "-1,25 EUR": "Minus ein Euro fünfundzwanzig Cent",
        "0,05 EUR": "Null Euro fünf Cent",
        "1.000,50": "Eintausend Komma fünf null",
        "3,14": "Drei Komma eins vier",
        ".02": "Null Komma null zwei",
        "03/01/26": "Dritte ersten zweitausendsechsundzwanzig",
        "3. Maerz 2026": "dritter März zweitausendsechsundzwanzig",
        "3. Mär 2026": "dritter März zweitausendsechsundzwanzig",
        "zur 6. Version": "zur sechsten Version",
        "auf der 7. Etage": "auf der siebten Etage",
        "ins 4. Fach": "ins vierte Fach",
        "Nummer 12.": "Nummer zwölf.",
        "Gleis 7.": "Gleis sieben.",
        "31.02.2026": "31.02.2026",
        "25:99": "25:99",
        "Model5kg": "Model5kg",
    }
    for source, expected in cases.items():
        assert prepare(source, language="de", use_spacy=False).spoken_text == expected, source


def test_structured_match_is_fail_closed_at_partial_decimal_overlap() -> None:
    result = prepare("1.000,50 kg", language="de", use_spacy=False)
    assert result.spoken_text == "Eintausend Komma fünf null Kilogramm"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("die 1. Frau", "die erste Frau"),
        ("der 1. Mann", "der erste Mann"),
        ("das 1. Kind", "das erste Kind"),
    ],
)
def test_german_determiner_context_keeps_existing_ordinal_inflection(
    source: str, expected: str
) -> None:
    assert prepare(source, language="de", use_spacy=False).spoken_text == expected
