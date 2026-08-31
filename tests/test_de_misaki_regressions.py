"""German regression cases derived from the Misaki review."""

import pytest

from spokenform import PreparationConfig, prepare
from spokenform.config import RecognitionDomain


@pytest.mark.parametrize(
    ("source", "fragment"),
    [
        ("vgl. Abschnitt 2", "vergleiche Abschnitt zwei"),
        ("i.d.R. reicht das", "in der Regel reicht das"),
        ("i. d. R. reicht das", "in der Regel reicht das"),
        ("o.ä. Geräte", "oder ähnliches Geräte"),
        ("o. ä. Geräte", "oder ähnliches Geräte"),
        ("u.U. später", "unter Umständen später"),
        ("u. U. später", "unter Umständen später"),
    ],
)
def test_german_phase01_abbreviations_flow_through_spokenform(source: str, fragment: str) -> None:
    result = prepare(source, language="de", use_spacy=False)
    assert fragment in result.spoken_text
    abbreviation = next(
        item for item in result.source_replacements if item.rule and item.rule.startswith("abbr:")
    )
    assert source[abbreviation.source_start : abbreviation.source_end] == abbreviation.source
    assert (
        result.spoken_text[abbreviation.output_start : abbreviation.output_end]
        == abbreviation.replacement
    )
    assert result.offset_map is not None
    assert result.offset_map.map_source_span(
        abbreviation.source_start, abbreviation.source_end
    ) == (abbreviation.output_start, abbreviation.output_end)


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
    "source",
    [
        "v14:30",
        "x14:30",
        "14:30beta",
        "ID14:30",
        "foo14:30bar",
        "x24.12.2024",
        "24.12.2024abc",
        "ID24.12.2024",
        "v24-12-2024",
        "24-12-2024beta",
    ],
)
def test_german_structured_dates_and_times_reject_identifier_adjacency(source: str) -> None:
    result = prepare(source, language="de", use_spacy=False)
    assert not any(
        item.rule in {"de.time", "de.time-range", "de.date", "de.date-range", "de.text-date"}
        for item in result.source_replacements
    )


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


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Im Jahr 1989.", "Im Jahr neunzehnhundertneunundachtzig."),
        ("Im Jahr 1900.", "Im Jahr neunzehnhundert."),
        ("Im Jahr 2024.", "Im Jahr zweitausendvierundzwanzig."),
        ("Im Jahr 2000.", "Im Jahr zweitausend."),
        ("im Jahre 1989", "im Jahre neunzehnhundertneunundachtzig"),
        ("Jahr 2024", "Jahr zweitausendvierundzwanzig"),
        ("das Jahr 2024", "das Jahr zweitausendvierundzwanzig"),
    ],
)
def test_german_contextual_year_uses_year_renderer(source: str, expected: str) -> None:
    result = prepare(source, language="de", use_spacy=False)
    assert result.spoken_text == expected
    replacements = [item for item in result.source_replacements if item.rule == "de.year"]
    assert len(replacements) == 1
    replacement = replacements[0]
    assert replacement.source in {"1989", "1900", "2024", "2000"}
    assert source[replacement.source_start : replacement.source_end] == replacement.source
    assert (
        result.spoken_text[replacement.output_start : replacement.output_end]
        == replacement.replacement
    )
    assert result.offset_map is not None
    assert result.offset_map.map_source_span(replacement.source_start, replacement.source_end) == (
        replacement.output_start,
        replacement.output_end,
    )


@pytest.mark.parametrize(
    "source",
    [
        "Version 1989",
        "Modell 1989",
        "Artikel 1989",
        "ID 1989",
        "PIN 1989",
        "Port 1989",
        "Build 1989",
    ],
)
def test_german_contextual_year_rejects_non_temporal_contexts(source: str) -> None:
    result = prepare(source, language="de", use_spacy=False)
    assert not any(item.rule == "de.year" for item in result.source_replacements)


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


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("€1", "ein Euro"),
        ("1 EUR", "ein Euro"),
        ("€2", "zwei Euro"),
        ("€0,01", "null Euro ein Cent"),
        ("€0,02", "null Euro zwei Cent"),
        ("€1,01", "ein Euro ein Cent"),
        ("€2,01", "zwei Euro ein Cent"),
        ("€2,02", "zwei Euro zwei Cent"),
        ("€9,99", "neun Euro neunundneunzig Cent"),
        ("9,99 EUR", "neun Euro neunundneunzig Cent"),
        ("-9,99 EUR", "minus neun Euro neunundneunzig Cent"),
        ("CHF 12,80", "zwölf Komma acht null Schweizer Franken"),
    ],
)
def test_german_currency_grammar(source: str, expected: str) -> None:
    result = prepare(source, language="de", use_spacy=False)
    assert result.spoken_text == expected


def test_german_currency_cent_replacement_maps_exactly() -> None:
    source = "Preis: €1,01"
    result = prepare(source, language="de", use_spacy=False)
    replacement = next(item for item in result.source_replacements if item.rule == "de.currency")
    assert (
        source[replacement.source_start : replacement.source_end] == replacement.source == "€1,01"
    )
    assert (
        result.spoken_text[replacement.output_start : replacement.output_end]
        == replacement.replacement
    )
    assert replacement.replacement == "ein Euro ein Cent"
    assert result.offset_map is not None
    assert result.offset_map.map_source_span(replacement.source_start, replacement.source_end) == (
        replacement.output_start,
        replacement.output_end,
    )


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


def test_german_unicode_whitespace_and_downstream_typography_ownership() -> None:
    assert (
        prepare(
            "Äpfel, Österreich, Überraschung, Größe", language="de", use_spacy=False
        ).spoken_text
        == "Äpfel, Österreich, Überraschung, Größe"
    )
    assert prepare("Hallo\u00a0Welt", language="de", use_spacy=False).spoken_text == "Hallo Welt"
    assert prepare("Hallo   Welt", language="de", use_spacy=False).spoken_text == "Hallo Welt"

    quoted = prepare("„Euro“ — Größe", language="de", use_spacy=False)
    assert quoted.spoken_text == "„Euro“ — Größe"
    assert not quoted.source_replacements

    company = prepare("GmbH", language="de", use_spacy=False)
    assert "Gesellschaft mit beschränkter Haftung" not in company.spoken_text
