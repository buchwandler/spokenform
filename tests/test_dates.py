from spokenform import prepare


def test_german_date_grammar_covers_short_text_hyphenated_and_ranges() -> None:
    cases = {
        "12.10.23": "zwölfte Oktober dreiundzwanzig",
        "5. Nov. 1990": "fünfter November neunzehnhundertneunzig",
        "15-Jan-2023": "fünfzehnter Januar zweitausenddreiundzwanzig",
        "31. Dez. 2025": "einunddreißigste Dezember zweitausendfünfundzwanzig",
        "’23": "zweitausenddreiundzwanzig",
        "30.06.": "dreißigster Juni",
        "10.-12. Mai": "zehnter bis zwölfter Mai",
    }
    for source, expected in cases.items():
        assert prepare(source, language="de", use_spacy=False).spoken_text == expected


def test_english_us_dates_cover_numeric_text_and_ranges() -> None:
    assert prepare("12/31/23", language="en_US", use_spacy=False).spoken_text == (
        "December thirty-first, two thousand and twenty-three"
    )
    assert prepare("January 5th, 2023", language="en_US", use_spacy=False).spoken_text == (
        "January fifth, two thousand and twenty-three"
    )
    assert prepare("Jan 5-7, 2023", language="en_US", use_spacy=False).spoken_text == (
        "January fifth through seventh, two thousand and twenty three"
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
