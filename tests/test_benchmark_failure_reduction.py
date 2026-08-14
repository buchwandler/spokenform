"""Focused fixtures for the benchmark-failure reduction brief."""

from spokenform import PreparationConfig, prepare

PRODUCT_FALSE_POSITIVES = (
    "Registration Clerk",
    "Registration: Edgerley",
    "Chief Product Officer",
    "Business Model Canvas",
    "Tag Team",
)

TEXT_DATE_FALSE_POSITIVES = (
    "105 mares",
    "314 marches",
    "12 market",
    "11 maybe",
)

TEXT_DATE_POSITIVES = (
    "5 Mar",
    "5 Mar.",
    "5 March",
    "17 February 2009",
    "September 5",
    "September 5, 2020",
)

AMBIGUOUS_UNIT_FIXTURES = (
    "1992 in Clareen",
    "1977 in Istanbul",
    "H 5 N 1",
    "Part 6 A",
)

SEMANTIC_FIXTURES = (
    "before 1919",
    "from 1991 to 2014",
    "between 1990 and 2000",
    "1618-1648",
    "1663-1735",
    "IUCN",
    "BBC",
    "PDF",
    "ISBN",
    "CEO",
    "U.S.",
    "ABC",
    "AAPL",
    "NASA",
    "FILM GETS TOP PRIZE",
    "v3.1.4",
    "2.5.1",
    "Python 3.9.7",
    "Firmware v3.2.1",
    "https://example.com/v1.2.3",
    "Article IX",
    "King Henry VIII",
    "Act III, Scene IV",
    "MMXXIV",
    "IV",
    "PIN 4711",
    "Matrikelnummer 1234567",
    "FL-ABC12",
    "BMW E46",
    "WH-1000XM4",
    "5:3",
    "6:3, 6:2",
    "10-7-3",
    "2:15:30",
    "HPV-16",
    "DENV-2",
)


def _rules(source: str) -> tuple[str, ...]:
    result = prepare(source, language="en", use_spacy=False)
    return tuple(item.rule for item in result.source_replacements if item.rule)


def test_brief_safety_fixtures_do_not_claim_lexical_product_phrases() -> None:
    for source in PRODUCT_FALSE_POSITIVES:
        assert "sequence.product" not in _rules(source), source


def test_brief_text_date_fixtures_respect_lexical_boundaries() -> None:
    for source in TEXT_DATE_FALSE_POSITIVES:
        assert not any(rule.startswith("en.date") for rule in _rules(source)), source


def test_brief_text_date_positive_fixtures_remain_claimable() -> None:
    for source in TEXT_DATE_POSITIVES:
        assert any(rule.startswith("en.date") for rule in _rules(source)), source


def test_brief_ambiguous_units_do_not_steal_typed_context() -> None:
    for source in AMBIGUOUS_UNIT_FIXTURES:
        assert "en.quantity" not in _rules(source), source


def test_brief_semantic_fixture_inventory_is_nonempty() -> None:
    assert len(SEMANTIC_FIXTURES) >= 30


def test_brief_contextual_years_and_historical_ranges_use_year_rendering() -> None:
    cases = {
        "before 1919": "before nineteen nineteen",
        "from 1991 to 2014": "from nineteen ninety one to twenty fourteen",
        "between 1990 and 2000": "between nineteen ninety and two thousand",
        "International Exhibitions of 1862, 1867 and 1871": (
            "International Exhibitions of eighteen sixty two, "
            "eighteen sixty seven and eighteen seventy one"
        ),
        "1618-1648": "sixteen eighteen to sixteen forty eight",
        "1663-1735": "sixteen sixty three to seventeen thirty five",
    }
    for source, expected in cases.items():
        assert prepare(source, language="en", use_spacy=False).spoken_text == expected


def test_brief_long_cardinal_mode_is_explicit_and_preserves_default() -> None:
    source = "844361"
    assert prepare(source, language="en", use_spacy=False).spoken_text == source
    assert prepare(
        source, language="en", use_spacy=False, long_number_mode="cardinal"
    ).spoken_text == ("eight hundred forty four thousand three hundred sixty one")
    configured = prepare(
        source,
        config=PreparationConfig(language="en", use_spacy=False, long_number_mode="cardinal"),
    )
    assert configured.spoken_text == "eight hundred forty four thousand three hundred sixty one"


def test_contextual_long_number_mode_requires_quantity_evidence() -> None:
    assert prepare(
        "there are 844361 items",
        language="en",
        use_spacy=False,
        long_number_mode="contextual",
    ).spoken_text == "there are eight hundred forty four thousand three hundred sixty one items"
    for source in ("844361", "(844361)", "account 844361", "0001234"):
        result = prepare(
            source,
            language="en",
            use_spacy=False,
            long_number_mode="contextual",
        )
        assert source in result.spoken_text
    pin_result = prepare(
        "PIN 844361",
        language="en",
        use_spacy=False,
        long_number_mode="contextual",
    )
    assert "eight four four three six one" in pin_result.spoken_text


def test_registered_acronym_spelling_is_independent_from_generic_policy() -> None:
    expanded = prepare(
        "CEO D.C. MIT ABC",
        language="en",
        use_spacy=False,
        registered_acronym_mode="expand",
        generic_acronym_mode="spell_unknown",
        generic_acronym_case="lower",
    )
    spelled = prepare(
        "CEO D.C. MIT ABC",
        language="en",
        use_spacy=False,
        registered_acronym_mode="spell",
        generic_acronym_mode="spell_unknown",
        generic_acronym_case="lower",
    )
    assert (
        expanded.spoken_text
        == "chief executive officer D C Massachusetts Institute of Technology A B C"
    )
    assert spelled.spoken_text == "c e o d c m i t a b c"


def test_conservative_unknown_initialisms_preserve_lexical_and_headline_text() -> None:
    result = prepare(
        "NASA NGO",
        language="en",
        use_spacy=False,
        generic_acronym_mode="conservative_unknown",
        generic_acronym_case="lower",
    )
    assert result.spoken_text == "NASA n g o"
    headline = prepare(
        "WORLD FIRST FILM GETS TOP PRIZE AT CANNES",
        language="en",
        use_spacy=False,
        generic_acronym_mode="conservative_unknown",
    )
    assert headline.spoken_text == "WORLD FIRST FILM GETS TOP PRIZE AT CANNES"


def test_conservative_unknown_runs_after_structured_reservation() -> None:
    result = prepare(
        "Python 3.9.7 NGO",
        language="en",
        use_spacy=False,
        generic_acronym_mode="conservative_unknown",
        generic_acronym_case="lower",
    )
    assert "Python 3.9.7" not in result.spoken_text
    assert "dot" in result.spoken_text
    assert result.spoken_text.endswith("n g o")


def test_contextual_parenthesized_initialisms_and_roman_numerals() -> None:
    result = prepare(
        "Apple (AAPL); stock (T); Article IX; Act III, Scene IV; King Henry VIII.",
        language="en",
        use_spacy=False,
    )
    assert result.spoken_text == (
        "Apple (A A P L); stock (T); Article nine; Act three, Scene four; King Henry the eighth."
    )
    assert any(
        item.rule == "sequence.parenthesized-initialism" for item in result.source_replacements
    )
    assert sum(item.rule == "sequence.roman" for item in result.source_replacements) == 4
    assert prepare("IV", language="en", use_spacy=False).spoken_text == "IV"


def test_typed_code_digit_modes_distinguish_identifiers_and_products() -> None:
    assert prepare("PIN 4711", language="en", use_spacy=False).spoken_text == (
        "P I N four seven one one"
    )
    assert prepare("BMW E46", language="en", use_spacy=False).spoken_text == "BMW E forty-six"
    assert prepare("WH-1000XM4", language="en", use_spacy=False).spoken_text == (
        "W H one thousand X M four"
    )
    assert prepare("ABC123", language="en", use_spacy=False).spoken_text == "ABC123"


def test_scores_and_durations_use_specific_precedence() -> None:
    assert prepare("5:3", language="en", use_spacy=False).spoken_text == "five to three"
    assert prepare("final 25:23", language="en", use_spacy=False).spoken_text == (
        "final twenty-five to twenty-three"
    )
    repeated = prepare("6:3, 6:2", language="en", use_spacy=False)
    assert repeated.spoken_text == "six to three, six to two"
    assert sum(item.rule == "sequence.sports" for item in repeated.source_replacements) == 2
    chained = prepare("10-7-3", language="en", use_spacy=False)
    assert chained.spoken_text == "ten to seven to three"
    assert any(item.rule == "sequence.chained-score" for item in chained.source_replacements)
    duration = prepare("2:15:30", language="en", use_spacy=False)
    assert duration.spoken_text == "two hours fifteen minutes thirty seconds"
    assert any(item.rule == "sequence.duration" for item in duration.source_replacements)
    assert not any(item.rule == "en.time" for item in duration.source_replacements)


def test_reviewed_biomedical_codes_beat_generic_code_claims() -> None:
    for source in ("HPV-16", "DENV-2", "HPV", "HBV", "HIV", "EBV", "MMR", "BRCA2"):
        result = prepare(source, language="en", use_spacy=False)
        assert any(item.rule == "sequence.biomedical" for item in result.source_replacements), (
            source
        )
    ordinary = prepare("Model ABC123", language="en", use_spacy=False)
    assert not any(item.rule == "sequence.biomedical" for item in ordinary.source_replacements)


def test_version_separators_are_semantic_points_in_every_locale() -> None:
    for language in ("en", "es", "it", "fr", "de"):
        result = prepare(
            "Python 3.9.7", language=language, use_spacy=False, normalize_literals=True
        )
        assert "3.9.7" not in result.spoken_text
        assert any(item.rule == "sequence.version" for item in result.source_replacements)
        assert all(word not in result.spoken_text for word in ("coma", "virgola", "virgule"))
