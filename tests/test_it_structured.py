import json
from pathlib import Path

from abbr2words import iter_unit_matches

from spokenform import PreparationConfig, ProtectedSpan, iter_structured_replacements, prepare

PARITY_PATH = Path(__file__).parent / "data" / "it_kokorog2p_parity.json"


def test_italian_parity_corpus() -> None:
    for case in json.loads(PARITY_PATH.read_text(encoding="utf-8")):
        result = prepare(case["input"], language="it", use_spacy=False)
        assert result.spoken_text == case["expected"], case["name"]


def test_italian_canonical_quantity_inventory_and_agreement() -> None:
    cases = {
        "1 s": "un secondo",
        "2 min": "due minuti",
        "1 h": "un'ora",
        "2 d": "due giorni",
        "2 mm": "due millimetri",
        "2 cm": "due centimetri",
        "1 m": "un metro",
        "2 km": "due chilometri",
        "2 ml": "due millilitri",
        "1 l": "un litro",
        "2 µg": "due microgrammi",
        "2 mg": "due milligrammi",
        "2 g": "due grammi",
        "1 kg": "un chilogrammo",
        "1 t": "una tonnellata",
        "2 K": "due kelvin",
        "1 m²": "un metro quadrato",
        "2 ha": "due ettari",
        "1 m³": "un metro cubo",
        "2 m/s": "due metri al secondo",
        "2 km/h": "due chilometri all'ora",
    }
    for source, expected in cases.items():
        assert prepare(source, language="it", use_spacy=False).spoken_text == expected
        matches = list(iter_unit_matches(source, "it"))
        assert len(matches) == 1
        assert matches[0].canonical_id


def test_italian_temperatures_and_currency_are_deterministic() -> None:
    assert prepare("1 °F e 25 °C", language="it", use_spacy=False).spoken_text == (
        "un grado Fahrenheit e venticinque gradi Celsius"
    )
    assert prepare("12,80 EUR e €12,80", language="it", use_spacy=False).spoken_text == (
        "dodici euro e ottanta centesimi e dodici euro e ottanta centesimi"
    )
    assert prepare("$10 e £5", language="it", use_spacy=False).spoken_text == (
        "dieci dollari e cinque sterline"
    )


def test_italian_structured_replacements_are_exact_sorted_and_non_overlapping() -> None:
    source = "Il 14.05.2026 necessita 1,5 kg e 1,5 kg; costa 12,80 EUR."
    replacements = iter_structured_replacements(source, language="it")
    assert list(replacements) == sorted(replacements, key=lambda item: (item.start, item.end))
    assert all(
        left.end <= right.start for left, right in zip(replacements, replacements[1:], strict=False)
    )
    assert [(item.start, item.end, source[item.start : item.end]) for item in replacements] == [
        (3, 13, "14.05.2026"),
        (24, 30, "1,5 kg"),
        (33, 39, "1,5 kg"),
        (47, 56, "12,80 EUR"),
    ]
    assert all(item.language == "it" and item.rule.startswith("it.") for item in replacements)


def test_italian_protection_is_fail_closed_for_literals_and_partial_quantity() -> None:
    source = "URL https://example.org/2kg email dev2@example.org v1.2.3 2 kg e 3 kg"
    partial = source.index("2 kg") + 2
    result = prepare(
        source,
        language="it",
        use_spacy=False,
        protected_spans=[(partial, partial + 2)],
    )
    assert result.spoken_text == (
        "U R L https://example.org/2kg email dev2@example.org v1.2.3 2 kg e tre chilogrammi"
    )


def test_italian_explicit_protected_override_preserves_coordinates() -> None:
    source = "Override 2 kg; normalizza 3 kg."
    start = source.index("2 kg")
    result = prepare(
        source,
        language="it",
        use_spacy=False,
        protected_spans=[ProtectedSpan(start, start + len("2 kg"), kind="g2p-override")],
    )
    assert result.spoken_text == "Override 2 kg; normalizza tre chilogrammi."
    assert result.protected_spans[0].kind == "g2p-override"
    output_start, output_end = result.map_source_span(start, start + len("2 kg"))
    assert result.spoken_text[output_start:output_end] == "2 kg"


def test_italian_repeated_identical_fragments_keep_distinct_source_replacements() -> None:
    source = "2 kg e 2 kg"
    result = prepare(source, language="it", use_spacy=False)
    structured = [item for item in result.source_replacements if item.language == "it"]
    assert [(item.source, item.replacement) for item in structured] == [
        ("2 kg", "due chilogrammi"),
        ("2 kg", "due chilogrammi"),
    ]
    for item in structured:
        assert source[item.source_start : item.source_end] == item.source
        assert result.spoken_text[item.output_start : item.output_end] == item.replacement


def test_italian_profile_promotes_numbers_but_keeps_colon_times_caller_managed() -> None:
    config = PreparationConfig.for_kokorog2p("it")
    assert config.number_policy.value == "structured_and_plain"
    assert prepare("18:20 e 12", config=config, use_spacy=False).spoken_text == (
        "diciotto e venti e dodici"
    )
    assert prepare("Ci vediamo alle 18:20.", language="it", use_spacy=False).spoken_text == (
        "Ci vediamo alle diciotto e venti."
    )


def test_italian_times_and_extended_units_use_locale_policies() -> None:
    assert prepare("14:30", language="it_IT", use_spacy=False).spoken_text == (
        "quattordici e trenta"
    )
    assert prepare("9:15", language="it_IT", use_spacy=False).spoken_text == ("nove e quindici")
    for source in ("60 mph", "100 kPa", "1 atm", "64 GB", "6 L/100km", "10 m³/s"):
        assert prepare(source, language="it_IT", use_spacy=False).spoken_text != source


def test_italian_plain_pass_protects_invalid_and_iso_date_candidates() -> None:
    source = "31.02.2026 2026-02-31 25:70 https://example.org/2 v1.2.3"
    assert prepare(source, language="it", use_spacy=False).spoken_text == source


def test_spanish_parity_corpus_still_passes_after_shared_plain_refactor() -> None:
    spanish_path = Path(__file__).parent / "data" / "es_kokorog2p_parity.json"
    for case in json.loads(spanish_path.read_text(encoding="utf-8")):
        result = prepare(case["input"], language="es", use_spacy=False)
        assert result.spoken_text == case["expected"], case["name"]
