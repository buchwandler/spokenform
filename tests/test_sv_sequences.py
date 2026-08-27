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


def test_swedish_digit_and_letter_rendering_is_explicit() -> None:
    assert render_digits("0123456789", language="sv") == (
        "noll ett två tre fyra fem sex sju åtta nio"
    )
    assert render_letters("EU", language="sv") == "E U"
    assert render_alnum("A2", language="sv") == "A två"


def test_swedish_literal_vocabulary_does_not_use_english_defaults() -> None:
    assert vocabulary("sv").at == "snabel-a"
    assert vocabulary("sv").slash == "snedstreck"
    assert vocabulary("sv").underscore == "understreck"
    assert vocabulary("sv").point is None
    assert vocabulary("sv").hyphen is None
    assert render_sequence("EU/@", language="sv") == "E U snedstreck snabel-a"
    assert render_sequence("1.2", language="sv") == "ett . två"


def test_unreviewed_swedish_shared_sequences_and_ranges_fail_closed() -> None:
    for source in ("3-5", "ISBN 978-1-4028-9462-6", "12:34", "A/B", "§ 12"):
        assert iter_sequence_replacements(source, language="sv") == ()
    assert iter_range_replacements("3-5", language="sv") == ()


def test_swedish_high_confidence_protection_has_no_english_fallback() -> None:
    source = "Besök https://example.com/v1.2.3, mejla test@example.com och gå 2 km."
    result = prepare(source, language="sv", use_spacy=False)
    assert (
        result.spoken_text
        == "Besök https://example.com/v1.2.3, mejla test@example.com och gå två kilometer."
    )
    assert not {"and", "dot", "slash", "question mark"} & set(result.spoken_text.split())
