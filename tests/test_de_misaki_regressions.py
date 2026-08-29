"""German regression cases derived from the Misaki review."""

import pytest

from spokenform import PreparationConfig, prepare
from spokenform.config import RecognitionDomain


def test_german_time_does_not_consume_uhrzeit_prefix() -> None:
    source = "Um 14:30 Uhrzeit beginnt es."
    result = prepare(source, language="de", use_spacy=False)

    assert "dreißigzeit" not in result.spoken_text
    assert "Uhrzeit" in result.spoken_text
    assert [(item.source, item.replacement, item.rule) for item in result.source_replacements] == [
        ("14:30", "vierzehn Uhr dreißig", "de.time")
    ]
    assert result.offset_map is not None
    replacement = result.source_replacements[0]
    assert result.offset_map.map_source_span(replacement.source_start, replacement.source_end) == (
        replacement.output_start,
        replacement.output_end,
    )


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("14:30 Uhr", "vierzehn Uhr dreißig"),
        ("14:30", "vierzehn Uhr dreißig"),
        ("24:00 Uhr", "24:00 Uhr"),
        ("23:99 Uhr", "23:99 Uhr"),
        ("14:00-15:30 Uhrzeit", "vierzehn bis fünfzehn Uhr dreißig Uhrzeit"),
        ("14:00 bis 15:30 Uhrwerk", "vierzehn bis fünfzehn Uhr dreißig Uhrwerk"),
    ],
)
def test_german_time_boundaries_and_invalid_values(source: str, expected: str) -> None:
    result = prepare(source, language="de", use_spacy=False)

    assert result.spoken_text == expected
    if source.startswith(("24:", "23:99")):
        assert not any(item.rule == "de.time" for item in result.source_replacements)


@pytest.mark.parametrize("source", ["24:00", "25:00", "23:99", "25:99"])
def test_german_invalid_time_is_not_claimed(source: str) -> None:
    result = prepare(source, language="de", use_spacy=False)

    assert source in result.spoken_text
    assert not any(item.rule == "de.time" for item in result.source_replacements)


@pytest.mark.parametrize(
    ("source", "fragment"),
    [
        ("am 14.05.2026", "am vierzehnten Mai"),
        ("Am 3.10.1990", "Am dritten Oktober"),
        ("vom 14.05.2026", "vom vierzehnten Mai"),
        ("zum 14.05.2026", "zum vierzehnten Mai"),
        ("der 14.05.2026", "der vierzehnte Mai"),
        ("auf die 2. Schiene", "auf die zweite Schiene"),
        ("auf der 7. Etage", "auf der siebten Etage"),
        ("zur 6. Version", "zur sechsten Version"),
    ],
)
def test_german_full_date_uses_bounded_context_inflection(
    source: str,
    fragment: str,
) -> None:
    result = prepare(source, language="de", use_spacy=False)
    assert fragment in result.spoken_text


@pytest.mark.parametrize(
    ("source", "expected"),
    [("Das Team 14.05.2026", "Das Team vierzehnter Mai zweitausendsechsundzwanzig")],
)
def test_german_context_lookalike_does_not_trigger_inflection(
    source: str,
    expected: str,
) -> None:
    assert prepare(source, language="de", use_spacy=False).spoken_text == expected


def test_german_large_ordinals_and_calendar_validation() -> None:
    assert prepare("am 100. Tag", language="de", use_spacy=False).spoken_text == (
        "am hundertsten Tag"
    )
    assert prepare("am 1000. Tag", language="de", use_spacy=False).spoken_text == (
        "am tausendsten Tag"
    )
    for source in ("31.02.2026", "29.02.2025"):
        result = prepare(source, language="de", use_spacy=False)
        assert result.spoken_text == source
        assert not any(item.rule == "de.date" for item in result.source_replacements)


def test_currency_preserves_excess_fractional_precision() -> None:
    cases = [
        ("de", "9,999 EUR", "neun Komma neun neun neun Euro"),
        ("de", "€9,999", "neun Komma neun neun neun Euro"),
        ("de", "-9,999 EUR", "minus neun Komma neun neun neun Euro"),
        ("fr", "9,999 EUR", "neuf virgule neuf neuf neuf euros"),
    ]
    for language, source, expected in cases:
        result = prepare(source, language=language, use_spacy=False)
        assert result.spoken_text == expected
        assert "neunundneunzig" not in result.spoken_text
        assert "99" not in result.spoken_text


def test_point_decimal_currency_preserves_excess_fractional_precision() -> None:
    result = prepare("$9.999", language="en", use_spacy=False)
    assert result.spoken_text == "$9.999"
    assert not any(item.rule == "en.currency" for item in result.source_replacements)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("§§ 12, 13 BGB", "Paragrafen zwölf, dreizehn B G B"),
        ("§§ 12 und 13 BGB", "Paragrafen zwölf und dreizehn B G B"),
        ("§§ 12-14 BGB", "Paragrafen zwölf bis vierzehn B G B"),
        ("§§ 12–14 BGB", "Paragrafen zwölf bis vierzehn B G B"),
    ],
)
def test_german_plural_paragraph_references_are_atomic(
    source: str,
    expected: str,
) -> None:
    result = prepare(source, language="de", use_spacy=False)
    assert result.spoken_text == expected
    assert [(item.source, item.rule) for item in result.source_replacements] == [
        (source, "sequence.legal")
    ]


@pytest.mark.parametrize("source", ["§§", "§§ foo", "§§ 12, foo BGB"])
def test_malformed_german_plural_paragraph_references_fail_closed(source: str) -> None:
    result = prepare(source, language="de", use_spacy=False)
    assert not any(item.rule == "sequence.legal" for item in result.source_replacements)
    assert "Paragraf" not in result.spoken_text


def test_german_plural_paragraph_reference_obeys_legal_domain() -> None:
    source = "§§ 12, 13 BGB"
    disabled = prepare(
        source,
        language="de",
        use_spacy=False,
        config=PreparationConfig(language="de", disabled_domains={RecognitionDomain.LEGAL}),
    )
    allowed = prepare(
        source,
        language="de",
        use_spacy=False,
        config=PreparationConfig(language="de", allowed_domains={RecognitionDomain.LEGAL}),
    )
    assert disabled.spoken_text == source
    assert allowed.spoken_text.startswith("Paragrafen")


@pytest.mark.parametrize(
    "source",
    [
        "Telefon 030 12345678",
        "Tel. 030 12345678",
        "Telefonnummer 030 12345678",
        "+49 30 12345678",
    ],
)
def test_german_grouped_phone_candidates_keep_typed_ownership(source: str) -> None:
    result = prepare(source, language="de", use_spacy=False)
    assert any(item.rule == "sequence.phone" for item in result.source_replacements)


def test_german_phone_policy_rejects_version_context() -> None:
    result = prepare("Version 030 12345678", language="de", use_spacy=False)
    assert not any(item.rule == "sequence.phone" for item in result.source_replacements)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("25%", "fünfundzwanzig Prozent"),
        ("12,5%", "zwölf Komma fünf Prozent"),
        ("-1,2%", "minus eins Komma zwei Prozent"),
        ("25 %", "fünfundzwanzig Prozent"),
    ],
)
def test_german_percent_uses_shared_typed_renderer(source: str, expected: str) -> None:
    result = prepare(source, language="de", use_spacy=False)
    assert result.spoken_text == expected
    assert any(item.rule == "sequence.percent" for item in result.source_replacements)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("1000000", "eine Million"),
        ("1000000000", "eine Milliarde"),
        ("1000000000000", "eine Billion"),
        ("der 100. Versuch", "der hundertste Versuch"),
        ("am 1000. Tag", "am tausendsten Tag"),
    ],
)
def test_german_scale_boundaries_and_large_ordinals_keep_num2words_contract(
    source: str,
    expected: str,
) -> None:
    assert prepare(source, language="de", use_spacy=False).spoken_text == expected


def test_german_protected_text_is_not_claimed_by_new_regressions() -> None:
    source = "https://example.org/14:30 Uhrzeit and §§ 12, 13 BGB"
    result = prepare(source, language="de", use_spacy=False)
    assert "https://example.org/14:30" in result.spoken_text
    assert any(item.rule == "sequence.legal" for item in result.source_replacements)
