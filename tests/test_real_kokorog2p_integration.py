"""Real downstream contract checks, enabled by the kokorog2p CI job."""

from __future__ import annotations

import pytest

pytest.importorskip("kokorog2p")
from kokorog2p.de.g2p import GermanG2P  # noqa: E402
from kokorog2p.en.g2p import EnglishG2P  # noqa: E402
from kokorog2p.es.g2p import SpanishG2P  # noqa: E402
from kokorog2p.fr.g2p import FrenchG2P  # noqa: E402
from kokorog2p.it import ItalianG2P  # noqa: E402
from kokorog2p.pt.g2p import PortugueseG2P  # noqa: E402

from spokenform import ProtectedSpan, prepare_for_kokorog2p  # noqa: E402


def _real_g2p() -> GermanG2P:
    return GermanG2P(
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        use_spacy=False,
        use_lexicon=False,
    )


def _real_english_g2p() -> EnglishG2P:
    return EnglishG2P(
        language="en-us",
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        use_spacy=False,
        load_gold=True,
        load_silver=True,
        strict=False,
    )


def test_real_english_downstream_contract() -> None:
    source = (
        "Visit St. Patrick at 37 C. Pay $12.50 for 10 in. World War II began in 1984, "
        "and first edition uses 1.02.3."
    )
    prepared = prepare_for_kokorog2p(source, "en")
    assert prepared.spoken_text == (
        "Visit Saint Patrick at thirty seven degrees Celsius Pay "
        "twelve dollars and fifty cents for ten inches World War II began in 1984, "
        "and first edition uses 1.02.3."
    )
    assert [
        (item.source, item.replacement, item.kind, item.rule)
        for item in prepared.source_replacements
    ] == [
        ("St.", "Saint", "abbreviation", "abbr:St."),
        ("37 C.", "thirty seven degrees Celsius", "structured", "en.quantity"),
        ("$12.50", "twelve dollars and fifty cents", "structured", "en.currency"),
        ("10 in.", "ten inches", "structured", "en.quantity"),
    ]
    for item in prepared.source_replacements:
        assert source[item.source_start : item.source_end] == item.source
        assert prepared.spoken_text[item.output_start : item.output_end] == item.replacement
    tokens = _real_english_g2p()(prepared.spoken_text)
    assert tokens
    assert all(token.phonemes for token in tokens)
    assert all(
        prepared.spoken_text[token._["char_start"] : token._["char_end"]] == token.text
        for token in tokens
    )
    assert any(token.text == "1984" for token in tokens)
    assert any(token.text == "II" for token in tokens)
    assert any(token.text == "first" for token in tokens)
    assert any(token.text == "1.02.3" for token in tokens)
    assert not prepared.warnings


def test_real_german_downstream_contract() -> None:
    source = "Zum 14.05.2026 kosten 12,50 EUR."
    prepared = prepare_for_kokorog2p(source, "de")
    assert prepared.spoken_text == (
        "Zum vierzehnten Mai zweitausendsechsundzwanzig kosten zwölf Euro fünfzig."
    )
    assert [(item.source, item.replacement) for item in prepared.source_replacements] == [
        ("14.05.2026", "vierzehnten Mai zweitausendsechsundzwanzig"),
        ("12,50 EUR", "zwölf Euro fünfzig"),
    ]
    tokens = _real_g2p()(prepared.spoken_text)
    assert [token.text for token in tokens] == [
        "Zum",
        "vierzehnten",
        "Mai",
        "zweitausendsechsundzwanzig",
        "kosten",
        "zwölf",
        "Euro",
        "fünfzig",
        ".",
    ]
    assert all(token.phonemes for token in tokens)
    assert all(
        prepared.spoken_text[token._["char_start"] : token._["char_end"]] == token.text
        for token in tokens
    )
    assert not any(character.isdigit() for token in tokens for character in token.text)
    assert not prepared.warnings


def test_real_german_extended_quantity_public_path_matches_semantic_expectation() -> None:
    cases = (
        ("1 mm²", "ein Quadratmillimeter"),
        ("2 mm²", "zwei Quadratmillimeter"),
        ("1 cm²", "ein Quadratzentimeter"),
        ("2 cm²", "zwei Quadratzentimeter"),
        ("1 m²", "ein Quadratmeter"),
        ("2 m²", "zwei Quadratmeter"),
        ("1 km²", "ein Quadratkilometer"),
        ("2 km²", "zwei Quadratkilometer"),
        ("1 ha", "ein Hektar"),
        ("2 ha", "zwei Hektar"),
        ("1 mm³", "ein Kubikmillimeter"),
        ("2 mm³", "zwei Kubikmillimeter"),
        ("1 cm³", "ein Kubikzentimeter"),
        ("2 cm³", "zwei Kubikzentimeter"),
        ("1 m³", "ein Kubikmeter"),
        ("2 m³", "zwei Kubikmeter"),
        ("1 m/s", "ein Meter pro Sekunde"),
        ("2 m/s", "zwei Meter pro Sekunde"),
        ("1 km/h", "ein Kilometer pro Stunde"),
        ("2 km/h", "zwei Kilometer pro Stunde"),
        ("1 m2", "ein Quadratmeter"),
        ("1 m3", "ein Kubikmeter"),
        ("1 cm2", "ein Quadratzentimeter"),
        ("1 cm3", "ein Kubikzentimeter"),
    )
    g2p = _real_g2p()
    for source, expected in cases:
        prepared = prepare_for_kokorog2p(source, "de")
        assert prepared.spoken_text == expected, source
        assert [(item.source, item.replacement) for item in prepared.source_replacements] == [
            (source, expected)
        ]
        tokens = g2p(prepared.spoken_text)
        assert tokens, source
        assert all(token.phonemes for token in tokens), source
        assert all(
            prepared.spoken_text[token._["char_start"] : token._["char_end"]] == token.text
            for token in tokens
        )
        assert not prepared.warnings


def test_real_german_extended_quantity_protected_span_remains_fail_closed() -> None:
    source = "1 m³, then 2 m³."
    first_end = len("1 m³")
    prepared = prepare_for_kokorog2p(
        source,
        "de",
        protected_spans=[ProtectedSpan(0, first_end, kind="g2p-override")],
    )

    assert prepared.spoken_text == "1 m³, then zwei Kubikmeter."
    assert [(item.source, item.replacement) for item in prepared.source_replacements] == [
        ("2 m³", "zwei Kubikmeter")
    ]
    output_start, output_end = prepared.map_source_span(0, first_end)
    assert prepared.spoken_text[output_start:output_end] == "1 m³"
    tokens = _real_g2p()(prepared.spoken_text)
    assert tokens
    assert all(token.phonemes for token in tokens)
    assert not prepared.warnings


def test_real_downstream_protected_override_coordinates() -> None:
    source = "Override 2 kg; normalize 3 kg."
    start = source.index("2 kg")
    prepared = prepare_for_kokorog2p(
        source,
        "de",
        protected_spans=[ProtectedSpan(start, start + len("2 kg"), kind="g2p-override")],
    )
    assert prepared.spoken_text == "Override 2 kg; normalize drei Kilogramm."
    output_start, output_end = prepared.map_source_span(start, start + len("2 kg"))
    assert prepared.spoken_text[output_start:output_end] == "2 kg"
    tokens = _real_g2p()(prepared.spoken_text)
    assert any(token.text == "zwei" for token in tokens)
    assert all(token.phonemes for token in tokens)
    assert all("\ue000" not in token.text for token in tokens)


def _real_spanish_g2p(dialect: str) -> SpanishG2P:
    return SpanishG2P(
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        use_spacy=False,
        dialect=dialect,
    )


def test_real_spanish_downstream_contract_is_dialect_independent() -> None:
    source = "El 14.05.2026 cuesta 12,80 EUR."
    prepared = prepare_for_kokorog2p(source, "es")
    assert prepared.spoken_text == (
        "El catorce de mayo de dos mil veintiséis cuesta doce euros con ochenta céntimos."
    )
    assert [(item.source, item.replacement) for item in prepared.source_replacements] == [
        ("14.05.2026", "catorce de mayo de dos mil veintiséis"),
        ("12,80 EUR", "doce euros con ochenta céntimos"),
    ]
    for dialect in ("es", "la"):
        tokens = _real_spanish_g2p(dialect)(prepared.spoken_text)
        assert tokens
        assert all(token.phonemes for token in tokens)
        assert all(
            prepared.spoken_text[token._["char_start"] : token._["char_end"]] == token.text
            for token in tokens
        )
        assert not any(character.isdigit() for token in tokens for character in token.text)
        assert not prepared.warnings


def test_real_spanish_downstream_protected_override_coordinates() -> None:
    source = "Override 2 kg; normaliza 3 kg."
    start = source.index("2 kg")
    prepared = prepare_for_kokorog2p(
        source,
        "es",
        protected_spans=[ProtectedSpan(start, start + len("2 kg"), kind="g2p-override")],
    )
    assert prepared.spoken_text == "Override 2 kg; normaliza tres kilogramos."
    output_start, output_end = prepared.map_source_span(start, start + len("2 kg"))
    assert prepared.spoken_text[output_start:output_end] == "2 kg"
    for dialect in ("es", "la"):
        tokens = _real_spanish_g2p(dialect)(prepared.spoken_text)
        assert all(token.phonemes for token in tokens)


def _real_french_g2p() -> FrenchG2P:
    return FrenchG2P(
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        use_spacy=False,
        load_gold=True,
        load_silver=False,
    )


def test_real_french_downstream_contract() -> None:
    source = "Le 14.05.2026 coûte 12,05 EUR."
    prepared = prepare_for_kokorog2p(source, "fr")
    assert prepared.spoken_text == (
        "Le quatorze mai deux mille vingt-six coûte douze euros cinq centimes."
    )
    assert [(item.source, item.replacement) for item in prepared.source_replacements] == [
        ("14.05.2026", "quatorze mai deux mille vingt-six"),
        ("12,05 EUR", "douze euros cinq centimes"),
    ]
    tokens = _real_french_g2p()(prepared.spoken_text)
    assert [token.text for token in tokens] == [
        "Le",
        "quatorze",
        "mai",
        "deux",
        "mille",
        "vingt",
        "-",
        "six",
        "coûte",
        "douze",
        "euros",
        "cinq",
        "centimes",
        ".",
    ]
    assert all(token.phonemes is not None for token in tokens)
    assert all(
        prepared.spoken_text[token._["char_start"] : token._["char_end"]] == token.text
        for token in tokens
    )
    assert not any(character.isdigit() for token in tokens for character in token.text)
    assert not prepared.warnings


def test_real_french_downstream_protected_override_coordinates() -> None:
    source = "Override 2 kg; normalise 3 kg."
    start = source.index("2 kg")
    prepared = prepare_for_kokorog2p(
        source,
        "fr",
        protected_spans=[ProtectedSpan(start, start + len("2 kg"), kind="g2p-override")],
    )
    assert prepared.spoken_text == "Override 2 kg; normalise trois kilogrammes."
    output_start, output_end = prepared.map_source_span(start, start + len("2 kg"))
    assert prepared.spoken_text[output_start:output_end] == "2 kg"
    tokens = _real_french_g2p()(prepared.spoken_text)
    assert all(token.phonemes is not None for token in tokens)
    assert all("\ue000" not in token.text for token in tokens)


def _real_italian_g2p() -> ItalianG2P:
    return ItalianG2P(
        use_espeak_fallback=False,
        use_goruut_fallback=False,
        use_spacy=False,
    )


def test_real_italian_downstream_contract() -> None:
    source = "Il 14.05.2026 costa 12,80 EUR."
    prepared = prepare_for_kokorog2p(source, "it")
    assert prepared.spoken_text == (
        "Il quattordici maggio duemilaventisei costa dodici euro e ottanta centesimi."
    )
    assert [(item.source, item.replacement) for item in prepared.source_replacements] == [
        ("14.05.2026", "quattordici maggio duemilaventisei"),
        ("12,80 EUR", "dodici euro e ottanta centesimi"),
    ]
    tokens = _real_italian_g2p()(prepared.spoken_text)
    assert tokens
    assert all(token.phonemes for token in tokens if token.is_word)
    assert all(
        prepared.spoken_text[token._["char_start"] : token._["char_end"]] == token.text
        for token in tokens
    )
    assert not any(character.isdigit() for token in tokens for character in token.text)
    assert not prepared.warnings


def test_real_italian_protected_override_coordinates() -> None:
    source = "Override 2 kg; normalizza 3 kg."
    start = source.index("2 kg")
    prepared = prepare_for_kokorog2p(
        source,
        "it",
        protected_spans=[ProtectedSpan(start, start + len("2 kg"), kind="g2p-override")],
    )
    assert prepared.spoken_text == "Override 2 kg; normalizza tre chilogrammi."
    output_start, output_end = prepared.map_source_span(start, start + len("2 kg"))
    assert prepared.spoken_text[output_start:output_end] == "2 kg"
    tokens = _real_italian_g2p()(prepared.spoken_text)
    assert any(token.text == "tre" for token in tokens)
    assert all(token.phonemes for token in tokens if token.is_word)
    assert all("\ue000" not in token.text for token in tokens)


def _real_portuguese_g2p(dialect: str = "br") -> PortugueseG2P:
    return PortugueseG2P(
        use_espeak_fallback=False,
        use_spacy=False,
        dialect=dialect,
    )


def test_real_portuguese_downstream_contract() -> None:
    source = "Em 14.05.2026, o Sr. Silva paga R$ 12,80 por 2 kg."
    prepared = prepare_for_kokorog2p(source, "pt-br")
    assert prepared.spoken_text == (
        "Em catorze de maio de dois mil e vinte e seis, o Senhor Silva paga "
        "doze reais e oitenta centavos por dois quilogramas."
    )
    assert [(item.source, item.replacement) for item in prepared.source_replacements] == [
        ("14.05.2026", "catorze de maio de dois mil e vinte e seis"),
        ("Sr.", "Senhor"),
        ("R$ 12,80", "doze reais e oitenta centavos"),
        ("2 kg", "dois quilogramas"),
    ]
    tokens = _real_portuguese_g2p()(prepared.spoken_text)
    assert tokens
    assert all(token.phonemes for token in tokens)
    assert all(
        prepared.spoken_text[token._["char_start"] : token._["char_end"]] == token.text
        for token in tokens
    )
    assert not any(character.isdigit() for token in tokens for character in token.text)
    assert not prepared.warnings


def test_real_portuguese_protected_override_coordinates() -> None:
    source = "Override 2 kg; normaliza 3 kg."
    start = source.index("2 kg")
    prepared = prepare_for_kokorog2p(
        source,
        "pt-br",
        protected_spans=[ProtectedSpan(start, start + len("2 kg"), kind="g2p-override")],
    )
    assert prepared.spoken_text == "Override 2 kg; normaliza três quilogramas."
    output_start, output_end = prepared.map_source_span(start, start + len("2 kg"))
    assert prepared.spoken_text[output_start:output_end] == "2 kg"
    tokens = _real_portuguese_g2p()(prepared.spoken_text)
    assert any(token.text == "três" and token.phonemes for token in tokens)
    assert all("\ue000" not in token.text for token in tokens)
