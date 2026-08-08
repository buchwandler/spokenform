import json
from pathlib import Path

from abbr2words import iter_unit_matches

from spokenform import NumberPolicy, PreparationConfig, ProtectedSpan, iter_structured_replacements, prepare
from spokenform.config import number_policy_for_language

PARITY_PATH = Path(__file__).parent / "data" / "pt_kokorog2p_parity.json"


def test_portuguese_parity_corpus() -> None:
    for case in json.loads(PARITY_PATH.read_text(encoding="utf-8")):
        result = prepare(case["input"], language="pt", use_spacy=False)
        assert result.spoken_text == case["expected"], case["name"]


def test_portuguese_policy_and_region_preservation() -> None:
    for language in ("pt", "pt-br", "pt-pt"):
        assert number_policy_for_language(language) is NumberPolicy.STRUCTURED_AND_PLAIN
        assert PreparationConfig.for_kokorog2p(language).number_policy is NumberPolicy.STRUCTURED_AND_PLAIN
    assert number_policy_for_language("cs") is NumberPolicy.CALLER_MANAGED
    assert number_policy_for_language("en") is NumberPolicy.CALLER_MANAGED
    assert prepare("16", language="pt-br", use_spacy=False).spoken_text == "dezesseis"
    assert prepare("16", language="pt-pt", use_spacy=False).spoken_text == "dezasseis"
    assert prepare("12,80 EUR", language="pt-br", use_spacy=False).spoken_text.endswith("oitenta centavos")
    assert prepare("12,80 EUR", language="pt-pt", use_spacy=False).spoken_text.endswith("oitenta cêntimos")


def test_portuguese_complete_canonical_quantity_inventory_and_agreement() -> None:
    cases = {
        "1 s": "um segundo",
        "2 min": "dois minutos",
        "1 h": "uma hora",
        "2 d": "dois dias",
        "2 mm": "dois milímetros",
        "2 cm": "dois centímetros",
        "1 m": "um metro",
        "2 km": "dois quilômetros",
        "2 ml": "dois mililitros",
        "1 l": "um litro",
        "2 µg": "dois microgramas",
        "2 mg": "dois miligramas",
        "2 g": "dois gramas",
        "1 kg": "um quilograma",
        "2 t": "duas toneladas",
        "2 K": "dois kelvin",
        "1 m²": "um metro quadrado",
        "2 cm²": "dois centímetros quadrados",
        "2 km²": "dois quilômetros quadrados",
        "2 ha": "dois hectares",
        "2 mm³": "dois milímetros cúbicos",
        "2 cm³": "dois centímetros cúbicos",
        "2 m³": "dois metros cúbicos",
        "2 m/s": "dois metros por segundo",
        "2 km/h": "dois quilômetros por hora",
    }
    for source, expected in cases.items():
        assert prepare(source, language="pt-br", use_spacy=False).spoken_text == expected
        matches = list(iter_unit_matches(source, "pt"))
        assert len(matches) == 1 and matches[0].canonical_id


def test_portuguese_gender_agreement_covers_compound_cardinals() -> None:
    assert prepare("21 h e 202 h", language="pt-br", use_spacy=False).spoken_text == (
        "vinte e uma horas e duzentas e duas horas"
    )


def test_portuguese_decimal_precision_dates_and_caller_managed_times() -> None:
    assert prepare("12,80", language="pt-br", use_spacy=False).spoken_text == "doze vírgula oito zero"
    assert prepare(",02", language="pt-br", use_spacy=False).spoken_text == "zero vírgula zero dois"
    assert prepare("−1,05", language="pt-br", use_spacy=False).spoken_text == "menos um vírgula zero cinco"
    expected_date = "catorze de maio de dois mil e vinte e seis"
    for source in ("14.05.2026", "14/05/2026", "2026-05-14"):
        assert prepare(source, language="pt-br", use_spacy=False).spoken_text == expected_date
    for source in ("31.02.2026", "2026-02-31", "18:20", "25:70"):
        assert prepare(source, language="pt-br", use_spacy=False).spoken_text == source


def test_portuguese_currency_is_deterministic_and_source_aligned() -> None:
    for source, expected in {
        "5€": "cinco euros",
        "12,80 EUR": "doze euros e oitenta centavos",
        "$1": "um dólar",
        "2 USD": "dois dólares",
        "£1": "uma libra esterlina",
        "R$ 1": "um real",
        "R$ 12,80": "doze reais e oitenta centavos",
        "12,80 BRL": "doze reais e oitenta centavos",
    }.items():
        result = prepare(source, language="pt-br", use_spacy=False)
        assert result.spoken_text == expected
        structured = [item for item in result.source_replacements if item.language == "pt"]
        assert [(item.source, item.replacement) for item in structured] == [(source, expected)]


def test_portuguese_dotted_duration_preserves_sentence_boundary() -> None:
    assert prepare("2 min. depois", language="pt-br", use_spacy=False).spoken_text == "dois minutos depois"
    assert prepare("2 min.", language="pt-br", use_spacy=False).spoken_text == "dois minutos."


def test_portuguese_structured_replacements_are_exact_sorted_and_non_overlapping() -> None:
    source = "Em 14.05.2026, há 1,5 kg e 1,5 kg; custa R$ 12,80."
    replacements = iter_structured_replacements(source, language="pt-br")
    assert list(replacements) == sorted(replacements, key=lambda item: (item.start, item.end))
    assert all(left.end <= right.start for left, right in zip(replacements, replacements[1:], strict=False))
    assert [(item.start, item.end, source[item.start : item.end]) for item in replacements] == [
        (3, 13, "14.05.2026"),
        (18, 24, "1,5 kg"),
        (27, 33, "1,5 kg"),
        (41, 49, "R$ 12,80"),
    ]
    assert all(item.language == "pt" and item.rule.startswith("pt.") for item in replacements)


def test_portuguese_protection_is_fail_closed_and_keeps_adjacent_quantity() -> None:
    source = "URL https://example.org/2kg email dev2@example.org v1.2.3 2 kg e 3 kg"
    partial = source.index("2 kg") + 2
    result = prepare(source, language="pt-br", use_spacy=False, protected_spans=[(partial, partial + 2)])
    assert result.spoken_text == (
        "URL https://example.org/2kg email dev2@example.org v1.2.3 2 kg e três quilogramas"
    )


def test_portuguese_explicit_protected_override_preserves_source_coordinates() -> None:
    source = "Override 2 kg; normaliza 3 kg."
    start = source.index("2 kg")
    result = prepare(
        source,
        language="pt-br",
        use_spacy=False,
        protected_spans=[ProtectedSpan(start, start + len("2 kg"), kind="g2p-override")],
    )
    assert result.spoken_text == "Override 2 kg; normaliza três quilogramas."
    output_start, output_end = result.map_source_span(start, start + len("2 kg"))
    assert result.spoken_text[output_start:output_end] == "2 kg"
    assert result.protected_spans[0].kind == "g2p-override"


def test_portuguese_repeated_fragments_and_nbsp_offsets_keep_provenance() -> None:
    source = "2 kg e 2 kg"
    result = prepare(source, language="pt-br", use_spacy=False)
    structured = [item for item in result.source_replacements if item.language == "pt"]
    assert [(item.source, item.replacement) for item in structured] == [
        ("2 kg", "dois quilogramas"),
        ("2 kg", "dois quilogramas"),
    ]
    for item in structured:
        assert source[item.source_start : item.source_end] == item.source
        assert result.spoken_text[item.output_start : item.output_end] == item.replacement
    for whitespace in ("\u00a0", "\u202f"):
        nbsp_source = f"2{whitespace}kg"
        nbsp_result = prepare(nbsp_source, language="pt-br", use_spacy=False)
        assert nbsp_result.spoken_text == "dois quilogramas"
        assert nbsp_result.source_replacements[0].source == nbsp_source


def test_portuguese_plain_pass_protects_literals_and_structured_candidates() -> None:
    source = "https://example.org/2 email dev2@example.org v1.2.3 31.02.2026 2026-02-31 25:70 18:20 12"
    assert prepare(source, language="pt-br", use_spacy=False).spoken_text == (
        "https://example.org/2 email dev2@example.org v1.2.3 31.02.2026 2026-02-31 25:70 18:20 doze"
    )
