from spokenform import prepare
from spokenform.dates import DateCandidate


def test_german_date_grammar_covers_short_text_hyphenated_and_ranges() -> None:
    cases = {
        "12.10.23": "zwölfte zehnten dreiundzwanzig",
        "5. Nov. 1990": "fünfter November neunzehnhundertneunzig",
        "15-Jan-2023": "fünfzehnter Januar zweitausenddreiundzwanzig",
        "31. Dez. 2025": "einunddreißigster Dezember zweitausendfünfundzwanzig",
        "’23": "dreiundzwanzig",
        "30.06.": "dreißigster sechster.",
        "10.-12. Mai": "zehnter bis zwölfter Mai",
    }
    for source, expected in cases.items():
        assert prepare(source, language="de", use_spacy=False).spoken_text == expected


def test_english_us_dates_cover_numeric_text_and_ranges() -> None:
    assert prepare("12/31/23", language="en_US", use_spacy=False).spoken_text == (
        "December thirty first twenty three"
    )
    assert prepare("January 5th, 2023", language="en_US", use_spacy=False).spoken_text == (
        "January fifth twenty twenty three"
    )
    assert prepare("Jan 5-7, 2023", language="en_US", use_spacy=False).spoken_text == (
        "January fifth through seventh twenty twenty three"
    )


def test_romance_locales_cover_short_and_text_month_dates() -> None:
    assert prepare("12/10/23", language="es_MX", use_spacy=False).spoken_text == (
        "doce de octubre de dos mil veintitrés"
    )
    assert prepare("5 nov. 1990", language="fr", use_spacy=False).spoken_text == (
        "cinq novembre mille neuf cent quatre-vingt-dix"
    )
    assert prepare("5 nov 1990", language="it", use_spacy=False).spoken_text == (
        "cinque novembre millenovecentonovanta"
    )


def test_date_candidates_retain_source_shape_and_locale_extensions() -> None:
    candidate = DateCandidate(
        day=12,
        month=10,
        year=2023,
        year_digits=4,
        month_style="numeric",
        source_order="dmy",
        separator=".",
    )
    assert candidate.month_style == "numeric"
    assert candidate.source_order == "dmy"
    assert candidate.separator == "."
    assert candidate.range_role == "single"
    assert prepare("Oct 12", language="en_US", use_spacy=False).spoken_text == ("October twelfth")
    assert prepare("Oct 12, 2023", language="en_US", use_spacy=False).spoken_text == (
        "October twelfth twenty twenty three"
    )
    assert prepare("12-10-2023", language="es_MX", use_spacy=False).spoken_text == (
        "doce de octubre de dos mil veintitrés"
    )
    assert prepare("12 de octubre de 2023", language="es_MX", use_spacy=False).spoken_text == (
        "doce de octubre de dos mil veintitrés"
    )
    assert prepare("12-10-2023", language="fr", use_spacy=False).spoken_text == (
        "douze octobre deux mille vingt-trois"
    )
    assert prepare("12-10-2023", language="it", use_spacy=False).spoken_text == (
        "dodici ottobre duemilaventitre"
    )


def test_dotted_short_dates_are_not_auto_protected_as_versions() -> None:
    assert prepare("12.10.23", language="fr", use_spacy=False).spoken_text == (
        "douze octobre deux mille vingt-trois"
    )


def test_iso_slash_dates_beat_fraction_and_phone_candidates() -> None:
    result = prepare("2025/03/15", language="en", use_spacy=False)
    assert result.spoken_text == "March fifteenth twenty twenty five"
    assert any(item.rule == "en.date" for item in result.source_replacements)


def test_benchmark_date_shapes_and_no_year_dates_use_date_rules() -> None:
    cases = {
        ("11/30", "en_US"): "November thirtieth",
        ("06/10", "en_US"): "June tenth",
        ("3rd July 1995", "en_US"): "the third of July nineteen ninety five",
        ("31 Jan 2025", "en_US"): "the thirty first of January twenty twenty five",
        ("09/01/24", "en_US"): "September first twenty four",
        ("le 30/06", "fr_FR"): "le trente juin",
        ("il 31/12", "it_IT"): "il trentuno dicembre",
        ("31/01", "es_MX"): "treinta y uno de enero",
        ("04/07", "es_MX"): "cuatro de julio",
    }
    for (source, language), expected in cases.items():
        result = prepare(source, language=language, use_spacy=False)
        assert result.spoken_text == expected, (source, language)
        assert any("date" in item.rule for item in result.source_replacements)
