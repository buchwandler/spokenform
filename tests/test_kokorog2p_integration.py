import re

from spokenform import prepare_for_kokorog2p


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
