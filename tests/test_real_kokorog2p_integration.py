"""Real downstream contract checks, enabled by the kokorog2p CI job."""

from __future__ import annotations

import pytest

pytest.importorskip("kokorog2p")
from kokorog2p.de.g2p import GermanG2P  # noqa: E402

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
