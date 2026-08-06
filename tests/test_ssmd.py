import pytest

from spokenform import prepare


def test_ssmd_clean_text_language_and_phoneme_protection() -> None:
    result = prepare(
        '[Bonjour]{lang="fr"} [SQL]{ph="ˈsiːkwəl"} 2 tests.',
        language="en",
        markup="ssmd",
    )
    assert result.clean_text == "Bonjour SQL 2 tests."
    assert result.spoken_text == "Bonjour SQL two tests."
    assert result.language_spans[0].language == "fr"
    assert result.language_spans[0].source == "ssmd"
    assert result.semantic_spans[1].protected
    assert result.marked_text is None


def test_ssmd_detected_mark_rendering_is_explicit() -> None:
    result = prepare(
        '[Bonjour]{lang="fr"} world',
        language="en",
        markup="ssmd",
        render_language_marks=True,
    )
    assert result.marked_text is not None
    assert '[Bonjour]{lang="fr"}' in result.marked_text
    assert result.render_ssmd(source="clean").startswith("[Bonjour]")


def test_plain_brackets_are_not_ssmd() -> None:
    result = prepare('[Bonjour]{lang="fr"}', language="en", markup="plain")
    assert result.clean_text == result.source_text
    assert result.semantic_spans == ()


def test_auto_mode_only_parses_markup_like_text() -> None:
    result = prepare('[Bonjour]{lang="fr"}', language="en", markup="auto")
    assert result.clean_text == "Bonjour"


def test_malformed_ssmd_is_strict() -> None:
    with pytest.raises(ValueError):
        prepare("[broken]{lang=", markup="ssmd", strict=True)
