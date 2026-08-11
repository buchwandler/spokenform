from spokenform import prepare


def test_locale_ordinal_symbols_are_expanded_without_sentence_final_cardinal_rewrites() -> None:
    assert prepare("1º", language="es", use_spacy=False).spoken_text == "primero"
    assert prepare("2ª", language="it", use_spacy=False).spoken_text == "secondo"
    assert prepare("2ème", language="fr", use_spacy=False).spoken_text == "deuxième"
    assert prepare("The 1st release", language="en", use_spacy=False).spoken_text == (
        "The 1st release"
    )
    assert prepare("1.", language="de", use_spacy=False).spoken_text == "1."
