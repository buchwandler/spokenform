"""Real downstream contract checks, enabled by the kokorog2p CI job."""

from __future__ import annotations

import pytest

pytest.importorskip("kokorog2p")
from kokorog2p.de.g2p import GermanG2P  # noqa: E402
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


def test_real_german_downstream_contract() -> None:
    source = "Zum 14.05.2026 kosten 12,50 EUR."
    prepared = prepare_for_kokorog2p(source, "de")
    assert prepared.spoken_text == (
        "Zum vierzehnten Mai zweitausendsechsundzwanzig kosten zwölf Euro fünfzig Cent."
    )
    assert [(item.source, item.replacement) for item in prepared.source_replacements] == [
        ("14.05.2026", "vierzehnten Mai zweitausendsechsundzwanzig"),
        ("12,50 EUR", "zwölf Euro fünfzig Cent"),
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
        "Cent",
        ".",
    ]
    assert all(token.phonemes for token in tokens)
    assert all(
        prepared.spoken_text[token._["char_start"] : token._["char_end"]] == token.text
        for token in tokens
    )
    assert not any(character.isdigit() for token in tokens for character in token.text)
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
