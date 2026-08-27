from __future__ import annotations

from spokenform import prepare
from spokenform.recognizers.ranges import iter_replacements as iter_range_replacements
from spokenform.recognizers.sequences import iter_sequence_replacements
from spokenform.sequences import (
    render_alnum,
    render_digits,
    render_letters,
    render_sequence,
    vocabulary,
)


def test_th_explicit_digit_and_letter_rendering() -> None:
    assert render_digits("0123456789", language="th") == ("ศูนย์ หนึ่ง สอง สาม สี่ ห้า หก เจ็ด แปด เก้า")
    assert render_letters("ABC", language="th") == "A B C"
    assert render_alnum("A2", language="th") == "A สอง"


def test_th_sequence_punctuation_is_unset_and_literal() -> None:
    vocab = vocabulary("th")
    assert all(
        value is None
        for value in (
            vocab.point,
            vocab.slash,
            vocab.hyphen,
            vocab.underscore,
            vocab.colon,
            vocab.at,
            vocab.hash,
            vocab.plus,
            vocab.equals,
            vocab.open_paren,
            vocab.close_paren,
        )
    )
    assert render_sequence("A/B", language="th") == "A / B"


def test_th_unreviewed_sequences_and_ranges_fail_closed() -> None:
    for source in (
        "ABC-123",
        "3-5",
        "1/2",
        "ISBN 978-1-4028-9462-6",
        "H2O",
        "0914.858.982",
        "v1.2.3",
    ):
        assert iter_sequence_replacements(source, language="th") == ()
        assert prepare(source, language="th", use_spacy=False).spoken_text == source
    assert iter_range_replacements("3-5", language="th") == ()


def test_th_protected_urls_and_email_have_no_english_semantic_fallback() -> None:
    source = "https://example.com/v1.2.3 test@example.com"
    result = prepare(source, language="th", use_spacy=False).spoken_text
    assert result == source
    assert not {"point", "slash", "to", "at", "hash", "minus", "plus"} & set(result.split())
