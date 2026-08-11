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


def test_sequence_policy_can_keep_alpha_runs_lexical() -> None:
    policy = SequenceRenderPolicy(alpha_mode="lexical", digit_mode="digitwise")
    assert render_sequence("TravelTips_2024", language="en", policy=policy) == (
        "T r a v e l T i p s underscore two zero two four"
    )


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
