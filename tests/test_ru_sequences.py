from __future__ import annotations

import pytest

from spokenform import prepare
from spokenform.recognizers import iter_range_replacements, iter_sequence_replacements
from spokenform.sequences import render_digits, render_letters, vocabulary


def test_russian_direct_digit_primitives() -> None:
    assert render_digits("0123456789", language="ru") == (
        "ноль один два три четыре пять шесть семь восемь девять"
    )


def test_russian_letters_are_conservative() -> None:
    assert render_letters("EU", language="ru") == "E U"


def test_russian_sequence_vocabulary_has_no_english_defaults() -> None:
    assert vocabulary("ru").point is None
    assert vocabulary("ru").slash is None
    assert vocabulary("ru").hyphen is None
    assert vocabulary("ru").underscore is None
    assert vocabulary("ru").colon is None
    assert vocabulary("ru").at is None
    assert vocabulary("ru").hash is None
    assert vocabulary("ru").plus is None
    assert vocabulary("ru").equals is None


@pytest.mark.parametrize(
    "source",
    ["3-5", "ISBN 978-1-4028-9462-6", "12:34", "A/B", "§ 12", "H2O", "A1"],
)
def test_russian_shared_sequences_and_ranges_fail_closed(source: str) -> None:
    assert iter_sequence_replacements(source, language="ru") == ()
    if source == "3-5":
        assert iter_range_replacements(source, language="ru") == ()


def test_russian_sentence_does_not_inject_english_sequence_words() -> None:
    source = "Откройте https://example.com/v1.2.3, напишите test@example.com и пройдите 2 км."
    result = prepare(source, language="ru", use_spacy=False)
    assert result.spoken_text == (
        "Откройте https://example.com/v1.2.3, напишите test@example.com и пройдите два километра."
    )
    for forbidden in (
        "and",
        "point",
        "slash",
        "underscore",
        "colon",
        "at",
        "hash",
        "hyphen",
        "equals",
    ):
        assert forbidden not in result.spoken_text
