from __future__ import annotations

from spokenform import prepare
from spokenform.numeric_lexeme import normalize_numeric_compatibility, parse_numeric_lexeme


def test_numeric_compatibility_folds_only_full_width_numeric_spans() -> None:
    assert normalize_numeric_compatibility("２０ ２０．５ －３ ＋３ ２０，０００") == (
        "20 20.5 -3 +3 20,000"
    )
    assert normalize_numeric_compatibility("Ａ３２０ OpenAI ㈱") == "Ａ３２０ OpenAI ㈱"


def test_full_width_lexemes_parse_under_cjk_profiles() -> None:
    for raw, expected in (("２０", "20"), ("２０．５", "20"), ("－３", "3"), ("＋３", "3")):
        normalized = normalize_numeric_compatibility(raw)
        lexeme = parse_numeric_lexeme(normalized, "ja", context="plain")
        assert lexeme is not None
        assert lexeme.integer_digits == expected


def test_compatibility_symbols_survive_numeric_normalization() -> None:
    result = prepare(
        "㈱東京 ２０．５ kg",
        language="ja",
        expand_structured=False,
        expand_numbers=False,
        use_spacy=False,
    )
    assert result.spoken_text == "株式会社東京 20.5 キログラム"
    assert result.source_replacements[0].source == "㈱"
    assert result.source_replacements[0].replacement == "株式会社"
    numeric = next(item for item in result.source_replacements if item.source_start == 4)
    assert numeric.source == "２０．５ kg"
    assert numeric.replacement == "20.5 キログラム"
    assert numeric.source_end == 11
