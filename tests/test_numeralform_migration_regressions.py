import pytest

from spokenform import prepare


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("de_DE", "€ 1.500"),
        ("de_DE", "£12.50"),
        ("de_DE", "$1.10"),
        ("en_US", "¥1,000,000"),
        ("it_IT", "$15.50"),
    ],
)
def test_currency_candidate_is_claimed_atomically(language: str, source: str) -> None:
    result = prepare(source, language=language, use_spacy=False)
    assert result.spoken_text != source
    assert any(
        replacement.source == source
        and replacement.source_start == 0
        and replacement.source_end == len(source)
        for replacement in result.source_replacements
    )


def test_italian_ordinary_cardinal_uses_corrected_numeralform_surface() -> None:
    assert prepare(
        "Il numero è 118.", language="it_IT", use_spacy=False
    ).spoken_text == "Il numero è centodiciotto."


def test_italian_social_identifier_suffix_is_digitwise() -> None:
    assert prepare(
        "Menziona @user123.", language="it_IT", use_spacy=False
    ).spoken_text == "Menziona chiocciola user uno due tre."


def test_italian_emergency_number_is_digitwise_in_call_context() -> None:
    assert prepare(
        "Chiama il 118 per l'ambulanza.", language="it_IT", use_spacy=False
    ).spoken_text == "Chiama il uno uno otto per l'ambulanza."


def test_same_digits_remain_cardinal_without_identifier_context() -> None:
    assert prepare(
        "Il numero è 118.", language="it_IT", use_spacy=False
    ).spoken_text == "Il numero è centodiciotto."


def test_german_section_reference_is_not_a_date() -> None:
    assert prepare(
        "Siehe Abschn. 3.2.", language="de_DE", use_spacy=False
    ).spoken_text == "Siehe Abschnitt drei Punkt zwei."


def test_german_currency_decimal_after_exchange_operator_is_not_a_date() -> None:
    result = prepare(
        "Der Wechselkurs ist 1€ = $1.10.", language="de_DE", use_spacy=False
    )
    assert "erster zehnter" not in result.spoken_text
    assert not any(item.rule == "de.date" for item in result.source_replacements)


def test_german_positive_dotted_date_context_is_preserved() -> None:
    result = prepare(
        "Der Termin ist am 3.2.", language="de_DE", use_spacy=False
    )
    assert "dritten zweiten" in result.spoken_text
    assert any(item.rule == "de.date" for item in result.source_replacements)


def test_social_identifier_matrix_preserves_reviewed_year_and_marker_policies() -> None:
    cases = (
        ("en", "@abc007", "at abc zero zero seven"),
        ("en", "#Summer2024", "hashtag Summer twenty twenty four"),
        ("en", "#Formula1", "hashtag Formula one"),
        ("en", "@EU_27", "at e u two seven"),
        ("de", "@abc007", "at abc null null sieben"),
        ("es-MX", "@abc007", "arroba abc cero cero siete"),
        ("fr", "@abc007", "arobase abc zéro zéro sept"),
        ("it", "@abc007", "chiocciola abc zero zero sette"),
    )
    for language, source, expected in cases:
        assert prepare(source, language=language, use_spacy=False).spoken_text == expected


def test_explicit_isbn_label_allows_identifier_shaped_non_checksum_value() -> None:
    result = prepare("ISBN 123-456", language="en", use_spacy=False)
    assert result.spoken_text == "I S B N one two three four five six"
    assert any(item.rule == "sequence.isbn" for item in result.source_replacements)

def test_short_emergency_number_requires_context() -> None:
    assert prepare(
        "Chiama il 118 per l'ambulanza.", language="it_IT", use_spacy=False
    ).spoken_text.endswith("uno uno otto per l'ambulanza.")
    assert prepare(
        "Ho contato 118 elementi.", language="it_IT", use_spacy=False
    ).spoken_text != "Ho contato uno uno otto elementi."


def test_grouped_currency_does_not_leave_a_partial_suffix() -> None:
    result = prepare("¥1,000,000", language="en_US", use_spacy=False)
    assert ",000" not in result.spoken_text
