from spokenform import prepare


def test_german_address_structures_use_category_specific_number_policies() -> None:
    assert prepare("Hauptstraße 45", language="de", use_spacy=False).spoken_text == (
        "Hauptstraße fünfundvierzig"
    )
    assert prepare("Bahnhofplatz 7a", language="de", use_spacy=False).spoken_text == (
        "Bahnhofplatz sieben a"
    )
    assert prepare("Hauptstraße 123-125", language="de", use_spacy=False).spoken_text == (
        "Hauptstraße einhundertdreiundzwanzig bis einhundertfünfundzwanzig"
    )
    assert prepare("Hauptstraße 12/3", language="de", use_spacy=False).spoken_text == (
        "Hauptstraße zwölf Schrägstrich drei"
    )
    assert prepare("Postfach 1234", language="de", use_spacy=False).spoken_text == (
        "Postfach eins zwei drei vier"
    )
    assert prepare("3. OG", language="de", use_spacy=False).spoken_text == "drittes Obergeschoss"


def test_phone_shapes_and_contextual_emergency_numbers() -> None:
    assert prepare("555.123.4567", language="en", use_spacy=False).spoken_text == (
        "five five five one two three four five six seven"
    )
    assert (
        prepare("Dial 911", language="en", use_spacy=False).spoken_text
        == "Dial nine hundred eleven"
    )
    assert (
        prepare("Notruf 112", language="de", use_spacy=False).spoken_text
        == "Notruf einhundertzwölf"
    )
    assert prepare("+49 30 123456", language="en", use_spacy=False).spoken_text.startswith(
        "plus four nine"
    )
    assert prepare("06 12 34 56 78", language="fr", use_spacy=False).spoken_text.startswith(
        "zéro six"
    )


def test_ambiguous_seven_digit_phone_shapes_require_contact_context() -> None:
    assert prepare("555-7890", language="en", use_spacy=False).spoken_text == "555-7890"
    result = prepare("Text me at 555-7890", language="en", use_spacy=False)
    assert result.spoken_text == "Text me at five five five seven eight nine zero"
    assert any(item.rule == "sequence.phone" for item in result.source_replacements)


def test_emergency_number_rendering_can_be_locale_digitwise() -> None:
    result = prepare("Emergencia 911", language="es", use_spacy=False)
    assert result.spoken_text == "Emergencia nueve uno uno"
