from spokenform import prepare
from spokenform.numeric_lexeme import (
    NumericLexeme,
    fraction_digit_groups,
    numeric_speech_policy,
    parse_numeric_lexeme,
)


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


def test_spanish_currency_accepts_comma_grouping_without_reclassifying_decimals() -> None:
    grouped = parse_numeric_lexeme("1,250,000", "es", context="currency")
    short_grouped = parse_numeric_lexeme("1,250", "es", context="currency")
    decimal = parse_numeric_lexeme("1,25", "es", context="currency")

    assert grouped is not None and grouped.integer_digits == "1250000"
    assert grouped.fraction_digits is None
    assert short_grouped is not None and short_grouped.integer_digits == "1250"
    assert short_grouped.fraction_digits is None
    assert decimal is not None and decimal.integer_digits == "1"
    assert decimal.fraction_digits == "25"


def test_spanish_math_accepts_long_dot_decimal_fraction() -> None:
    lexeme = parse_numeric_lexeme("3.1416", "es", context="math")

    assert lexeme is not None
    assert lexeme.integer_digits == "3"
    assert lexeme.fraction_digits == "1416"


def test_numeric_lexeme_fails_closed_for_date_and_version_candidates() -> None:
    assert parse_numeric_lexeme("12.10.23", "de-DE", context="date_candidate") is None
    assert parse_numeric_lexeme("2024.1.2", "en-US", context="version") is None


def test_cross_locale_quantity_regressions_are_not_grouped_integers() -> None:
    assert prepare("5.5 kg", language="es-MX", use_spacy=False).spoken_text == (
        "Cinco punto cinco kilogramos"
    )
    assert prepare("23.7°C", language="es-MX", use_spacy=False).spoken_text == (
        "Veintitrés punto siete grados Celsius"
    )
    assert prepare("36.5°C", language="it-IT", use_spacy=False).spoken_text == (
        "trentasei virgola cinque gradi Celsius"
    )
    assert prepare("2.75 kg", language="it-IT", use_spacy=False).spoken_text == (
        "due virgola settantacinque chilogrammi"
    )


def test_numeric_speech_policy_is_locale_specific_and_immutable() -> None:
    assert numeric_speech_policy("es-MX").decimal_word == "punto"
    assert numeric_speech_policy("es").decimal_word == "coma"
    assert numeric_speech_policy("en-US").omit_cardinal_conjunction is True
    assert numeric_speech_policy("fr-FR").fraction_mode == "two_digit_cardinal"
    assert fraction_digit_groups("75", "fr-FR") == ("75",)
    assert fraction_digit_groups("09", "fr-FR") == ("0", "9")


def test_plain_decimal_rendering_is_digitwise_without_changing_quantity_policy() -> None:
    assert prepare("9.58", language="es-MX", use_spacy=False).spoken_text == (
        "Nueve punto cinco ocho"
    )
    assert prepare("9.58 segundos", language="es-MX", use_spacy=False).spoken_text == (
        "Nueve punto cinco ocho segundos"
    )
    assert prepare("2.75 kg", language="it-IT", use_spacy=False).spoken_text == (
        "due virgola settantacinque chilogrammi"
    )
