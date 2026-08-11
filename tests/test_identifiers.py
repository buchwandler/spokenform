from spokenform import prepare


def test_isbn_validation_and_typed_rendering() -> None:
    result = prepare("ISBN 978-0-306-40615-7", language="en", use_spacy=False)
    assert result.spoken_text == "i s b n nine seven eight hyphen zero hyphen three zero six hyphen four zero six one five hyphen seven"
    assert any(item.rule == "sequence.isbn" for item in result.source_replacements)
    invalid = prepare("ISBN 978-0-306-40615-8", language="en", use_spacy=False)
    assert not any(item.rule == "sequence.isbn" for item in invalid.source_replacements)


def test_formula_codes_legal_references_and_scores_use_typed_renderers() -> None:
    assert prepare("H₂O", language="en", use_spacy=False).spoken_text == "h two o"
    assert prepare("VW789XY", language="it", use_spacy=False).spoken_text == (
        "vu doppia vu settecentottantanove ics ipsilon"
    )
    assert prepare("§ 12 BGB", language="de", use_spacy=False).spoken_text == (
        "Paragraph zwölf B G B"
    )
    assert prepare("Final 2:1", language="en", use_spacy=False).spoken_text == (
        "Final two to one"
    )
