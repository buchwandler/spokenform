from spokenform import prepare


def test_german_readable_pipeline() -> None:
    result = prepare(
        "Prof. Klein bringt am 14.05.2026 um 18:20 Uhr 2 kg mit.",
        language="de",
    )

    assert result.language == "de"
    assert "Professor Klein" in result.spoken_text
    assert "vierzehnten Mai" in result.spoken_text
    assert "achtzehn Uhr zwanzig" in result.spoken_text
    assert "zwei Kilogramm" in result.spoken_text
    assert [stage.name for stage in result.stages] == [
        "abbreviations",
        "numbers",
        "whitespace",
    ]
    assert result.changed
    assert result.edits


def test_disable_stages() -> None:
    result = prepare(
        "Prof. Klein hat 2 kg.",
        language="de",
        expand_abbreviations=False,
        expand_numbers=False,
        normalize_whitespace=False,
    )
    assert result.spoken_text == "Prof. Klein hat 2 kg."
    assert result.stages == ()


def test_custom_detector_is_injectable() -> None:
    result = prepare("Das ist ein Test.", detect_language=True, detector=lambda _: "de")
    assert result.language == "de"
    assert result.language_spans[0].source == "detected"


def test_spacing_is_last_and_reviewable() -> None:
    result = prepare(
        "  Hello\u00a0  world  ",
        language="en",
        expand_abbreviations=False,
        expand_numbers=False,
    )
    assert result.spoken_text == "Hello world"
    assert result.stages[-1].name == "whitespace"
    assert result.stages[-1].changed
