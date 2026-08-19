from __future__ import annotations

import pytest

from spokenform import prepare


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("Q1", "quarter one"),
        ("Q2 2023", "quarter two two thousand twenty three"),
        ("FY2024 Q3", "fiscal year two thousand twenty four quarter three"),
    ),
)
def test_quarter_notation_is_explicit_and_contextual(source: str, expected: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert result.spoken_text == expected
    assert any(item.rule == "sequence.quarter" for item in result.source_replacements)


@pytest.mark.parametrize("source", ("Q5", "model Q2", "part Q2-17"))
def test_quarter_near_misses_remain_unclaimed(source: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert not any(item.rule == "sequence.quarter" for item in result.source_replacements)


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        ("ticker CMCSA", "ticker C M C S A"),
        ("stock symbol AAPL", "stock symbol A A P L"),
        ("NASDAQ: MSFT", "NASDAQ: M S F T"),
        ("NYSE: IBM", "NYSE: I B M"),
    ),
)
def test_explicit_ticker_contexts_are_spelled(source: str, expected: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert result.spoken_text == expected
    assert any(item.rule == "sequence.ticker" for item in result.source_replacements)


def test_unlabeled_uppercase_word_is_not_a_ticker() -> None:
    result = prepare("APPLE", language="en", use_spacy=False)
    assert not any(item.rule == "sequence.ticker" for item in result.source_replacements)
