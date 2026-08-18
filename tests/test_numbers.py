import pytest

from spokenform import normalize_numbers, prepare
from spokenform.numbers import normalize_plain_numbers
from spokenform.numeric_lexeme import parse_numeric_lexeme


def test_german_decimal_and_unit_ready_text() -> None:
    assert normalize_numbers("1,5 Kilogramm", language="de") == "eins Komma fünf Kilogramm"


def test_english_direct_number_api_preserves_explicit_decimal_precision() -> None:
    assert normalize_numbers("2.0", language="en") == "two point zero"
    assert normalize_numbers(".02", language="en") == "point zero two"


def test_english_leading_decimal_in_sentence() -> None:
    result = prepare(
        "He hesitated for .02 seconds.",
        language="en",
        use_spacy=False,
    )
    assert result.spoken_text == "He hesitated for point zero two seconds."
    assert not any(
        item.rule
        in {
            "sequence.version",
            "sequence.time",
            "sequence.duration",
            "sequence.sports",
            "sequence.chained-score",
        }
        for item in result.source_replacements
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        (".3", "point three"),
        (".02", "point zero two"),
        ("-.3", "minus point three"),
        ("+.3", "plus point three"),
        ("0.3", "zero point three"),
        ("0.02", "zero point zero two"),
    ),
)
def test_english_leading_decimal_contract(source: str, expected: str) -> None:
    assert normalize_plain_numbers(source, language="en") == expected


def test_english_leading_decimal_parser_invariant() -> None:
    lexeme = parse_numeric_lexeme(".3", "en", context="plain")

    assert lexeme is not None
    assert lexeme.integer_digits == "0"
    assert lexeme.fraction_digits == "3"
    assert lexeme.decimal_separator == "."


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        (
            "It took nearly .3 seconds.",
            "It took nearly point three seconds.",
        ),
        (
            "After .02 seconds",
            "After point zero two seconds",
        ),
    ),
)
def test_english_leading_decimals_in_prose(source: str, expected: str) -> None:
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == expected
    decimal_source = ".3" if ".3" in source else ".02"
    decimal_replacements = [
        item for item in result.source_replacements if item.source == decimal_source
    ]
    assert len(decimal_replacements) == 1
    assert decimal_replacements[0].stages == ("numbers",)
    assert decimal_replacements[0].rule is None
    assert not any(
        item.rule
        in {
            "sequence.version",
            "sequence.time",
            "sequence.duration",
            "sequence.sports",
            "sequence.chained-score",
        }
        for item in result.source_replacements
    )


@pytest.mark.parametrize("punctuation", [".", ",", "!", "?"])
def test_english_plain_decimal_allows_terminal_punctuation(punctuation: str) -> None:
    result = prepare(f"The value is 2.0{punctuation}", language="en", use_spacy=False)
    assert result.spoken_text == f"The value is two point zero{punctuation}"


@pytest.mark.parametrize(
    ("source", "language", "expected"),
    (
        ("He is 2.", "en", "He is two."),
        ("He is 7!", "en", "He is seven!"),
        ("He is 3?", "en", "He is three?"),
        ("He is 12.", "en", "He is twelve."),
        ("Value: 2.", "en", "Value: two."),
        ("Tiene 2.", "es", "Tiene dos."),
    ),
)
def test_terminal_cardinals_preserve_sentence_punctuation(
    source: str, language: str, expected: str
) -> None:
    assert prepare(source, language=language, use_spacy=False).spoken_text == expected


def test_terminal_cardinals_normalize_in_multi_sentence_prose() -> None:
    result = prepare("First sentence. He is 2. Next sentence.", language="en", use_spacy=False)

    assert result.spoken_text == "First sentence. He is two. Next sentence."


def test_terminal_cardinals_respect_explicit_protected_spans() -> None:
    source = "Value: 2."
    start = source.index("2")
    result = prepare(
        source,
        language="en",
        use_spacy=False,
        protected_spans=[(start, start + 1)],
    )

    assert result.spoken_text == source


def test_urls_emails_and_versions_are_protected() -> None:
    source = "Version v1.2.3: https://example.org/a2 and dev2@example.org have 2 tests."
    result = normalize_numbers(source, language="en")
    assert "v1.2.3" in result
    assert "https://example.org/a2" in result
    assert "dev2@example.org" in result
    assert "two tests" in result


def test_iso_date() -> None:
    result = normalize_numbers("2026-05-14", language="en")
    assert result == "May fourteenth, two thousand and twenty-six"


def test_currency_prefix_and_suffix() -> None:
    assert "Euro" in normalize_numbers("€12,80", language="de")
    assert "Euro" in normalize_numbers("12,80 EUR", language="de")


def test_bare_dotted_version_is_not_verbalized() -> None:
    assert normalize_numbers("Version 1.2.3", language="en") == "Version 1.2.3"


@pytest.mark.parametrize("source", ["1.2.3", "1.02.3", "v1.2.3"])
def test_multi_dot_versions_are_not_partially_normalized(source: str) -> None:
    assert normalize_numbers(source, language="en") == source


def test_french_decimal_digits_keep_fractional_zero() -> None:
    assert normalize_numbers("0,02", language="fr") == "zéro virgule zéro deux"


def test_spanish_and_italian_dot_decimals_use_fractional_digit_policy() -> None:
    assert normalize_numbers("1.5", language="es") == "Uno coma cinco"
    assert normalize_numbers("1.5", language="it") == "uno virgola cinque"
