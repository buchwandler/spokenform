import re

from spokenform import ProtectedSpan, prepare_for_kokorog2p


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÄÖÜäöüß]+|\d+|[^\w\s]", text)


def _phonemize(tokens: list[str]) -> list[str]:
    # Stable downstream stand-in: the real G2P owns this transformation.
    return [token.casefold() for token in tokens]


def test_german_adapter_token_and_phoneme_parity_fixture() -> None:
    source = "Zum 14.05.2026 um 18:20 Uhr."
    result = prepare_for_kokorog2p(source, "de")
    tokens = _tokenize(result.spoken_text)
    phonemes = _phonemize(tokens)

    assert result.spoken_text == (
        "Zum vierzehnten Mai zweitausendsechsundzwanzig um achtzehn Uhr zwanzig."
    )
    assert tokens == [
        "Zum",
        "vierzehnten",
        "Mai",
        "zweitausendsechsundzwanzig",
        "um",
        "achtzehn",
        "Uhr",
        "zwanzig",
        ".",
    ]
    assert phonemes == [token.casefold() for token in tokens]
    assert "\ue000" not in result.spoken_text
    assert all("\ue000" not in warning for warning in result.warnings)


def test_adapter_protected_override_and_adjacent_semantic_expression() -> None:
    source = "Override 2 kg; speak 3 kg."
    start = source.index("2 kg")
    result = prepare_for_kokorog2p(
        source,
        "de",
        protected_spans=[ProtectedSpan(start, start + len("2 kg"), kind="g2p-override")],
    )
    assert result.spoken_text == "Override 2 kg; speak drei Kilogramm."
    assert result.protected_spans[0].kind == "g2p-override"
    assert result.map_source_span(start, start + len("2 kg")) == (start, start + len("2 kg"))


def test_adapter_contract_keeps_runs_composable() -> None:
    source = "  Hallo  2 kg  "
    left = prepare_for_kokorog2p(source[:8], "de")
    right = prepare_for_kokorog2p(source[8:], "de")
    assert left.spoken_text + right.spoken_text == "  Hallo  zwei Kilogramm  "


def test_french_adapter_token_and_phoneme_parity_fixture() -> None:
    source = "Le 14.05.2026 coûte 12,80 EUR."
    result = prepare_for_kokorog2p(source, "fr")
    tokens = _tokenize(result.spoken_text)
    phonemes = _phonemize(tokens)
    assert result.spoken_text == (
        "Le quatorze mai deux mille vingt-six coûte douze euros quatre-vingts centimes."
    )
    assert phonemes == [token.casefold() for token in tokens]
    assert all(not any(character.isdigit() for character in token) for token in tokens)
    assert all("\ue000" not in warning for warning in result.warnings)
