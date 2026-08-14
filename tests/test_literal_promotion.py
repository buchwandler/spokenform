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


def test_literal_promotion_uses_typed_url_email_and_version_renderers() -> None:
    result = prepare(
        "Visit https://www.example.com/page1 and email support@company.com; update v3.1.4.",
        language="en",
        normalize_literals=True,
        use_spacy=False,
    )
    assert "h t t p s colon slash slash w w w dot example dot com slash" in result.spoken_text
    assert "support at company dot com" in result.spoken_text
    assert "version three dot one dot four." in result.spoken_text


def test_bare_domain_and_contextual_version_are_profile_scoped() -> None:
    source = "Visit example.com/page1; version 5.0.1 is installed."
    safe = prepare(source, language="en", use_spacy=False)
    normalized = prepare(source, language="en", normalize_literals=True, use_spacy=False)
    assert "example.com/page1" in safe.spoken_text
    assert "version five dot zero dot one" in safe.spoken_text
    assert "example dot com slash" in normalized.spoken_text
    assert "version five dot zero dot one" in normalized.spoken_text


def test_literal_promotion_remains_opt_in_for_defaults() -> None:
    source = "https://example.org/v1.2.3"
    default = prepare(source, language="en", use_spacy=False)
    promoted = prepare(source, language="en", use_spacy=False, normalize_literals=True)
    assert default.spoken_text == source
    assert promoted.spoken_text != source


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
    assert standalone.spoken_text == "IV C D D V D"
