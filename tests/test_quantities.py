from spokenform import prepare


def test_percentage_and_compound_units_are_claimed_as_whole_spans() -> None:
    assert prepare("2,75%", language="de", use_spacy=False).spoken_text == (
        "zwei Komma sieben fünf Prozent"
    )
    assert prepare("2,75%", language="es_MX", use_spacy=False).spoken_text == (
        "dos punto setenta y cinco por ciento"
    )
    assert prepare("2 g/cm³", language="en", use_spacy=False).spoken_text == (
        "two grams per cubic centimeter"
    )
    assert prepare("2 mol/l", language="de", use_spacy=False).spoken_text == (
        "zwei Mol pro Liter"
    )
    assert prepare("6 L/100km", language="en", use_spacy=False).spoken_text == (
        "six liters per one hundred kilometers"
    )


def test_currency_symbols_use_guarded_locale_decimal_heuristics() -> None:
    assert prepare("$25.50", language="it", use_spacy=False).spoken_text == (
        "venticinque dollari e cinquanta centesimi"
    )
    assert prepare("150€", language="de", use_spacy=False).spoken_text == (
        "einhundertfünfzig Euro"
    )
    assert prepare("$1.5 million", language="en", use_spacy=False).spoken_text == (
        "one point five million dollars"
    )
