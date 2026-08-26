from __future__ import annotations

from spokenform import prepare


def test_japanese_abbreviations_quantities_dates_times_and_currency() -> None:
    result = prepare(
        "№ 12 ㈱東京商事 20°C 80 km/h 2026年8月26日 18時20分 ¥500 AAPL",
        language="ja",
        use_spacy=False,
    )
    assert result.spoken_text == (
        "番号 十二 株式会社東京商事 摂氏 二十 度 時速 八十 キロメートル "
        "二零二六年八月二十六日 十八時二十分 五百円 AAPL"
    )
    assert result.source_replacements[0].source == "№"
    assert any(item.rule == "ja.quantity" for item in result.source_replacements)
    assert any(item.rule == "ja.date" for item in result.source_replacements)
    assert any(item.rule == "ja.time" for item in result.source_replacements)
    assert any(item.rule == "ja.currency" for item in result.source_replacements)
    quantity = next(item for item in result.source_replacements if item.rule == "ja.quantity")
    assert result.map_source_span(quantity.source_start, quantity.source_end) == (
        quantity.output_start,
        quantity.output_end,
    )


def test_japanese_unknown_identifiers_are_preserved() -> None:
    result = prepare("AAPL NASA", language="ja", use_spacy=False)
    assert result.spoken_text == "AAPL NASA"
    assert not result.source_replacements
