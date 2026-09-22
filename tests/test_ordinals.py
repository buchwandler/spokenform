import pytest

from spokenform import prepare


def test_locale_ordinal_symbols_are_expanded_without_sentence_final_cardinal_rewrites() -> None:
    assert prepare("1º", language="es", use_spacy=False).spoken_text == "Primero"
    assert prepare("2ª", language="it", use_spacy=False).spoken_text == "seconda"
    assert prepare("2ème", language="fr", use_spacy=False).spoken_text == "deuxième"
    assert prepare("The 1st release", language="en", use_spacy=False).spoken_text == (
        "The first release"
    )
    assert prepare("1.", language="de", use_spacy=False).spoken_text == "Eins."


def test_ordinal_policies_validate_suffixes_and_degree_collisions() -> None:
    assert prepare("1st 2nd 3rd 11th 12th 13th", language="en", use_spacy=False).spoken_text == (
        "first second third eleventh twelfth thirteenth"
    )
    assert prepare("1nd 2rd 3th", language="en", use_spacy=False).spoken_text == ("1nd 2rd 3th")
    assert prepare("1.º 1.ª 1er 1a", language="es", use_spacy=False).spoken_text == (
        "Primero primera primer primera"
    )
    assert prepare("1° 1°C", language="it", use_spacy=False).spoken_text == (
        "primo un grado Celsius"
    )
    assert prepare(
        "das 3. Ergebnis; ihren 3. Versuch", language="de", use_spacy=False
    ).spoken_text == ("das dritte Ergebnis; ihren dritten Versuch")


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1. Frau", "Erste Frau"),
        ("2. Frau", "Zweite Frau"),
        ("3. Frau", "Dritte Frau"),
        ("1. Mann", "Erster Mann"),
        ("2. Mann", "Zweiter Mann"),
        ("3. Mann", "Dritter Mann"),
        ("1. Kind", "Erstes Kind"),
        ("1. Stunde", "Erste Stunde"),
        ("1. Tag", "Erster Tag"),
        ("1. Kilogramm", "Erstes Kilogramm"),
    ],
)
def test_german_bare_ordinals_agree_with_reviewed_noun_gender(source: str, expected: str) -> None:
    assert prepare(source, language="de", use_spacy=False).spoken_text == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1. Mann ist gut.", "Erster Mann ist gut."),
        ("1. Frau ist gut.", "Erste Frau ist gut."),
        ("42 Männer sind hier.", "Zweiundvierzig Männer sind hier."),
        ("(1. Frau)", "(Erste Frau)"),
    ],
)
def test_german_generated_numeric_input_starts_are_capitalized(source: str, expected: str) -> None:
    assert prepare(source, language="de", use_spacy=False).spoken_text == expected


def test_german_generated_numeric_casing_does_not_recase_middle_of_input() -> None:
    assert (
        prepare("Wir wählen die 1. Frau.", language="de", use_spacy=False).spoken_text
        == "Wir wählen die erste Frau."
    )
