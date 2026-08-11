from spokenform import prepare
from spokenform.numeric_lexeme import NumericLexeme, parse_numeric_lexeme


def test_numeric_lexeme_preserves_cross_locale_decimal_precision() -> None:
    cases = (
        ("es-MX", "5.5", "5", "5"),
        ("es-MX", "23.7", "23", "7"),
        ("it-IT", "36.5", "36", "5"),
        ("it-IT", "2.75", "2", "75"),
        ("fr-FR", "1,5", "1", "5"),
    )

    for language, raw, integer, fraction in cases:
        lexeme = parse_numeric_lexeme(raw, language, context="quantity")
        assert isinstance(lexeme, NumericLexeme)
        assert lexeme.integer_digits == integer
        assert lexeme.fraction_digits == fraction


def test_numeric_lexeme_distinguishes_grouping_and_mixed_decimal_forms() -> None:
    grouped = parse_numeric_lexeme("3,000", "es-MX", context="quantity")
    german_grouped = parse_numeric_lexeme("1.000.000", "de-DE", context="currency")
    english = parse_numeric_lexeme("1,234.56", "en-US", context="currency")

    assert grouped is not None and grouped.integer_digits == "3000"
    assert grouped.fraction_digits is None
    assert german_grouped is not None and german_grouped.integer_digits == "1000000"
    assert english is not None and english.integer_digits == "1234"
    assert english.fraction_digits == "56"
    assert english.grouping_separators == (",",)


def test_numeric_lexeme_fails_closed_for_date_and_version_candidates() -> None:
    assert parse_numeric_lexeme("12.10.23", "de-DE", context="date_candidate") is None
    assert parse_numeric_lexeme("2024.1.2", "en-US", context="version") is None


def test_cross_locale_quantity_regressions_are_not_grouped_integers() -> None:
    assert prepare("5.5 kg", language="es-MX", use_spacy=False).spoken_text == (
        "cinco coma cinco kilogramos"
    )
    assert prepare("23.7°C", language="es-MX", use_spacy=False).spoken_text == (
        "veintitrés coma siete grados Celsius"
    )
    assert prepare("36.5°C", language="it-IT", use_spacy=False).spoken_text == (
        "trentasei virgola cinque gradi Celsius"
    )
    assert prepare("2.75 kg", language="it-IT", use_spacy=False).spoken_text == (
        "due virgola sette cinque chilogrammi"
    )
