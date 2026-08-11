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
    assert prepare("Dial 911", language="en", use_spacy=False).spoken_text == "Dial nine one one"
    assert prepare("Notruf 112", language="de", use_spacy=False).spoken_text == "Notruf eins eins zwei"
    assert prepare("+49 30 123456", language="en", use_spacy=False).spoken_text.startswith("plus four nine")
    assert prepare("06 12 34 56 78", language="fr", use_spacy=False).spoken_text.startswith("zéro six")
