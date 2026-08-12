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


def test_english_adapter_preserves_migrated_and_reserved_ownership() -> None:
    source = (
        "Visit St. Patrick at 37 C. Pay $12.50 for 10 in. World War II began in 1984, "
        "and first edition uses 1.02.3."
    )
    result = prepare_for_kokorog2p(source, "en")
    assert result.spoken_text == (
        "Visit Saint Patrick at thirty seven degrees Celsius Pay "
        "twelve dollars and fifty cents for ten inches World War II began in nineteen eighty four, "
        "and first edition uses 1.02.3."
    )
    assert [(item.source, item.rule) for item in result.source_replacements] == [
        ("St.", "abbr:St."),
        ("37 C.", "en.quantity"),
        ("$12.50", "en.currency"),
        ("10 in.", "en.quantity"),
        ("1984", "sequence.year"),
    ]
    assert [(item.source, item.replacement, item.kind) for item in result.source_replacements] == [
        ("St.", "Saint", "abbreviation"),
        ("37 C.", "thirty seven degrees Celsius", "structured"),
        ("$12.50", "twelve dollars and fifty cents", "structured"),
        ("10 in.", "ten inches", "structured"),
        ("1984", "nineteen eighty four", "structured"),
    ]
    for item in result.source_replacements:
        assert source[item.source_start : item.source_end] == item.source
        assert result.spoken_text[item.output_start : item.output_end] == item.replacement
    tokens = _tokenize(result.spoken_text)
    assert "nineteen" in tokens and "II" in tokens
    assert "first" in result.spoken_text and "1.02.3" in result.spoken_text
    assert _phonemize(tokens) == [token.casefold() for token in tokens]
    assert "\ue000" not in result.spoken_text


def test_english_adapter_disambiguates_high_plural_tens() -> None:
    source = "There was a chance in the high 70s that they knew."
    result = prepare_for_kokorog2p(source, "en")

    assert result.spoken_text == "There was a chance in the high seventies that they knew."
    assert any(
        item.source == "70s" and item.replacement == "seventies" and item.rule == "en.plural_tens"
        for item in result.source_replacements
    )
