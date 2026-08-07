import json
from pathlib import Path

from spokenform import PreparationConfig, iter_structured_replacements, prepare

PARITY_PATH = Path(__file__).parent / "data" / "de_kokorog2p_parity.json"


def test_german_parity_corpus() -> None:
    for case in json.loads(PARITY_PATH.read_text(encoding="utf-8")):
        result = prepare(case["input"], language="de", use_spacy=False)
        assert result.spoken_text == case["expected"], case["name"]


def test_german_quantity_inventory_and_grammar() -> None:
    cases = {
        "1 kg": "ein Kilogramm",
        "2 kg": "zwei Kilogramm",
        "1 Std.": "eine Stunde.",
        "2 Std.": "zwei Stunden.",
        "1 Mio.": "eine Million.",
        "2 Mio.": "zwei Millionen.",
        "1 kWh": "eine Kilowattstunde",
        "2 kWh": "zwei Kilowattstunden",
        "1,0 kg": "ein Kilogramm",
        "1,5 kg": "eins Komma fünf Kilogramm",
        "-2 kg": "minus zwei Kilogramm",
        "2kg": "zwei Kilogramm",
        "Model5kg": "Model5kg",
    }
    for source, expected in cases.items():
        assert prepare(source, language="de", use_spacy=False).spoken_text == expected


def test_german_structured_values_and_invalid_candidates() -> None:
    cases = {
        "03.01.2026": "dritte Januar zweitausendsechsundzwanzig",
        "am 3. Tag": "am dritten Tag",
        "der 3. Versuch": "der dritte Versuch",
        "auf die 2. Schiene": "auf die zweite Schiene",
        "14:05": "vierzehn Uhr fünf",
        "01:00 Uhr": "ein Uhr",
        "25:99": "25:99",
        "24:00": "24:00",
        "31.02.2026": "31.02.2026",
        "29.02.2025": "29.02.2025",
        "3°C": "drei Grad Celsius",
        "-1,2 °F": "minus eins Komma zwei Grad Fahrenheit",
        "12,50 EUR": "zwölf Euro fünfzig Cent",
        "EUR 12,50": "zwölf Euro fünfzig Cent",
        "1.234 EUR": "eintausendzweihundertvierunddreißig Euro",
        "CHF 12,80": "zwölf Schweizer Franken achtzig Cent",
        ".02": "null Komma null zwei",
        ",02": "null Komma null zwei",
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
    assert result.spoken_text == "eine Stunde zweiundvierzig Kilogramm Prof."


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
        (0, 4, "zwei Kilogramm", "de.quantity"),
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
        "1 Wh": "eine Wattstunde",
        "1 mAh": "eine Milliamperestunde",
        "1 Sek.": "eine Sekunde.",
        "1 MIN. warten": "eine Minute warten",
        "1 Ltr. Milch": "ein Liter Milch",
        "2 STCK. Eier": "zwei Stück Eier",
        "1 mio. EUR": "eine Million Euro",
        "2 mrd. EUR": "zwei Milliarden Euro",
        "1 EUR": "ein Euro",
        "2 EUR": "zwei Euro",
        "12.50 EUR": "zwölf Euro fünfzig Cent",
        "-1,25 EUR": "minus ein Euro fünfundzwanzig Cent",
        "0,05 EUR": "null Euro fünf Cent",
        "1.000,50": "eintausend Komma fünf null",
        "3,14": "drei Komma eins vier",
        ".02": "null Komma null zwei",
        "03/01/26": "dritte Januar zweitausendsechsundzwanzig",
        "3. Maerz 2026": "dritte März zweitausendsechsundzwanzig",
        "3. Mär 2026": "dritte März zweitausendsechsundzwanzig",
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
    assert result.spoken_text == "eintausend Komma fünf null Kilogramm"
