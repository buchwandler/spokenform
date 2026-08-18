import pytest

from spokenform import prepare


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("9pm", "nine P M"),
        ("9PM", "nine P M"),
        ("9 pm", "nine P M"),
        ("9 PM", "nine P M"),
        ("9p.m.", "nine P M."),
        ("9 P.M.", "nine P M."),
        ("12am", "twelve A M"),
        ("12pm", "twelve P M"),
        ("7 AM", "seven A M"),
    ],
)
def test_explicit_ampm_bare_hour_forms_are_atomic(source: str, expected: str) -> None:
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == expected
    assert [(item.source, item.rule, item.replacement) for item in result.source_replacements] == [
        (source, "en.time", expected)
    ]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("9:05am", "nine oh five A M"),
        ("9:05 AM", "nine oh five A M"),
        ("8:15PM", "eight fifteen P M"),
        ("8:15 PM", "eight fifteen P M"),
        ("5:30 AM", "five thirty A M"),
        ("11:30PM", "eleven thirty P M"),
        ("12:00AM", "twelve A M"),
        ("6:00 PM", "six P M"),
        ("2:00 PM", "two P M"),
    ],
)
def test_explicit_ampm_minute_forms_render_without_oclock(source: str, expected: str) -> None:
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == expected
    assert [(item.source, item.rule, item.replacement) for item in result.source_replacements] == [
        (source, "en.time", expected)
    ]


@pytest.mark.parametrize(
    ("source", "expected", "time_source", "replacement"),
    [
        ("Meet me at 9pm.", "Meet me at nine P M.", "9pm", "nine P M"),
        (
            "The show starts at 8:15 PM.",
            "The show starts at eight fifteen P M.",
            "8:15 PM",
            "eight fifteen P M",
        ),
        (
            "Breakfast is served at 7 AM.",
            "Breakfast is served at seven A M.",
            "7 AM",
            "seven A M",
        ),
        (
            "Our next call is 8pm Friday.",
            "Our next call is eight P M Friday.",
            "8pm",
            "eight P M",
        ),
        ("Meet at 9 p.m.", "Meet at nine P M.", "9 p.m.", "nine P M."),
        ("Meet at 9 p.m. tomorrow", "Meet at nine P M tomorrow", "9 p.m.", "nine P M"),
        ("Meet at 9 p.m., Friday", "Meet at nine P M, Friday", "9 p.m.", "nine P M"),
    ],
)
def test_explicit_ampm_sentence_integration_preserves_owned_span(
    source: str, expected: str, time_source: str, replacement: str
) -> None:
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == expected
    replacements = [item for item in result.source_replacements if item.rule == "en.time"]
    assert len(replacements) == 1
    assert replacements[0].source == time_source
    assert replacements[0].replacement == replacement


@pytest.mark.parametrize(
    "source",
    ["13pm", "00am", "13:00PM", "00:30AM", "13:00 PM", "00:30 AM", "9pm2", "9pmx", "rpm", "PM2"],
)
def test_invalid_explicit_ampm_forms_do_not_claim_time(source: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert not any(item.rule == "en.time" for item in result.source_replacements)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("3:00", "three o'clock"),
        ("3:05", "three oh five"),
        ("23:30", "twenty three thirty"),
    ],
)
def test_unmarked_english_clock_behavior_is_unchanged(source: str, expected: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert result.spoken_text == expected
    assert any(item.rule == "en.time" for item in result.source_replacements)
