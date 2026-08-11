import pytest

from spokenform import prepare
from spokenform.language import SUPPORTED_BASE_LANGUAGES
from spokenform.sequences import SequenceRenderPolicy, render_letters, render_sequence


@pytest.mark.parametrize("language", sorted(SUPPORTED_BASE_LANGUAGES))
def test_every_supported_language_renders_ascii_letters_without_index_errors(language: str) -> None:
    rendered = render_letters("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", language=language)
    assert rendered
    assert "IndexError" not in rendered


@pytest.mark.parametrize("language", sorted(SUPPORTED_BASE_LANGUAGES))
def test_mixed_identifier_rendering_is_total(language: str) -> None:
    rendered = render_sequence("XYZ-2024/Abc", language=language)
    assert rendered


def test_sequence_renderer_advances_past_whitespace() -> None:
    assert render_sequence("A B", language="de") == "A B"


def test_german_legal_reference_with_whitespace_completes() -> None:
    result = prepare("Nach Art. 1 Abs. 1 GG.", language="de_DE", use_spacy=False)
    assert result.spoken_text == "Nach A R T Punkt eins A B S Punkt eins G G."


def test_sequence_policy_can_keep_alpha_runs_lexical() -> None:
    policy = SequenceRenderPolicy(alpha_mode="lexical", digit_mode="digitwise")
    assert render_sequence("TravelTips_2024", language="en", policy=policy) == (
        "TravelTips underscore two zero two four"
    )


def test_sequence_alpha_modes_are_distinct() -> None:
    assert render_sequence(
        "ISBN", language="es", policy=SequenceRenderPolicy(alpha_mode="lexical")
    ) == "ISBN"
    assert render_sequence(
        "ISBN", language="es", policy=SequenceRenderPolicy(alpha_mode="grapheme_spaced")
    ) == "I S B N"
    assert render_sequence(
        "ISBN", language="es", policy=SequenceRenderPolicy(alpha_mode="spoken_letter_names")
    ) == "i ese be ene"


def test_hashtag_and_mention_rendering_is_lexical() -> None:
    assert prepare("#TravelTips @JeanDupont", language="en", use_spacy=False).spoken_text == (
        "hashtag Travel Tips at Jean Dupont"
    )
    assert prepare("#vacanze2024", language="it", use_spacy=False).spoken_text == (
        "hashtag vacanze duemilaventiquattro"
    )
    assert prepare("#Été2024", language="fr", use_spacy=False).spoken_text == (
        "hashtag Été deux mille vingt-quatre"
    )


def test_opaque_short_handles_use_letterwise_rendering() -> None:
    assert prepare("#API2", language="en", use_spacy=False).spoken_text == "hashtag a p i two"
    assert prepare("#E.", language="en", use_spacy=False).spoken_text == "hashtag e."


def test_coordinates_support_integer_precision_and_direction_words() -> None:
    assert prepare("90° N", language="en", use_spacy=False).spoken_text == "ninety degrees north"
    assert prepare("0°", language="de", use_spacy=False).spoken_text == "null Grad"
    assert prepare("12.3456° E", language="de", use_spacy=False).spoken_text == (
        "zwölf Komma drei vier fünf sechs Grad Ost"
    )


def test_coordinates_fail_closed_when_directional_ranges_are_invalid() -> None:
    assert prepare("91° N", language="en", use_spacy=False).spoken_text == "ninety one° N"
    assert prepare("181° E", language="en", use_spacy=False).spoken_text == "one hundred and eighty one° E"


def test_isbn_and_sports_scores_use_category_specific_policies() -> None:
    isbn = prepare("ISBN 978-3-16-148410-0", language="en", use_spacy=False)
    assert isbn.spoken_text == "i s b n nine seven eight three one six one four eight four one zero zero"
    assert any(item.rule == "sequence.isbn" for item in isbn.source_replacements)

    assert prepare("final 3-2", language="en", use_spacy=False).spoken_text == (
        "final three to two"
    )
    assert prepare("punteggio 3 a 0", language="it", use_spacy=False).spoken_text == (
        "punteggio tre a zero"
    )
    assert prepare("3-2", language="en", use_spacy=False).spoken_text == "three-two"


def test_fraction_and_acronym_policies_are_high_confidence_only() -> None:
    assert prepare("½ ⅝", language="it", use_spacy=False).spoken_text == (
        "un mezzo cinque ottavi"
    )
    assert prepare("NASA BND API", language="en", use_spacy=False).spoken_text == (
        "nasa b n d API"
    )
    protected = prepare("https://example.org/v1.2.3", language="en", use_spacy=False)
    assert protected.spoken_text == "https://example.org/v1.2.3"


def test_generic_uppercase_acronyms_are_grapheme_spaced() -> None:
    result = prepare("ABC", language="en", use_spacy=False)
    assert result.spoken_text == "A B C"
    assert any(item.rule == "sequence.acronym" for item in result.source_replacements)


@pytest.mark.parametrize(
    ("language", "source", "expected"),
    [
        ("en", "1/2", "one half"),
        ("de", "3/7", "drei Siebtel"),
        ("es", "1 1/2", "uno y un medio"),
        ("fr", "3/7", "trois septièmes"),
        ("it", "1½", "uno e un mezzo"),
    ],
)
def test_slash_and_mixed_fractions_are_semantic(language: str, source: str, expected: str) -> None:
    result = prepare(source, language=language, use_spacy=False)
    assert result.spoken_text == expected
    assert any(item.rule == "sequence.fraction" for item in result.source_replacements)


def test_fraction_does_not_claim_url_or_full_date_shape() -> None:
    url = prepare("https://example.org/1/2", language="en", use_spacy=False)
    assert url.spoken_text == "https://example.org/1/2"
    date = prepare("2025/03/15", language="en", use_spacy=False)
    assert not any(item.rule == "sequence.fraction" for item in date.source_replacements)
    assert not any(item.rule == "sequence.phone" for item in date.source_replacements)
