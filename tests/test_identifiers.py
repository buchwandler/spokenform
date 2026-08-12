from spokenform import prepare


def test_isbn_validation_and_typed_rendering() -> None:
    result = prepare("ISBN 978-0-306-40615-7", language="en", use_spacy=False)
    assert (
        result.spoken_text
        == "I S B N nine seven eight zero three zero six four zero six one five seven"
    )
    assert any(item.rule == "sequence.isbn" for item in result.source_replacements)
    invalid = prepare("ISBN 978-0-306-40615-8", language="en", use_spacy=False)
    assert any(item.rule == "sequence.isbn" for item in invalid.source_replacements)
    labeled = prepare("ISBN-10 0-306-40615-2", language="en", use_spacy=False)
    assert labeled.spoken_text.startswith("I S B N ten")
    assert any(item.rule == "sequence.isbn" for item in labeled.source_replacements)


def test_labeled_isbn_values_are_owned_before_phone_detection() -> None:
    for source in (
        "The ISBN is 978-3-16-148410-0",
        "The book's ISBN is 978-3-16-148410-0",
        "ISBN for this edition is 978-3-16-148410-0",
    ):
        result = prepare(source, language="en", use_spacy=False)
        assert sum(item.rule == "sequence.isbn" for item in result.source_replacements) == 2
        assert not any(item.rule == "sequence.phone" for item in result.source_replacements)


def test_formula_codes_legal_references_and_scores_use_typed_renderers() -> None:
    assert prepare("H₂O", language="en", use_spacy=False).spoken_text == "H two O"
    assert prepare("NaCl", language="en", use_spacy=False).spoken_text == "N a C l"
    assert prepare("H5N1", language="en", use_spacy=False).spoken_text == "H five N one"
    assert prepare("VW789XY", language="it", use_spacy=False).spoken_text == (
        "V W sette otto nove X Y"
    )
    assert prepare("§ 12 BGB", language="de", use_spacy=False).spoken_text == (
        "Paragraf zwölf B G B"
    )
    assert prepare("Final 2:1", language="en", use_spacy=False).spoken_text == ("Final two to one")


def test_typed_code_profiles_and_coordinate_directions_are_contextual() -> None:
    assert prepare("serial number: AB-123", language="en", use_spacy=False).spoken_text == (
        "serial number A B one two three"
    )
    assert prepare("Model E46", language="en", use_spacy=False).spoken_text == ("model E forty-six")
    assert prepare("12,3456° O", language="es", use_spacy=False).spoken_text == (
        "doce coma tres cuatro cinco seis grados oeste"
    )
    assert prepare("E46", language="en", use_spacy=False).spoken_text == "E46"


def test_locale_legal_reference_grammars_are_atomic() -> None:
    assert prepare("§ 823 Abs. 1 BGB", language="de", use_spacy=False).spoken_text == (
        "Paragraf achthundertdreiundzwanzig Absatz eins B G B"
    )
    assert prepare("StVO § 1", language="de", use_spacy=False).spoken_text == (
        "S T V O Paragraf eins"
    )
    assert prepare("42 U.S.C. § 1983", language="en", use_spacy=False).spoken_text == (
        "forty two U S C section one thousand nine hundred eighty three"
    )
    assert prepare("ley 5.678", language="es", use_spacy=False).spoken_text == (
        "ley cinco mil seiscientos setenta y ocho"
    )
    assert prepare("legge n. 145/2018", language="it", use_spacy=False).spoken_text == (
        "legge numero centoquarantacinque del duemiladiciotto"
    )


def test_brief_legal_references_use_atomic_contextual_renderers() -> None:
    docket = prepare("Docket No. 2022-5678", language="en", use_spacy=False)
    assert docket.spoken_text == "Docket Number twenty twenty two dash five six seven eight"
    assert any(item.rule == "sequence.legal" for item in docket.source_replacements)

    case = prepare("Case No. 1:22-cv-00123", language="en", use_spacy=False)
    assert (
        case.spoken_text == "Case Number one colon twenty two dash c v dash zero zero one two three"
    )

    assert prepare("Sentencia 4567/2024", language="es", use_spacy=False).spoken_text == (
        "sentencia cuatro mil quinientos sesenta y siete de dos mil veinticuatro"
    )
    assert prepare("regolamento n. 2017/745", language="it", use_spacy=False).spoken_text == (
        "regolamento numero duemiladiciassette del settecentoquarantacinque"
    )


def test_strongly_labeled_codes_use_digitwise_policies() -> None:
    assert prepare("barcode 123456789012", language="en", use_spacy=False).spoken_text == (
        "barcode one two three four five six seven eight nine zero one two"
    )
    assert prepare("Matrikelnummer 1234567", language="de", use_spacy=False).spoken_text == (
        "Matrikelnummer eins zwei drei vier fünf sechs sieben"
    )
    assert prepare("P/N 7890-12", language="en", use_spacy=False).spoken_text == (
        "P N seven eight nine zero one two"
    )
    result = prepare("X5Y-7890", language="en", use_spacy=False)
    assert result.spoken_text == "X five Y seven eight nine zero"
    assert any(item.rule == "sequence.product" for item in result.source_replacements)

    ordinary = prepare("2024 points", language="en", use_spacy=False)
    assert not any(item.rule == "sequence.product" for item in ordinary.source_replacements)
