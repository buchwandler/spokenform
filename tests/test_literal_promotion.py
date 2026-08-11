from spokenform import ProtectedSpan, prepare


def test_opt_in_literal_promotion_renders_url_email_and_version() -> None:
    result = prepare(
        "https://example.org/a2 dev2@example.org v1.2.3",
        language="en",
        normalize_literals=True,
        use_spacy=False,
    )
    assert "sequence.url" in {item.rule for item in result.source_replacements}
    assert "sequence.email" in {item.rule for item in result.source_replacements}
    assert "sequence.version" in {item.rule for item in result.source_replacements}
    assert "at" in result.spoken_text


def test_literal_promotion_keeps_caller_protected_spans_absolute() -> None:
    source = "See https://example.org/a2 and Chapter IV"
    start = source.index("https://")
    end = start + len("https://example.org/a2")
    result = prepare(
        source,
        language="en",
        normalize_literals=True,
        protected_spans=[ProtectedSpan(start, end, kind="url")],
        use_spacy=False,
    )
    assert "https://example.org/a2" in result.spoken_text
    assert "Chapter four" in result.spoken_text


def test_contextual_roman_numerals_do_not_claim_standalone_codes() -> None:
    chapter = prepare("Chapter IV", language="en", use_spacy=False)
    standalone = prepare("IV CD DVD", language="en", use_spacy=False)
    assert chapter.spoken_text == "Chapter four"
    assert standalone.spoken_text == "IV c d d v d"
