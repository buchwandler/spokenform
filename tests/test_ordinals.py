from spokenform import prepare


def test_locale_ordinal_symbols_are_expanded_without_sentence_final_cardinal_rewrites() -> None:
    assert prepare("1º", language="es", use_spacy=False).spoken_text == "primero"
    assert prepare("2ª", language="it", use_spacy=False).spoken_text == "seconda"
    assert prepare("2ème", language="fr", use_spacy=False).spoken_text == "deuxième"
    assert prepare("The 1st release", language="en", use_spacy=False).spoken_text == (
        "The first release"
    )
    assert prepare("1.", language="de", use_spacy=False).spoken_text == "1."


def test_ordinal_policies_validate_suffixes_and_degree_collisions() -> None:
    assert prepare("1st 2nd 3rd 11th 12th 13th", language="en", use_spacy=False).spoken_text == (
        "first second third eleventh twelfth thirteenth"
    )
    assert prepare("1nd 2rd 3th", language="en", use_spacy=False).spoken_text == ("1nd 2rd 3th")
    assert prepare("1.º 1.ª 1er 1a", language="es", use_spacy=False).spoken_text == (
        "primero primera primer primera"
    )
    assert prepare("1° 1°C", language="it", use_spacy=False).spoken_text == (
        "primo un grado Celsius"
    )
    assert prepare(
        "das 3. Ergebnis; ihren 3. Versuch", language="de", use_spacy=False
    ).spoken_text == ("das dritte Ergebnis; ihren dritten Versuch")
