import json
from pathlib import Path

from abbr2words import iter_unit_matches

from spokenform import PreparationConfig, ProtectedSpan, iter_structured_replacements, prepare

PARITY_PATH = Path(__file__).parent / "data" / "fr_kokorog2p_parity.json"


def test_french_parity_corpus() -> None:
    for case in json.loads(PARITY_PATH.read_text(encoding="utf-8")):
        result = prepare(case["input"], language="fr", use_spacy=False)
        assert result.spoken_text == case["expected"], case["name"]


def test_french_replacements_have_exact_source_and_output_coordinates() -> None:
    source = "Le 14.05.2026: 2 kg, 12,80 EUR et 2 kg."
    result = prepare(source, language="fr", use_spacy=False)
    assert result.source_replacements
    assert list(result.source_replacements) == sorted(result.source_replacements, key=lambda item: (item.source_start, item.output_start))
    for replacement in result.source_replacements:
        assert source[replacement.source_start : replacement.source_end] == replacement.source
        assert result.spoken_text[replacement.output_start : replacement.output_end] == replacement.replacement
        assert replacement.kind in {"structured", "abbreviation"}
        if replacement.language == "fr":
            assert replacement.rule.startswith("fr.")


def test_french_structured_replacements_preserve_repeated_source_spans() -> None:
    replacements = iter_structured_replacements("2 kg puis 2 kg", language="fr")
    assert [(item.start, item.end, item.text, item.language, item.rule) for item in replacements] == [
        (0, 4, "deux kilogrammes", "fr", "fr.quantity"),
        (10, 14, "deux kilogrammes", "fr", "fr.quantity"),
    ]


def test_french_canonical_inventory_covers_base_and_extended_units() -> None:
    cases = {
        "1 h": "une heure", "2 min": "deux minutes", "2 sec": "deux secondes",
        "1 kg": "un kilogramme", "2 l": "deux litres", "2 m": "deux mètres",
        "2 km/h": "deux kilomètres par heure", "2 m²": "deux mètres carrés", "2 m³": "deux mètres cubes",
    }
    for source, expected in cases.items():
        assert prepare(source, language="fr", use_spacy=False).spoken_text == expected
        assert list(iter_unit_matches(source, "fr"))[0].canonical_id


def test_french_dotted_duration_consumes_period_only_when_sentence_final() -> None:
    assert prepare("45 min. puis 30 sec.", language="fr", use_spacy=False).spoken_text == "quarante-cinq minutes puis trente secondes."
    assert prepare("45 min. Puis", language="fr", use_spacy=False).spoken_text == "quarante-cinq minutes Puis"


def test_french_protection_is_fail_closed_for_partial_quantity_and_literals() -> None:
    source = "URL https://example.org/2kg email dev2@example.org v1.2.3 2 kg et 3 kg"
    partial = source.index("2 kg") + 2
    result = prepare(source, language="fr", use_spacy=False, protected_spans=[(partial, partial + 2)])
    assert result.spoken_text == "URL https://example.org/2kg email dev2@example.org v1.2.3 2 kg et trois kilogrammes"
    assert "https://example.org/2kg" in result.spoken_text
    assert "dev2@example.org" in result.spoken_text
    assert "v1.2.3" in result.spoken_text


def test_french_explicit_protected_override_keeps_adjacent_quantity() -> None:
    source = "Override 2 kg; normalise 3 kg."
    start = source.index("2 kg")
    result = prepare(source, language="fr", use_spacy=False, protected_spans=[ProtectedSpan(start, start + len("2 kg"), kind="g2p-override")])
    assert result.spoken_text == "Override 2 kg; normalise trois kilogrammes."
    assert result.protected_spans[0].kind == "g2p-override"
    output_start, output_end = result.map_source_span(start, start + len("2 kg"))
    assert result.spoken_text[output_start:output_end] == "2 kg"


def test_french_nbsp_and_narrow_nbsp_units_keep_exact_source_slices() -> None:
    source = "2\u00a0kg et 3\u202fkg"
    result = prepare(source, language="fr", use_spacy=False)
    assert result.spoken_text == "deux kilogrammes et trois kilogrammes"
    assert [item.source for item in result.source_replacements] == ["2\u00a0kg", "3\u202fkg"]


def test_french_ordinal_suffixes_do_not_corrupt_numbers_or_dates() -> None:
    result = prepare("1er 1ère 1re 2e 2ème 2nd 2nde 3e 21e 14.05.2026", language="fr", use_spacy=False)
    assert result.spoken_text == "premier première première deuxième deuxième second seconde troisième vingt et unième quatorze mai deux mille vingt-six"


def test_french_profile_promotes_number_policy() -> None:
    assert PreparationConfig.for_kokorog2p("fr").number_policy.value == "structured_and_plain"
