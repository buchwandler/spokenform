import pytest

from spokenform import ProtectedSpan, prepare
from spokenform.precedence import priority_for_rule
from spokenform.recognizers.sequences import iter_lexical_slash_candidates


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("open/close", "open slash close"),
        ("target/destination", "target slash destination"),
        ("head/processor", "head slash processor"),
        ("torus/whatever", "torus slash whatever"),
        ("we/somebody", "we slash somebody"),
        ("where/who", "where slash who"),
        ("proximity/safety", "proximity slash safety"),
        ("and/or", "and slash or"),
        ("yes/no", "yes slash no"),
        ("input/output/error", "input slash output slash error"),
    ],
)
def test_english_lexical_slash_replaces_the_whole_compound(source: str, expected: str) -> None:
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == expected
    assert len(result.source_replacements) == 1
    edit = result.source_replacements[0]
    assert (edit.source_start, edit.source_end, edit.source) == (0, len(source), source)
    assert edit.replacement == expected
    assert edit.rule == "sequence.lexical-slash"
    assert edit.kind == "structured"
    assert edit.recognition_domain == "core"
    assert result.spoken_text[edit.output_start : edit.output_end] == expected
    assert result.map_source_span(edit.source_start, edit.source_end) == (
        edit.output_start,
        edit.output_end,
    )


def test_lexical_slash_accepts_unicode_alphabetic_components_and_sentence_punctuation() -> None:
    result = prepare("Straße/Öffnung.", language="en", use_spacy=False)

    assert result.spoken_text == "Straße slash Öffnung."
    assert [(edit.source, edit.replacement) for edit in result.source_replacements] == [
        ("Straße/Öffnung", "Straße slash Öffnung")
    ]


@pytest.mark.parametrize(
    "protected_span",
    [
        (0, 10),
        (4, 5),
        (0, 4),
    ],
)
def test_any_protected_overlap_suppresses_the_whole_candidate(
    protected_span: tuple[int, int],
) -> None:
    source = "open/close"
    result = prepare(
        source,
        language="en",
        use_spacy=False,
        protected_spans=[ProtectedSpan(*protected_span, kind="caller")],
    )

    assert result.spoken_text == source
    assert not any(edit.rule == "sequence.lexical-slash" for edit in result.source_replacements)
    assert list(iter_lexical_slash_candidates(source, protected_ranges=[protected_span])) == []


@pytest.mark.parametrize(
    "source",
    [
        "1/2",
        "12/05/2026",
        "2026/10/27",
        "https://example.org/a/b",
        "example.org/a/b",
        "/usr/local/bin",
        "C:/Users/name",
        "km/h",
        "m/s",
        "g/cm3",
        "L/100km",
        "USD/EUR",
        "EUR/USD",
        "ABC/123",
        "+49/30/123456",
        "foo 1 km/hbar",
        "Δy/Δx",
        "x/y=z",
        "x/y = z",
    ],
)
def test_structured_slash_forms_are_not_lexical_candidates(source: str) -> None:
    assert list(iter_lexical_slash_candidates(source)) == []
    result = prepare(source, language="en", use_spacy=False)
    assert not any(edit.rule == "sequence.lexical-slash" for edit in result.source_replacements)


def test_specific_fraction_and_date_rules_keep_precedence() -> None:
    fraction = prepare("1/2", language="en", use_spacy=False)
    date = prepare("12/05/2026", language="en", use_spacy=False)

    assert any(edit.rule == "sequence.fraction" for edit in fraction.source_replacements)
    assert any(edit.rule == "en.date" for edit in date.source_replacements)
    assert priority_for_rule("sequence.lexical-slash") < priority_for_rule("sequence.fraction")
    assert priority_for_rule("sequence.lexical-slash") < priority_for_rule("sequence.url")
    assert priority_for_rule("sequence.lexical-slash") < priority_for_rule("sequence.exchange-rate")
    assert priority_for_rule("sequence.lexical-slash") < priority_for_rule("sequence.compound-unit")
    assert priority_for_rule("sequence.lexical-slash") < priority_for_rule("sequence.math")


@pytest.mark.parametrize("language", ["pt", "cs"])
def test_unreviewed_math_equations_are_not_lexical_slash_compounds(language: str) -> None:
    source = "x/y=z"
    result = prepare(source, language=language, use_spacy=False)

    assert result.spoken_text == source
    assert not any(edit.rule == "sequence.lexical-slash" for edit in result.source_replacements)


def test_supported_localized_vocabulary_and_unsupported_fail_closed() -> None:
    swedish = prepare("open/close", language="sv", use_spacy=False)
    russian = prepare("open/close", language="ru", use_spacy=False)

    assert swedish.spoken_text == "open snedstreck close"
    assert any(edit.rule == "sequence.lexical-slash" for edit in swedish.source_replacements)
    assert russian.spoken_text == "open/close"
    assert not any(edit.rule == "sequence.lexical-slash" for edit in russian.source_replacements)


def test_structured_expansion_toggle_disables_lexical_slash() -> None:
    result = prepare(
        "open/close",
        language="en",
        use_spacy=False,
        expand_structured=False,
        expand_numbers=False,
    )

    assert result.spoken_text == "open/close"
    assert not any(edit.rule == "sequence.lexical-slash" for edit in result.source_replacements)
