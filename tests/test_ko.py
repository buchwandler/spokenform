from __future__ import annotations

from spokenform import prepare


def test_korean_abbreviations_quantities_dates_times_and_currency() -> None:
    result = prepare(
        "№ 12 p. 12 ㈜한빛 AI KTX 20°C 80 km/h 7 L/100km 2026년 8월 26일 18시 20분 ₩5000 NASA",
        language="ko",
        use_spacy=False,
    )
    assert result.spoken_text == (
        "번호 십이 페이지 십이 주식회사한빛 에이아이 케이티엑스 섭씨 이십도 "
        "시속 팔십킬로미터 100킬로미터당 칠리터 이천이십육년 팔월 이십육일 "
        "열여덟시 이십분 오천 원 NASA"
    )
    assert any(item.rule == "ko.quantity" for item in result.source_replacements)
    assert any(item.rule == "ko.date" for item in result.source_replacements)
    assert any(item.rule == "ko.time" for item in result.source_replacements)
    assert any(item.rule == "ko.currency" for item in result.source_replacements)


def test_korean_unknown_identifiers_are_preserved() -> None:
    result = prepare("NASA AAPL A320 H100", language="ko", use_spacy=False)
    assert result.spoken_text == "NASA AAPL A320 H100"
