from __future__ import annotations

import unicodedata

import pytest

pytest.importorskip("piperg2p")

from piperg2p import RawPhonemeSegment, parse_raw_blocks, phonemize_prepared  # noqa: E402

from spokenform import ProtectedSpan, prepare_for_piperg2p  # noqa: E402


def _text_voice_config(text: str) -> dict[str, object]:
    phonemes = sorted(set(unicodedata.normalize("NFD", text)))
    symbols = ["_", "^", "$", *(phoneme for phoneme in phonemes if phoneme not in {"_", "^", "$"})]
    phoneme_id_map = {symbol: index for index, symbol in enumerate(symbols)}
    return {
        "num_symbols": len(phoneme_id_map),
        "num_speakers": 1,
        "audio": {"sample_rate": 22050},
        "inference": {},
        "espeak": {"voice": "en-us"},
        "phoneme_type": "text",
        "phoneme_id_map": phoneme_id_map,
    }


def test_real_piperg2p_downstream_contract() -> None:
    source = "Pay 12.50 USD for 2 kg."
    prepared = prepare_for_piperg2p(source, "en")

    result = phonemize_prepared(
        prepared.spoken_text,
        language="en-us",
        config=_text_voice_config(prepared.spoken_text),
        missing="error",
    )

    assert result.clean_text == prepared.spoken_text
    assert result.token_ids
    assert not result.missing_phonemes
    assert not any(character.isdigit() for character in prepared.spoken_text)
    assert [(item.source, item.replacement) for item in prepared.source_replacements] == [
        ("12.50 USD", "twelve dollars and fifty cents"),
        ("2 kg", "two kilograms"),
    ]
    for token in result.tokens:
        assert prepared.spoken_text[token.char_start : token.char_end] == token.text


def test_real_piperg2p_parser_boundary_protects_raw_blocks() -> None:
    source = "Use 2 kg [[ tɛst ]] and 3 kg."
    protected = [
        ProtectedSpan(
            segment.source_start,
            segment.source_end,
            kind="piperg2p-raw-phonemes",
        )
        for segment in parse_raw_blocks(source)
        if isinstance(segment, RawPhonemeSegment)
    ]

    prepared = prepare_for_piperg2p(source, "en", protected_spans=protected)

    assert "[[ tɛst ]]" in prepared.spoken_text
    assert len(prepared.source_replacements) == 2
    assert [item.source for item in prepared.source_replacements] == ["2 kg", "3 kg"]
    start, end = prepared.map_source_span(protected[0].start, protected[0].end)
    assert prepared.spoken_text[start:end] == "[[ tɛst ]]"
