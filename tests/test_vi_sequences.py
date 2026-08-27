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


def test_vietnamese_digit_and_letter_rendering_is_explicit() -> None:
    assert render_digits("0123456789", language="vi") == (
        "không một hai ba bốn năm sáu bảy tám chín"
    )
    assert render_letters("ABC", language="vi") == "A B C"
    assert render_alnum("A2", language="vi") == "A hai"


def test_vietnamese_literal_vocabulary_has_no_english_defaults() -> None:
    vocab = vocabulary("vi")
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
    assert render_sequence("A/B", language="vi") == "A / B"


def test_unreviewed_vietnamese_shared_sequences_and_ranges_fail_closed() -> None:
    for source in ("A/B", "3-5", "ISBN 978-1-4028-9462-6", "H2O", "AAPL", "§ 12", "12:34"):
        assert iter_sequence_replacements(source, language="vi") == ()
    assert iter_range_replacements("3-5", language="vi") == ()


def test_vietnamese_protection_has_no_english_fallback() -> None:
    source = "https://example.com/v1.2.3 test@example.com v1.2.3"
    result = prepare(source, language="vi", use_spacy=False)
    assert result.spoken_text == source
    assert not {"point", "slash", "to", "at", "hash", "minus", "plus"} & set(
        result.spoken_text.split()
    )
