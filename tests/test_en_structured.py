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
}


def _fixture_rows() -> list[dict[str, str]]:
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("language", ["en", "en-us", "en-gb"])
def test_english_parity_fixture(language: str) -> None:
    for row in _fixture_rows():
        result = prepare(row["source"], language=language, use_spacy=False)
        assert result.spoken_text == row["spoken"], row["id"]
        if "rule" in row:
            assert any(edit.rule == row["rule"] for edit in result.source_replacements), row["id"]


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
    assert result.map_source_span(start, start + len("2 kg")) == (len("Protect "), len("Protect 2 kg"))
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
        "forty two minus five three point one four point zero two thirty thousand 1984 1st II 1.02.3"
    )
    assert prepare(result.spoken_text, language="en", use_spacy=False).spoken_text == result.spoken_text


def test_number_policy_for_english_aliases() -> None:
    assert all(number_policy_for_language(language) is NumberPolicy.STRUCTURED_AND_PLAIN for language in ("en", "en-us", "en-gb"))
