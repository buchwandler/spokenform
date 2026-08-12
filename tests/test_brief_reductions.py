from spokenform import prepare


def test_postal_recognizer_does_not_steal_measurements_or_counts() -> None:
    for source, expected in (
        ("1500 Tonnen", "eintausendfünfhundert Tonnen"),
        ("2024 Punkte", "zweitausendvierundzwanzig Punkte"),
        ("4711 Teilnehmer", "viertausendsiebenhundertelf Teilnehmer"),
    ):
        assert prepare(source, language="de", use_spacy=False).spoken_text == expected

    assert prepare("10115 Berlin", language="de", use_spacy=False).spoken_text == (
        "eins null eins eins fünf Berlin"
    )


def test_legal_and_product_claims_require_typed_evidence() -> None:
    assert prepare("Siehe § 3 BGB.", language="de", use_spacy=False).spoken_text == (
        "Siehe Paragraf drei B G B."
    )
    assert prepare("Nach Berlin fahren.", language="de", use_spacy=False).spoken_text == (
        "Nach Berlin fahren."
    )
    assert prepare("model number is unknown", language="en", use_spacy=False).spoken_text == (
        "model number is unknown"
    )
    assert prepare("Model X7", language="en", use_spacy=False).spoken_text == "model X seven"


def test_locale_numeric_policies_are_selected_before_separator_heuristics() -> None:
    assert prepare("42,195 km", language="de_DE", use_spacy=False).spoken_text == (
        "zweiundvierzig Komma eins neun fünf Kilometer"
    )
    assert prepare("3,000", language="es_MX", use_spacy=False).spoken_text == "tres mil"
    assert (
        prepare("45,000", language="es_MX", use_spacy=False).spoken_text == "cuarenta y cinco mil"
    )
    assert (
        prepare("1.75", language="es_MX", use_spacy=False).spoken_text
        == "uno punto setenta y cinco"
    )


def test_typed_and_contextual_renderers_do_not_use_global_code_rules() -> None:
    assert prepare("ISBN 978-3-16-148410-0", language="en", use_spacy=False).spoken_text.startswith(
        "I S B N nine seven eight"
    )
    assert prepare("Chapter IIX", language="en", use_spacy=False).spoken_text == "Chapter IIX"
    assert (
        prepare("Heinrich VIII.", language="de", use_spacy=False).spoken_text
        == "Heinrich der Achte."
    )
    assert prepare("√9 = 3", language="es", use_spacy=False).spoken_text == (
        "raíz cuadrada de nueve igual a tres"
    )
    assert prepare("E. coli strain K-12", language="en", use_spacy=False).spoken_text == (
        "e coli strain K twelve"
    )


def test_typed_locale_numeric_cleanup_is_contextual() -> None:
    assert prepare("1,80 m", language="de", use_spacy=False).spoken_text == ("ein Meter achtzig")
    assert prepare("Código postal 03900", language="es", use_spacy=False).spoken_text == (
        "Código postal cero tres nueve cero cero"
    )
    assert prepare("16.00%", language="es", use_spacy=False).spoken_text == ("dieciséis por ciento")
    assert prepare("15ª", language="it", use_spacy=False).spoken_text == "quindicesima"
