from spokenform import prepare


def test_isbn_validation_and_typed_rendering() -> None:
    result = prepare("ISBN 978-0-306-40615-7", language="en", use_spacy=False)
    assert result.spoken_text == "i s b n nine seven eight zero three zero six four zero six one five seven"
    assert any(item.rule == "sequence.isbn" for item in result.source_replacements)
    invalid = prepare("ISBN 978-0-306-40615-8", language="en", use_spacy=False)
    assert any(item.rule == "sequence.isbn" for item in invalid.source_replacements)
    labeled = prepare("ISBN-10 0-306-40615-2", language="en", use_spacy=False)
    assert labeled.spoken_text.startswith("i s b n ten")
    assert any(item.rule == "sequence.isbn" for item in labeled.source_replacements)


def test_formula_codes_legal_references_and_scores_use_typed_renderers() -> None:
    assert prepare("H₂O", language="en", use_spacy=False).spoken_text == "h two o"
    assert prepare("VW789XY", language="it", use_spacy=False).spoken_text == (
        "vu doppia vu sette otto nove ics ipsilon"
    )
    assert prepare("§ 12 BGB", language="de", use_spacy=False).spoken_text == (
        "Paragraph zwölf B G B"
    )
    assert prepare("Final 2:1", language="en", use_spacy=False).spoken_text == (
        "Final two to one"
    )


def test_typed_code_profiles_and_coordinate_directions_are_contextual() -> None:
    assert prepare("serial number: AB-123", language="en", use_spacy=False).spoken_text == (
        "serial number a b one two three"
    )
    assert prepare("Model E46", language="en", use_spacy=False).spoken_text == (
        "model e forty-six"
    )
    assert prepare("12,3456° O", language="es", use_spacy=False).spoken_text == (
        "doce coma tres cuatro cinco seis grados oeste"
    )
    assert prepare("E46", language="en", use_spacy=False).spoken_text == "E46"


def test_locale_legal_reference_grammars_are_atomic() -> None:
    assert prepare("§ 823 Abs. 1 BGB", language="de", use_spacy=False).spoken_text == (
        "Paragraph achthundertdreiundzwanzig Absatz eins B G B"
    )
    assert prepare("StVO § 1", language="de", use_spacy=False).spoken_text == (
        "S T V O Paragraf eins"
    )
    assert prepare("42 U.S.C. § 1983", language="en", use_spacy=False).spoken_text == (
        "forty two U S C section one thousand nine hundred and eighty three"
    )
    assert prepare("ley 5.678", language="es", use_spacy=False).spoken_text == (
        "ley cinco mil seiscientos setenta y ocho"
    )
    assert prepare("legge n. 145/2018", language="it", use_spacy=False).spoken_text == (
        "legge numero centoquarantacinque del duemiladiciotto"
    )
