import json
from pathlib import Path

from abbr2words import iter_unit_matches

from spokenform import PreparationConfig, ProtectedSpan, iter_structured_replacements, prepare

PARITY_PATH = Path(__file__).parent / "data" / "es_kokorog2p_parity.json"


def test_spanish_parity_corpus() -> None:
    for case in json.loads(PARITY_PATH.read_text(encoding="utf-8")):
        result = prepare(case["input"], language="es", use_spacy=False)
        assert result.spoken_text == case["expected"], case["name"]


def test_spanish_quantity_grammar_uses_canonical_abbr2words_ids() -> None:
    cases = {
        "1 kg": "Un kilogramo",
        "2 kg": "Dos kilogramos",
        "1,5 kg": "Uno coma cinco kilogramos",
        "1 h": "Una hora",
        "2 h": "Dos horas",
        "1 min.": "Un minuto.",
        "2 min.": "Dos minutos.",
        "1 °C": "Un grado Celsius",
        "-1°C": "Menos un grado Celsius",
        "25 °C": "Veinticinco grados Celsius",
    }
    for source, expected in cases.items():
        assert prepare(source, language="es", use_spacy=False).spoken_text == expected
        matches = list(iter_unit_matches(source, "es"))
        assert matches and matches[0].canonical_id


def test_spanish_currency_prefix_suffix_and_fraction_precision() -> None:
    assert prepare("12,80 EUR", language="es", use_spacy=False).spoken_text == (
        "Doce euros con ochenta céntimos"
    )
    assert prepare("€12,80", language="es", use_spacy=False).spoken_text == (
        "Doce euros con ochenta céntimos"
    )
    assert prepare("1,01 EUR", language="es", use_spacy=False).spoken_text == (
        "Un euro con un céntimo"
    )
    assert prepare("10 USD y 5 GBP", language="es", use_spacy=False).spoken_text == (
        "Diez dólares y cinco libras esterlinas"
    )


def test_spanish_structured_replacements_are_exact_and_non_overlapping() -> None:
    source = "El 14.05.2026 necesita 1,5 kg y 1,5 kg; cuesta 12,80 EUR."
    replacements = iter_structured_replacements(source, language="es")
    assert list(replacements) == sorted(replacements, key=lambda item: (item.start, item.end))
    assert all(
        left.end <= right.start for left, right in zip(replacements, replacements[1:], strict=False)
    )
    assert [(item.start, item.end, source[item.start : item.end]) for item in replacements] == [
        (3, 13, "14.05.2026"),
        (23, 29, "1,5 kg"),
        (32, 38, "1,5 kg"),
        (47, 56, "12,80 EUR"),
    ]
    assert all(item.language == "es" and item.rule.startswith("es.") for item in replacements)


def test_spanish_protection_is_fail_closed_and_keeps_adjacent_quantity() -> None:
    source = "URL https://example.org/2kg email dev2@example.org v1.2.3 2 kg y 3 kg"
    partial = source.index("2 kg") + 2
    result = prepare(
        source,
        language="es",
        use_spacy=False,
        protected_spans=[(partial, partial + 2)],
    )
    assert result.spoken_text == (
        "URL https://example.org/2kg email dev2@example.org v1.2.3 2 kg y tres kilogramos"
    )
    assert "https://example.org/2kg" in result.spoken_text
    assert "dev2@example.org" in result.spoken_text
    assert "v1.2.3" in result.spoken_text


def test_spanish_explicit_protected_override_preserves_coordinates() -> None:
    source = "Override 2 kg; normaliza 3 kg."
    start = source.index("2 kg")
    result = prepare(
        source,
        language="es",
        use_spacy=False,
        protected_spans=[ProtectedSpan(start, start + len("2 kg"), kind="g2p-override")],
    )
    assert result.spoken_text == "Override 2 kg; normaliza tres kilogramos."
    assert result.protected_spans[0].kind == "g2p-override"
    output_start, output_end = result.map_source_span(start, start + len("2 kg"))
    assert result.spoken_text[output_start:output_end] == "2 kg"


def test_spanish_repeated_fragments_and_source_replacements() -> None:
    source = "2 kg y 2 kg"
    result = prepare(source, language="es", use_spacy=False)
    structured = [item for item in result.source_replacements if item.language == "es"]
    assert [(item.source, item.replacement) for item in structured] == [
        ("2 kg", "Dos kilogramos"),
        ("2 kg", "dos kilogramos"),
    ]
    for item in structured:
        assert source[item.source_start : item.source_end] == item.source
        assert result.spoken_text[item.output_start : item.output_end] == item.replacement


def test_spanish_profile_promotes_number_policy_without_time_ownership() -> None:
    config = PreparationConfig.for_kokorog2p("es")
    assert config.number_policy.value == "structured_and_plain"
    assert prepare("18:20 y 12", config=config, use_spacy=False).spoken_text == (
        "Dieciocho y veinte y doce"
    )


def test_spanish_times_and_extended_units_use_locale_policies() -> None:
    assert prepare("9:45 AM", language="es_MX", use_spacy=False).spoken_text == (
        "Nueve y cuarenta y cinco de la mañana"
    )
    assert prepare("14:30", language="es_MX", use_spacy=False).spoken_text == ("Catorce y treinta")
    for source in ("60 mph", "100 kPa", "1 atm", "64 GB", "6 L/100km", "10 m³/s"):
        assert prepare(source, language="es_MX", use_spacy=False).spoken_text != source


def test_spanish_generated_numeric_sentence_starts_are_capitalized() -> None:
    cases = (
        ("7 días.", "Siete días."),
        ("42 años.", "Cuarenta y dos años."),
        ("0 personas.", "Cero personas."),
        ("(7 días.)", "(Siete días.)"),
        ("5 + 3 = 8.", "Cinco más tres igual a ocho."),
    )

    for source, expected in cases:
        assert prepare(source, language="es", use_spacy=False).spoken_text == expected


def test_spanish_generated_casing_does_not_recase_untouched_prose() -> None:
    assert prepare("hola 7 días.", language="es", use_spacy=False).spoken_text == "hola siete días."
