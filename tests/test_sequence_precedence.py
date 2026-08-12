from spokenform import prepare


def test_contextual_years_beat_generic_numbers_without_claiming_identifiers() -> None:
    for source in (
        "2006 IUCN report",
        "Liturgical Press, 2008.",
        "October 2009",
        "Ayers, Andrew (2004).",
    ):
        result = prepare(source, language="en", use_spacy=False)
        assert any(item.rule == "sequence.year" for item in result.source_replacements)
    identifier = prepare("serial number 2008", language="en", use_spacy=False)
    assert not any(item.rule == "sequence.year" for item in identifier.source_replacements)


def test_phone_range_and_product_lexical_precedence() -> None:
    phone = prepare("Text me at 555-7890", language="en", use_spacy=False)
    assert any(item.rule == "sequence.phone" for item in phone.source_replacements)
    assert not any(item.rule == "sequence.numeric-range" for item in phone.source_replacements)
    lexical = prepare("LaCrosse McGill VanRullen", language="en", use_spacy=False)
    assert not lexical.source_replacements


def test_typed_contexts_do_not_claim_initials_or_single_letter_parts() -> None:
    author = prepare(
        "George M. Scott was the pastor.", language="en", use_spacy=False, normalize_literals=True
    )
    assert "the one thousandth" not in author.spoken_text

    part = prepare(
        "Part A. General Pathology, Section II.",
        language="en",
        use_spacy=False,
        normalize_literals=True,
        symbol_mode="remove",
    )
    assert "part number" not in part.spoken_text.casefold()


def test_literal_rendering_and_contextual_phones_are_locale_safe() -> None:
    url = prepare(
        "Le site est http://site.fr.", language="fr", use_spacy=False, normalize_literals=True
    )
    assert (
        url.spoken_text
        == "Le site est h t t p deux-points barre oblique barre oblique s i t e point f r."
    )

    version = prepare(
        "La versione è v2.5.1.", language="it", use_spacy=False, normalize_literals=True
    )
    assert version.spoken_text == "La versione è v due punto cinque punto uno."

    phone = prepare("Il centralino è 800123456", language="it", use_spacy=False)
    assert phone.spoken_text == "Il centralino è otto zero zero uno due tre quattro cinque sei"
