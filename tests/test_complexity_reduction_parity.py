from __future__ import annotations

import pytest

from spokenform import prepare
from spokenform.config import PreparationConfig
from spokenform.numeric_lexeme import parse_numeric_lexeme
from spokenform.structured import iter_structured_candidates


def candidate_signature(item: object) -> tuple[object, ...]:
    return (
        item.start,
        item.end,
        item.text,
        item.kind,
        item.language,
        item.rule,
        item.specificity,
        item.evidence_source,
        item.evidence_score,
        item.evidence_cues,
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "Python 3.9.7",
            ((7, 12, "three dot nine dot seven", "sequence.version", 2),),
        ),
        (
            "IPv4 192.168.1.1",
            ((5, 16, "one nine two point one six eight point one point one", "sequence.ipv4", 0),),
        ),
        (
            "final 10-7-3",
            (
                (6, 12, "ten to seven to three", "sequence.chained-score", 88),
                (9, 12, "seven to three", "sequence.sports", 84),
                (6, 10, "ten to seven", "sequence.sports", 0),
            ),
        ),
        (
            "ISBN 978-3-16-148410-0",
            (
                (
                    0,
                    22,
                    "I S B N nine seven eight three one six one four eight four one zero zero",
                    "sequence.isbn",
                    30,
                ),
                (0, 4, "I S B N", "sequence.isbn", 35),
                (
                    5,
                    22,
                    "nine seven eight three one six one four eight four one zero zero",
                    "sequence.isbn",
                    35,
                ),
            ),
        ),
        (
            "Docket No. 2022-5678",
            (
                (
                    11,
                    20,
                    "two thousand twenty two to five thousand six hundred seventy eight",
                    "sequence.numeric-range",
                    55,
                ),
                (
                    0,
                    20,
                    "Docket Number twenty twenty two dash five six seven eight",
                    "sequence.legal",
                    0,
                ),
            ),
        ),
    ],
)
def test_candidate_stream_signature_and_order_are_stable(
    source: str, expected: tuple[tuple[object, ...], ...]
) -> None:
    candidates = tuple(
        candidate_signature(item) for item in iter_structured_candidates(source, language="en")
    )
    compact = tuple(
        (start, end, text, rule, specificity)
        for start, end, text, _, _, rule, specificity, *_ in candidates
    )
    assert compact == expected


@pytest.mark.parametrize(
    ("source", "language", "expected"),
    [
        ("Siehe § 3 BGB.", "de", "Siehe Paragraf drei B G B."),
        (
            "42 U.S.C. § 1983",
            "en",
            "forty two U S C section one thousand nine hundred eighty three",
        ),
        ("Artículo 5 de la ley 12/2020", "es", "Artículo cinco de la ley doce/dos mil veinte"),
        ("Apple (AAPL)", "en", "Apple (A A P L)"),
    ],
)
def test_legal_and_contextual_rendering_regressions(
    source: str, language: str, expected: str
) -> None:
    assert prepare(source, language=language, use_spacy=False).spoken_text == expected


@pytest.mark.parametrize(
    ("raw", "language", "context", "integer", "fraction", "grouping"),
    [
        ("1,234.56", "en-US", "currency", "1234", "56", (",",)),
        ("1.234,56", "de-DE", "currency", "1234", "56", (".",)),
        ("3,000", "es-MX", "quantity", "3000", None, (",",)),
        ("1,250,000", "es", "currency", "1250000", None, (",",)),
        ("1,25", "es", "currency", "1", "25", ()),
        ("3.1416", "es", "math", "3", "1416", ()),
        (".3", "en", "plain", "0", "3", ()),
        (".02", "en", "plain", "0", "02", ()),
    ],
)
def test_numeric_lexeme_truth_table(
    raw: str,
    language: str,
    context: str,
    integer: str,
    fraction: str | None,
    grouping: tuple[str, ...],
) -> None:
    lexeme = parse_numeric_lexeme(raw, language, context=context)
    assert lexeme is not None
    assert (lexeme.integer_digits, lexeme.fraction_digits, lexeme.grouping_separators) == (
        integer,
        fraction,
        grouping,
    )


def test_numeric_lexeme_rejects_date_and_version_shapes() -> None:
    assert parse_numeric_lexeme("12.10.23", "de-DE", context="date_candidate") is None
    assert parse_numeric_lexeme("2024.1.2", "en-US", context="version") is None


@pytest.mark.parametrize(
    ("field", "value", "error"),
    [
        ("language", 3, TypeError),
        ("interpretation_mode", "unknown", ValueError),
        ("sequence_fallback_mode", "unknown", ValueError),
        ("disabled_domains", ("unknown",), ValueError),
        ("allowed_domains", ("unknown",), ValueError),
        ("use_spacy", "yes", TypeError),
        ("number_policy", "plain", TypeError),
        ("keep_symbols", 3, TypeError),
        ("expand_numbers", 1, TypeError),
    ],
)
def test_configuration_validation_contract(
    field: str, value: object, error: type[Exception]
) -> None:
    with pytest.raises(error):
        PreparationConfig(**{field: value})


def prepared_signature(result: object) -> tuple[object, ...]:
    return (
        result.spoken_text,
        tuple((stage.name, stage.before, stage.after) for stage in result.stages),
        tuple(result.source_replacements),
        tuple(result.reserved_spans),
        result.warnings,
    )


def test_prepared_text_mapping_and_provenance_contract() -> None:
    result = prepare("Python 3.9.7; ISBN 978-3-16-148410-0", language="en", use_spacy=False)
    assert result.stages[0].name == "structured"
    assert [stage.name for stage in result.stages] == [
        "structured",
        "abbreviations",
        "numbers",
        "whitespace",
    ]
    assert result.source_replacements
    for replacement in result.source_replacements:
        assert result.map_source_span(replacement.source_start, replacement.source_end) == (
            replacement.output_start,
            replacement.output_end,
        )
    assert prepared_signature(result)[0] == (
        "Python three dot nine dot seven; I S B N nine seven eight three one six one four eight four one zero zero"
    )
