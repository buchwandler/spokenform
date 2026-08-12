from spokenform import prepare


def test_math_specialist_requires_expression_shape() -> None:
    result = prepare("2+2=4", language="en", use_spacy=False)
    assert result.spoken_text == "two plus two equals four"
    assert any(item.rule == "sequence.math" for item in result.source_replacements)
    assert prepare("ordinary text", language="en", use_spacy=False).spoken_text == "ordinary text"


def test_math_specialist_covers_extended_expression_tokens() -> None:
    cases = {
        "x² + y² = z²": "x squared plus y squared equals z squared",
        "2³ = 8": "two cubed equals eight",
        "π ≈ 3.14": "pi is approximately three point one four",
        "Δy/Δx": "delta y over delta x",
        "5 ≠ 3": "five does not equal three",
        "|−5| = 5": "absolute value of minus five equals five",
    }
    for source, expected in cases.items():
        result = prepare(source, language="en", use_spacy=False)
        assert result.spoken_text == expected
        assert any(item.rule == "sequence.math" for item in result.source_replacements)


def test_music_specialist_requires_music_context() -> None:
    result = prepare("chord C# and key Bb", language="en", use_spacy=False)
    assert result.spoken_text == "chord c sharp and key b flat"
    assert sum(item.rule == "sequence.music" for item in result.source_replacements) == 2


def test_biology_specialist_claims_controlled_genus_species_shape() -> None:
    result = prepare("E. coli and H2O", language="en", use_spacy=False)
    assert result.spoken_text == "e coli and H two O"
    assert any(item.rule == "sequence.biology" for item in result.source_replacements)
    assert any(item.rule == "sequence.formula" for item in result.source_replacements)


def test_contextual_roman_and_greek_symbol_rendering_are_typed() -> None:
    assert prepare("George VI.", language="en", use_spacy=False).spoken_text == (
        "George the sixth."
    )
    assert prepare("Año MMXXIV.", language="es", use_spacy=False).spoken_text == (
        "Año dos mil veinticuatro."
    )
    greek = prepare("θ^2 = 1", language="en", use_spacy=False)
    assert greek.spoken_text == "theta to the power of two equals one"
    assert any(item.rule == "sequence.math" for item in greek.source_replacements)


def test_biomedical_specialist_handles_codes_without_global_alphanumeric_claims() -> None:
    cases = {
        "MERS": "Mers",
        "COVID-19": "covid nineteen",
        "SARS-CoV-2": "Sars Cov two",
        "BRCA2": "b r c a two",
        "TP53": "t p five three",
        "pUC19": "p u c one nine",
        "CRF07_BC": "c r f zero seven b c",
        "variant B.1.1.7": "variant b point one point one point seven",
    }
    for source, expected in cases.items():
        result = prepare(source, language="en", use_spacy=False)
        assert result.spoken_text == expected
        assert any(item.rule == "sequence.biomedical" for item in result.source_replacements)

    ordinary = prepare("Model ABC123", language="en", use_spacy=False)
    assert not any(item.rule == "sequence.biomedical" for item in ordinary.source_replacements)


def test_sports_score_beats_math_minus_expression() -> None:
    result = prepare("final 3-2", language="en", use_spacy=False)
    assert result.spoken_text == "final three to two"
    assert any(item.rule == "sequence.sports" for item in result.source_replacements)
    assert not any(item.rule == "sequence.math" for item in result.source_replacements)


def test_biology_and_math_specialists_fail_closed_on_abbreviations_and_codes() -> None:
    for source in ("z.B. genannten", "M. et Mme", "M. est arrivé"):
        result = prepare(source, language="de", use_spacy=False)
        assert not any(item.rule == "sequence.biology" for item in result.source_replacements)

    result = prepare("M-789-123", language="en", use_spacy=False)
    assert not any(item.rule == "sequence.math" for item in result.source_replacements)


def test_math_and_music_words_follow_locale_without_promoting_literals() -> None:
    assert prepare("2+2=4", language="de", use_spacy=False).spoken_text == (
        "zwei plus zwei gleich vier"
    )
    assert prepare("chord C#", language="fr", use_spacy=False).spoken_text == ("chord cé dièse")
