from __future__ import annotations

import pytest

from spokenform import ProtectedSpan, prepare


def _assert_source_replacements(source: str, language: str) -> None:
    result = prepare(source, language=language, use_spacy=False)
    assert result.source_replacements
    for item in result.source_replacements:
        assert source[item.source_start : item.source_end] == item.source
        assert result.spoken_text[item.output_start : item.output_end] == item.replacement


def test_czech_migrated_sentence_has_exact_source_coordinates() -> None:
    source = "Dr. Novák má 2 kg a teplota je 25°C."
    result = prepare(source, language="cs", use_spacy=False)
    assert result.spoken_text == (
        "Doktor Novák má dva kilogramy a teplota je dvacet pět stupňů Celsia."
    )
    assert [
        (item.source_start, item.source_end, item.source, item.replacement)
        for item in result.source_replacements
    ] == [
        (0, 3, "Dr.", "Doktor"),
        (13, 17, "2 kg", "dva kilogramy"),
        (31, 35, "25°C", "dvacet pět stupňů Celsia"),
    ]
    _assert_source_replacements(source, "cs")


def test_czech_repeated_fragments_keep_distinct_replacements() -> None:
    source = "2 kg a 2 kg"
    result = prepare(source, language="cs", use_spacy=False)
    assert [(item.source_start, item.source_end) for item in result.source_replacements] == [
        (0, 4),
        (7, 11),
    ]


def test_czech_protection_preserves_one_quantity_and_normalizes_the_other() -> None:
    source = "2 kg a 3 kg"
    result = prepare(
        source,
        language="cs",
        use_spacy=False,
        protected_spans=[ProtectedSpan(0, 4, kind="literal")],
    )
    assert result.spoken_text == "2 kg a tři kilogramy"
    assert all(
        item.source != "2 kg" or item.source_start != 0 for item in result.source_replacements
    )
    assert any(item.source == "3 kg" for item in result.source_replacements)


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("fr", "Mme Dupont a 1,5 kg."),
        ("es", "Dr. Pérez tiene 2 kg y 25°C."),
        ("it", "Prof. Klein ha 1,5 kg e 25°C."),
        ("pt-br", "Dr. Ana tem 1,5 kg, 25°C e paga R$ 12,80 — ok."),
    ],
)
def test_cross_locale_migrations_preserve_source_replacement_coordinates(
    language: str, source: str
) -> None:
    _assert_source_replacements(source, language)


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("fr", "1,5 kg et 1,5 kg"),
        ("es", "1 kg y 1 kg"),
        ("it", "1,5 kg e 1,5 kg"),
        ("pt-br", "1,5 kg e 1,5 kg"),
    ],
)
def test_cross_locale_repeated_fragments_remain_distinct(language: str, source: str) -> None:
    result = prepare(source, language=language, use_spacy=False)
    replacements = [item for item in result.source_replacements if item.source.startswith("1")]
    assert len(replacements) == 2
    assert replacements[0].source_start < replacements[1].source_start


@pytest.mark.parametrize(
    ("language", "source", "protected"),
    [
        ("fr", "5€ 14h30", (0, 2)),
        ("es", "25°C y 2 kg", (0, 5)),
        ("it", "25°C e 2 kg", (0, 5)),
        ("pt-br", "25°C e 2 kg", (0, 5)),
    ],
)
def test_cross_locale_protection_keeps_adjacent_semantics(
    language: str, source: str, protected: tuple[int, int]
) -> None:
    result = prepare(source, language=language, use_spacy=False, protected_spans=[protected])
    assert source[protected[0] : protected[1]] in result.spoken_text
    assert any(item.source_start >= protected[1] for item in result.source_replacements)
    assert all(
        item.source_end <= protected[0] or item.source_start >= protected[1]
        for item in result.source_replacements
    )


@pytest.mark.parametrize(
    "source", ["The temperature is 37°C.", "approximately 37°C", "It is 37°C outside today."]
)
def test_english_temperature_does_not_trigger_circa_abbreviation(source: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert "thirty seven degrees Celsius" in result.spoken_text
    assert "circa" not in result.spoken_text.lower()


@pytest.mark.parametrize(
    ("source", "expected"),
    [("50%", "오십 퍼센트"), ("5km", "오 킬로미터")],
)
def test_korean_semantic_gaps_are_prepared_upstream(source: str, expected: str) -> None:
    assert prepare(source, language="ko", use_spacy=False).spoken_text == expected
