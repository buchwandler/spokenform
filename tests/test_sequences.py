import pytest

from spokenform import prepare
from spokenform.language import SUPPORTED_BASE_LANGUAGES
from spokenform.sequences import SequenceRenderPolicy, render_letters, render_sequence


@pytest.mark.parametrize("language", sorted(SUPPORTED_BASE_LANGUAGES))
def test_every_supported_language_renders_ascii_letters_without_index_errors(language: str) -> None:
    rendered = render_letters(
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ", language=language
    )
    assert rendered
    assert "IndexError" not in rendered


@pytest.mark.parametrize("language", sorted(SUPPORTED_BASE_LANGUAGES))
def test_mixed_identifier_rendering_is_total(language: str) -> None:
    rendered = render_sequence("XYZ-2024/Abc", language=language)
    assert rendered


def test_sequence_renderer_advances_past_whitespace() -> None:
    assert render_sequence("A B", language="de") == "A B"


def test_german_legal_reference_with_whitespace_completes() -> None:
    result = prepare("Nach Art. 1 Abs. 1 GG.", language="de_DE", use_spacy=False)
    assert result.spoken_text == "Nach Artikel eins Absatz eins G G."


def test_sequence_policy_can_keep_alpha_runs_lexical() -> None:
    policy = SequenceRenderPolicy(alpha_mode="lexical", digit_mode="digitwise")
    assert render_sequence("TravelTips_2024", language="en", policy=policy) == (
        "TravelTips underscore two zero two four"
    )


def test_sequence_alpha_modes_are_distinct() -> None:
    assert (
        render_sequence("ISBN", language="es", policy=SequenceRenderPolicy(alpha_mode="lexical"))
        == "ISBN"
    )
    assert (
        render_sequence(
            "ISBN", language="es", policy=SequenceRenderPolicy(alpha_mode="grapheme_spaced")
        )
        == "I S B N"
    )
    assert (
        render_sequence(
            "ISBN", language="es", policy=SequenceRenderPolicy(alpha_mode="spoken_letter_names")
        )
        == "i ese be ene"
    )


def test_hashtag_and_mention_rendering_is_lexical() -> None:
    assert prepare("#TravelTips @JeanDupont", language="en", use_spacy=False).spoken_text == (
        "hashtag Travel Tips at Jean Dupont"
    )
    assert (
        prepare("#vacanze2024", language="it", use_spacy=False).spoken_text
        == "hashtag vacanze duemilaventiquattro"
    )
    assert (
        prepare("#Été2024", language="fr", use_spacy=False).spoken_text
        == "hashtag Été deux mille vingt-quatre"
    )


def test_opaque_short_handles_use_letterwise_rendering() -> None:
    assert prepare("#API2", language="en", use_spacy=False).spoken_text == "hashtag a p i two"
    assert prepare("#E.", language="en", use_spacy=False).spoken_text == "hashtag e."


def test_coordinates_support_integer_precision_and_direction_words() -> None:
    assert prepare("90° N", language="en", use_spacy=False).spoken_text == "ninety degrees north"
    assert prepare("0°", language="de", use_spacy=False).spoken_text == "null Grad"
    assert prepare("12.3456° E", language="de", use_spacy=False).spoken_text == (
        "zwölf Komma drei vier fünf sechs Grad Ost"
    )


def test_coordinates_fail_closed_when_directional_ranges_are_invalid() -> None:
    assert prepare("91° N", language="en", use_spacy=False).spoken_text == "ninety one° N"
    assert (
        prepare("181° E", language="en", use_spacy=False).spoken_text == "one hundred eighty one° E"
    )


def test_isbn_and_sports_scores_use_category_specific_policies() -> None:
    isbn = prepare("ISBN 978-3-16-148410-0", language="en", use_spacy=False)
    assert (
        isbn.spoken_text
        == "I S B N nine seven eight three one six one four eight four one zero zero"
    )
    assert any(item.rule == "sequence.isbn" for item in isbn.source_replacements)

    assert prepare("final 3-2", language="en", use_spacy=False).spoken_text == (
        "final three to two"
    )
    assert prepare("punteggio 3 a 0", language="it", use_spacy=False).spoken_text == (
        "punteggio tre a zero"
    )
    assert prepare("3-2", language="en", use_spacy=False).spoken_text == "three-two"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("I initiate in 3-2-1.", "I initiate in three two one."),
        ("We launch in 5-4-3-2-1.", "We launch in five four three two one."),
        ("Starting in 3-2-1.", "Starting in three two one."),
        ("Countdown 3-2-1.", "Countdown three two one."),
        ("Counting down from 3-2-1.", "Counting down from three two one."),
    ],
)
def test_english_contextual_countdowns(source: str, expected: str) -> None:
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == expected
    assert sum(item.rule == "sequence.countdown" for item in result.source_replacements) == 1
    assert not any(
        item.rule in {"sequence.chained-score", "sequence.sports", "sequence.numeric-range"}
        for item in result.source_replacements
    )


def test_contextual_chained_scores_remain_scores() -> None:
    for source, expected in (
        ("final 10-7-3", "final ten to seven to three"),
        ("score 3-2-1", "score three to two to one"),
    ):
        result = prepare(source, language="en", use_spacy=False)
        assert result.spoken_text == expected
        assert any(item.rule == "sequence.chained-score" for item in result.source_replacements)


def test_fraction_and_abbreviation_policies_are_high_confidence_only() -> None:
    assert prepare("½ ⅝", language="it", use_spacy=False).spoken_text == ("un mezzo cinque ottavi")
    assert prepare("NASA BND API", language="en", use_spacy=False).spoken_text == ("NASA BND API")
    protected = prepare("https://example.org/v1.2.3", language="en", use_spacy=False)
    assert protected.spoken_text == "https://example.org/v1.2.3"


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("⅕", "one fifth"),
        ("⅖", "two fifths"),
        ("⅗", "three fifths"),
        ("⅘", "four fifths"),
        ("⅙", "one sixth"),
        ("⅚", "five sixths"),
        ("1⅕", "one and one fifth"),
        ("2⅙", "two and one sixth"),
    ],
)
def test_unicode_fifths_and_sixths_use_generic_fraction_rendering(
    source: str, expected: str
) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert result.spoken_text == expected
    assert [item.rule for item in result.source_replacements] == ["sequence.fraction"]
    replacement = result.source_replacements[0]
    assert replacement.source == source
    assert result.map_source_span(replacement.source_start, replacement.source_end) == (
        replacement.output_start,
        replacement.output_end,
    )
    assert (
        prepare(result.spoken_text, language="en", use_spacy=False).spoken_text
        == result.spoken_text
    )


@pytest.mark.parametrize("language", ["de", "es", "fr", "it"])
def test_unicode_fifths_and_sixths_are_supported_by_existing_denominator_vocab(
    language: str,
) -> None:
    result = prepare("⅕ ⅖ ⅙ ⅚", language=language, use_spacy=False)
    assert all(word not in result.spoken_text for word in ("⅕", "⅖", "⅙", "⅚"))
    assert (
        len([item for item in result.source_replacements if item.rule == "sequence.fraction"]) == 4
    )


def test_unknown_uppercase_prose_is_preserved() -> None:
    result = prepare("AAPL", language="en", use_spacy=False)
    assert result.spoken_text == "AAPL"
    assert not result.source_replacements


def test_generic_acronym_mode_and_case_are_independent() -> None:
    known_upper = prepare("ABC AAPL NASA API", language="en", use_spacy=False)
    known_lower = prepare(
        "ABC AAPL NASA API",
        language="en",
        use_spacy=False,
        generic_acronym_case="lower",
    )
    spelled_upper = prepare(
        "ABC AAPL NASA API",
        language="en",
        use_spacy=False,
        generic_acronym_mode="spell_unknown",
        generic_acronym_case="upper",
    )
    spelled_lower = prepare(
        "ABC AAPL NASA API",
        language="en",
        use_spacy=False,
        generic_acronym_mode="spell_unknown",
        generic_acronym_case="lower",
    )

    assert known_upper.spoken_text == "A B C AAPL NASA API"
    assert known_lower.spoken_text == "A B C AAPL NASA API"
    assert spelled_upper.spoken_text == "A B C A A P L N A S A A P I"
    assert spelled_lower.spoken_text == "A B C a a p l n a s a a p i"
    assert any(
        item.rule == "abbr:initialism-undotted" for item in spelled_upper.source_replacements
    )


def test_contextual_tickers_are_typed_and_not_generic_acronyms() -> None:
    result = prepare(
        "The ticker is MSFT. The stock symbol is GOOG.", language="en", use_spacy=False
    )
    ticker_rules = [item for item in result.source_replacements if item.rule == "sequence.ticker"]
    assert result.spoken_text == "The ticker is M S F T. The stock symbol is G O O G."
    assert [item.source for item in ticker_rules] == ["MSFT", "GOOG"]


def test_typed_identifier_labels_use_contextual_code_policies() -> None:
    for source, expected in (
        ("PIN 4711", "P I N four seven one one"),
        (
            "VIN-1234567890ABCDEF",
            "V I N one two three four five six seven eight nine zero A B C D E F",
        ),
        ("License plate FL-ABC12", "license plate F L A B C one two"),
        ("Matrikelnummer 1234567", "Matrikelnummer one two three four five six seven"),
    ):
        result = prepare(source, language="en", use_spacy=False)
        assert result.spoken_text == expected
        assert any(
            item.rule in {"sequence.product", "sequence.plate", "sequence.vin"}
            for item in result.source_replacements
        )


def test_product_code_supports_mixed_suffixes_without_claiming_words() -> None:
    positive = prepare("WH-1000XM4", language="en", use_spacy=False)
    negative = prepare("LaCrosse McGill VanRullen", language="en", use_spacy=False)
    assert any(item.rule == "sequence.product" for item in positive.source_replacements)
    assert "LaCrosse McGill VanRullen" in negative.spoken_text


@pytest.mark.parametrize(
    ("language", "source", "expected"),
    [
        ("en", "1/2", "one half"),
        ("de", "3/7", "drei Siebtel"),
        ("es", "1 1/2", "Uno y un medio"),
        ("fr", "3/7", "trois septièmes"),
        ("it", "1½", "uno e un mezzo"),
    ],
)
def test_slash_and_mixed_fractions_are_semantic(language: str, source: str, expected: str) -> None:
    result = prepare(source, language=language, use_spacy=False)
    assert result.spoken_text == expected
    assert any(item.rule == "sequence.fraction" for item in result.source_replacements)


def test_fraction_does_not_claim_url_or_full_date_shape() -> None:
    url = prepare("https://example.org/1/2", language="en", use_spacy=False)
    assert url.spoken_text == "https://example.org/1/2"
    date = prepare("2025/03/15", language="en", use_spacy=False)
    assert not any(item.rule == "sequence.fraction" for item in date.source_replacements)
    assert not any(item.rule == "sequence.phone" for item in date.source_replacements)


def test_year_and_numeric_ranges_are_contextual_and_precedence_safe() -> None:
    year = prepare("Ayers, Andrew (2004).", language="en", use_spacy=False)
    assert year.spoken_text == "Ayers, Andrew (two thousand four)."
    assert any(item.rule == "sequence.year" for item in year.source_replacements)

    historical = prepare("1946-1975", language="en", use_spacy=False)
    assert historical.spoken_text == "nineteen forty six to nineteen seventy five"
    assert any(item.rule == "sequence.year-range" for item in historical.source_replacements)

    for source, expected in (
        ("33-38", "thirty three to thirty eight"),
        ("93-102", "ninety three to one hundred two"),
        ("1048-1049", "one thousand forty eight to one thousand forty nine"),
    ):
        result = prepare(source, language="en", use_spacy=False)
        assert result.spoken_text == expected
        assert any(item.rule == "sequence.numeric-range" for item in result.source_replacements)

    for source in ("v3.1.4", "978-3-16-148410-0", "2024-05-31", "X5Y-7890", "-5"):
        result = prepare(source, language="en", use_spacy=False)
        assert not any("range" in (item.rule or "") for item in result.source_replacements)


def test_unowned_dash_and_em_dash_text_remains_source_aligned() -> None:
    for source in ("Sure Love—Single", "Sure Love - Single", "A—B"):
        result = prepare(source, language="en", use_spacy=False)
        assert result.spoken_text == source
        assert all(stage.before == stage.after for stage in result.stages)


def test_numeric_benchmark_contexts_use_category_specific_renderers() -> None:
    assert prepare("The team won 7-0.", language="en", use_spacy=False).spoken_text == (
        "The team won seven to zero."
    )
    assert prepare("Die Basketballer gewannen 102:98.", language="de", use_spacy=False).spoken_text == (
        "Die Basketballer gewannen einhundertzwei zu achtundneunzig."
    )
    assert prepare(
        "ISBN 978-3-16-148410-0", language="es_MX", use_spacy=False
    ).spoken_text == (
        "I S B N nueve siete ocho, guión tres, guión uno seis, guión uno cuatro ocho cuatro uno cero, guión cero"
    )
    assert prepare("Necesito 1/2 litro", language="es_MX", use_spacy=False).spoken_text == (
        "Necesito medio litro"
    )
