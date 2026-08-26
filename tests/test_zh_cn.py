from __future__ import annotations

import pytest

from spokenform import prepare


@pytest.mark.parametrize("language", ["zh", "zh_CN", "cn"])
def test_chinese_dates_times_and_numbers(language: str) -> None:
    result = prepare(
        "123 -123 1.23 2026年8月26日 2026-08-26 18点20分",
        language=language,
        use_spacy=False,
    )
    assert "一百二十三" in result.spoken_text
    assert "负一百二十三" in result.spoken_text
    assert "一点二三" in result.spoken_text
    assert "二零二六年八月二十六日" in result.spoken_text
    assert "十八点二十分" in result.spoken_text


def test_mainland_chinese_abbreviations_quantities_and_currency() -> None:
    result = prepare(
        "№ 12 AI技术 GDP增长 WHO发布 5 km 20°C 80 km/h "
        "7 L/100km 5 m³/s ¥12.50 OpenAI AIGC A320 H100 AAPL NASA",
        language="zh_CN",
        use_spacy=False,
    )
    assert result.spoken_text == (
        "编号 十二 人工智能技术 国内生产总值增长 世界卫生组织发布 五 公里 二十 摄氏度 "
        "每小时八十公里 每100公里七升 每秒五立方米 十二元五角 "
        "OpenAI AIGC A320 H100 AAPL NASA"
    )
    assert any(item.rule == "zh.quantity" for item in result.source_replacements)
    assert any(item.rule == "zh.currency" for item in result.source_replacements)


def test_chinese_date_mapping_is_source_aligned() -> None:
    result = prepare("日期 2026年8月26日", language="zh_CN", use_spacy=False)
    replacement = next(item for item in result.source_replacements if item.rule == "zh.date")
    assert replacement.source == "2026年8月26日"
    assert result.map_source_span(replacement.source_start, replacement.source_end) == (
        replacement.output_start,
        replacement.output_end,
    )
