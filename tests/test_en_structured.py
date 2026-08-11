from __future__ import annotations

import json
from pathlib import Path

import pytest
from abbr2words import iter_unit_matches
from abbr2words.units import unit_entries

from spokenform import ProtectedSpan, iter_structured_replacements, prepare
from spokenform.config import NumberPolicy, number_policy_for_language
from spokenform.locales.en import QUANTITY_GRAMMAR

_FIXTURE = Path(__file__).parent / "data" / "en_kokorog2p_parity.json"
_CURRENCY_IDS = {
    "currency-euro",
    "currency-us-dollar",
    "currency-pound-sterling",
    "currency-japanese-yen",
    "currency-swiss-franc",
    "currency-indian-rupee",
    "currency-south-korean-won",
    "currency-mexican-peso",
}


def _fixture_rows() -> list[dict[str, str]]:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("language", ["en", "en-gb"])
def test_english_parity_fixture(language: str) -> None:
    for row in _fixture_rows():
        result = prepare(
            row["source"],
            language=language,
            use_spacy=False,
            expand_numbers=row.get("expand_numbers", True),
        )
        assert result.spoken_text == row["spoken"], row["id"]
        if "rule" in row:
            assert any(edit.rule == row["rule"] for edit in result.source_replacements), row["id"]


def test_english_us_uses_regional_cardinal_and_year_style() -> None:
    assert prepare("250 mg", language="en_US", use_spacy=False).spoken_text == (
        "two hundred fifty milligrams"
    )
    assert prepare("05/20/2023", language="en_US", use_spacy=False).spoken_text == (
        "May twentieth twenty twenty three"
    )


def test_all_current_english_canonical_ids_have_grammar() -> None:
    canonical_ids = {entry.canonical_id for entry in unit_entries("en")}
    assert canonical_ids == set(QUANTITY_GRAMMAR) | _CURRENCY_IDS

    for entry in unit_entries("en"):
        source = f"2 {entry.canonical_symbol}"
        matches = list(iter_unit_matches(source, "en"))
        assert matches and matches[0].canonical_id == entry.canonical_id
        replacements = iter_structured_replacements(source, language="en")
        assert replacements, entry.canonical_id


def test_structured_rules_and_source_mapping_are_exact() -> None:
    source = "At 3:00, pay $12.50 for 2 kg; then 2 kg."
    result = prepare(source, language="en", use_spacy=False)
    assert result.spoken_text == (
        "At three o'clock, pay twelve dollars and fifty cents for two kilograms; then two kilograms."
    )
    assert [(item.source, item.rule) for item in result.source_replacements] == [
        ("3:00", "en.time"),
        ("$12.50", "en.currency"),
        ("2 kg", "en.quantity"),
        ("2 kg", "en.quantity"),
    ]
    for item in result.source_replacements:
        assert source[item.source_start : item.source_end] == item.source
        assert result.spoken_text[item.output_start : item.output_end] == item.replacement
    rebuilt: list[str] = []
    cursor = 0
    for item in result.source_replacements:
        rebuilt.extend((source[cursor : item.source_start], item.replacement))
        cursor = item.source_end
    rebuilt.append(source[cursor:])
    assert "".join(rebuilt) == result.spoken_text


def test_english_contextual_dot_zero_version_label_uses_oh() -> None:
    source = "We had built bot 2.0."
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == "We had built bot two point oh."
    assert len(result.source_replacements) == 1
    replacement = result.source_replacements[0]
    start = source.index("2.0")
    assert (replacement.source_start, replacement.source_end) == (start, start + 3)
    assert replacement.source == "2.0"
    assert replacement.replacement == "two point oh"
    assert replacement.kind == "structured"
    assert replacement.rule == "en.version_decimal"
    assert source[replacement.source_end :] == "."


@pytest.mark.parametrize(
    ("source", "spoken"),
    [
        ("Version 2.0.", "Version two point oh."),
        ("release 3.0", "release three point oh"),
        ("API 2.0", "API two point oh"),
        ("bot 2.0", "bot two point oh"),
        ("Acme 2.0", "Acme two point oh"),
    ],
)
def test_english_contextual_version_labels_use_release_style_zero(source: str, spoken: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert result.spoken_text == spoken
    assert [(item.source, item.rule) for item in result.source_replacements] == [
        (source.split()[-1].rstrip("."), "en.version_decimal")
    ]


@pytest.mark.parametrize(
    ("source", "spoken"),
    [
        ("The value is 2.0.", "The value is two point zero."),
        ("The score is 2.0.", "The score is two point zero."),
        ("It measured 2.0 kg.", "It measured two point zero kilograms."),
        ("Wait .02 seconds.", "Wait point zero two seconds."),
        ("The ratio is 2.05.", "The ratio is two point zero five."),
    ],
)
def test_english_decimal_contrasts_keep_ordinary_zero_wording(source: str, spoken: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert result.spoken_text == spoken
    assert not any(item.rule == "en.version_decimal" for item in result.source_replacements)


def test_english_version_context_defers_to_quantity_grammar() -> None:
    source = "It measured 2.0 kg."
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == "It measured two point zero kilograms."
    assert [(item.source, item.rule, item.kind) for item in result.source_replacements] == [
        ("2.0 kg", "en.quantity", "structured")
    ]


def test_english_version_rule_respects_protected_spans_and_is_idempotent() -> None:
    source = "Keep Acme 2.0 exactly."
    start = source.index("2.0")
    protected = prepare(
        source,
        language="en",
        use_spacy=False,
        protected_spans=[ProtectedSpan(start, start + 3, kind="literal")],
    )
    assert protected.spoken_text == source
    assert not protected.source_replacements

    first = prepare("We had built bot 2.0.", language="en", use_spacy=False)
    second = prepare(first.spoken_text, language="en", use_spacy=False)
    assert second.spoken_text == first.spoken_text


def test_high_plural_tens_are_not_seconds() -> None:
    source = "There was a chance in the high 70s that they knew."
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == "There was a chance in the high seventies that they knew."
    replacements = [item for item in result.source_replacements if item.rule == "en.plural_tens"]
    assert len(replacements) == 1
    replacement = replacements[0]
    assert replacement.source == "70s"
    assert replacement.replacement == "seventies"
    assert source[replacement.source_start : replacement.source_end] == "70s"
    assert result.spoken_text[replacement.output_start : replacement.output_end] == "seventies"
    assert result.map_source_span(replacement.source_start, replacement.source_end) == (
        replacement.output_start,
        replacement.output_end,
    )


@pytest.mark.parametrize(
    ("source", "spoken"),
    [
        ("high 70s", "high seventies"),
        ("low 80s", "low eighties"),
        ("mid 60s", "mid sixties"),
        ("upper 90s", "upper nineties"),
        ("lower 40s", "lower forties"),
        ("early 50s", "early fifties"),
        ("late 30s", "late thirties"),
    ],
)
def test_plural_tens_range_modifiers(source: str, spoken: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert result.spoken_text == spoken
    assert [(item.source, item.replacement, item.rule) for item in result.source_replacements] == [
        (source.split()[-1], spoken.split()[-1], "en.plural_tens")
    ]


@pytest.mark.parametrize(
    ("source", "spoken"),
    [
        ("He was in his 70s.", "He was in his seventies."),
        ("Music from the 80s was playing.", "Music from the eighties was playing."),
        ("During the 90s it changed.", "During the nineties it changed."),
    ],
)
def test_plural_tens_age_and_era_contexts(source: str, spoken: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert result.spoken_text == spoken
    assert any(item.rule == "en.plural_tens" for item in result.source_replacements)


@pytest.mark.parametrize(
    ("source", "spoken"),
    [
        ("It took 70s.", "It took seventy seconds."),
        ("Wait 5s.", "Wait five seconds."),
        ("The timeout is 30s.", "The timeout is thirty seconds."),
        ("Pause for 20s.", "Pause for twenty seconds."),
        ("Wait 70 s.", "Wait seventy seconds."),
        ("Wait 70 sec.", "Wait seventy seconds."),
        ("Wait 15s.", "Wait fifteen seconds."),
        ("Wait 25s.", "Wait twenty five seconds."),
        ("Wait 75s.", "Wait seventy five seconds."),
    ],
)
def test_plural_tens_context_does_not_change_duration_candidates(source: str, spoken: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert result.spoken_text == spoken
    assert any(item.rule == "en.quantity" for item in result.source_replacements)
    assert not any(item.rule == "en.plural_tens" for item in result.source_replacements)


@pytest.mark.parametrize("language", ["en", "en-us", "en-gb"])
def test_plural_tens_aliases_agree(language: str) -> None:
    source = "There was a chance in the high 70s that they knew."
    result = prepare(source, language=language, use_spacy=False)
    assert result.spoken_text == "There was a chance in the high seventies that they knew."
    assert any(item.rule == "en.plural_tens" for item in result.source_replacements)


def test_plural_tens_respects_protected_spans() -> None:
    source = "Keep high 70s exactly."
    start = source.index("70s")
    result = prepare(
        source,
        language="en",
        use_spacy=False,
        protected_spans=[ProtectedSpan(start, start + len("70s"), kind="literal")],
    )
    assert result.spoken_text == source
    assert not result.source_replacements


def test_plural_tens_is_idempotent_and_four_digit_decades_remain_out_of_scope() -> None:
    source = "There was a chance in the high 70s that they knew."
    first = prepare(source, language="en", use_spacy=False)
    second = prepare(first.spoken_text, language="en", use_spacy=False)
    assert second.spoken_text == first.spoken_text

    decade = prepare("the 1970s", language="en", use_spacy=False)
    assert not any(item.rule == "en.plural_tens" for item in decade.source_replacements)
    assert any(
        item.source == "1970s" and item.rule == "en.quantity" for item in decade.source_replacements
    )


@pytest.mark.parametrize(
    ("source", "spoken"),
    [
        ("37 C.", "thirty seven degrees Celsius"),
        ("37C", "thirty seven degrees Celsius"),
        ("37° C", "thirty seven degrees Celsius"),
        ("37 ° C", "thirty seven degrees Celsius"),
        ("37 c.", "thirty seven degrees Celsius"),
        ("98 F.", "ninety eight degrees Fahrenheit"),
        ("98F", "ninety eight degrees Fahrenheit"),
        ("98° F", "ninety eight degrees Fahrenheit"),
        ("-40 C.", "minus forty degrees Celsius"),
    ],
)
def test_temperature_aliases_are_atomic_source_aligned_replacements(
    source: str, spoken: str
) -> None:
    wrapped = f"Before {source} after"
    result = prepare(wrapped, language="en", use_spacy=False)
    start = wrapped.index(source)
    end = start + len(source)

    assert result.spoken_text == f"Before {spoken} after"
    assert len(result.source_replacements) == 1
    replacement = result.source_replacements[0]
    assert (replacement.source_start, replacement.source_end) == (start, end)
    assert replacement.source == source
    assert replacement.replacement == spoken
    assert replacement.rule == "en.quantity"
    assert replacement.kind == "structured"
    output_start, output_end = result.map_source_span(start, end)
    assert result.spoken_text[output_start:output_end] == spoken


@pytest.mark.parametrize(
    ("source", "spoken"),
    [
        ("Visit St.", "Visit Saint"),
        ("123 Main St.", "one two three Main Street"),
        ("St. Patrick", "Saint Patrick"),
        ("They wandered around in.", "They wandered around in."),
        ("10 in.", "ten inches."),
    ],
)
def test_english_abbreviation_compatibility(source: str, spoken: str) -> None:
    result = prepare(
        source,
        language="en",
        expand_numbers=False,
        use_spacy=False,
    )
    assert result.spoken_text == spoken


def test_currency_precision_and_invalid_structured_values_fail_closed() -> None:
    assert prepare("$1.005", language="en", use_spacy=False).spoken_text == "$1.005"
    assert prepare("$12,50", language="en", use_spacy=False).spoken_text == "$12,50"
    assert prepare("24:00 12:99 31.02.2026", language="en", use_spacy=False).spoken_text == (
        "24:00 12:99 31.02.2026"
    )


def test_protection_is_atomic_and_repeated_fragments_map_independently() -> None:
    source = "Protect 2 kg and 2 kg; URL https://example.org/2 and dev2@example.org."
    start = source.index("2 kg")
    result = prepare(
        source,
        language="en",
        use_spacy=False,
        protected_spans=[ProtectedSpan(start, start + len("2 kg"), kind="override")],
    )
    assert result.spoken_text == (
        "Protect 2 kg and two kilograms; URL https://example.org/2 and dev2@example.org."
    )
    assert result.map_source_span(start, start + len("2 kg")) == (
        len("Protect "),
        len("Protect 2 kg"),
    )
    assert "\ue000" not in result.spoken_text
    assert all("\ue000" not in str(value) for value in result.to_dict().values())


def test_partial_quantity_protection_fails_closed_for_the_whole_candidate() -> None:
    source = "2 kg and 3 kg"
    start = source.index("2 kg") + 2
    result = prepare(source, language="en", use_spacy=False, protected_spans=[(start, start + 2)])
    assert result.spoken_text == "2 kg and three kilograms"


def test_idempotence_and_plain_number_reservations() -> None:
    source = "42 -5 3.14 .02 30,000 1984 1st II 1.02.3"
    result = prepare(source, language="en", use_spacy=False)
    assert result.spoken_text == (
        "forty two minus five three point one four point zero two thirty thousand 1984 first II 1.02.3"
    )
    assert (
        prepare(result.spoken_text, language="en", use_spacy=False).spoken_text
        == result.spoken_text
    )


def test_number_policy_for_english_aliases() -> None:
    assert all(
        number_policy_for_language(language) is NumberPolicy.STRUCTURED_AND_PLAIN
        for language in ("en", "en-us", "en-gb")
    )
