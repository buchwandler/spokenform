from spokenform import prepare


def test_math_specialist_requires_expression_shape() -> None:
    result = prepare("2+2=4", language="en", use_spacy=False)
    assert result.spoken_text == "two plus two equals four"
    assert any(item.rule == "sequence.math" for item in result.source_replacements)
    assert prepare("ordinary text", language="en", use_spacy=False).spoken_text == "ordinary text"


def test_music_specialist_requires_music_context() -> None:
    result = prepare("chord C# and key Bb", language="en", use_spacy=False)
    assert result.spoken_text == "chord c sharp and key b flat"
    assert sum(item.rule == "sequence.music" for item in result.source_replacements) == 2


def test_biology_specialist_claims_controlled_genus_species_shape() -> None:
    result = prepare("E. coli and H2O", language="en", use_spacy=False)
    assert result.spoken_text == "e coli and h two o"
    assert any(item.rule == "sequence.biology" for item in result.source_replacements)
    assert any(item.rule == "sequence.formula" for item in result.source_replacements)


def test_sports_score_beats_math_minus_expression() -> None:
    result = prepare("final 3-2", language="en", use_spacy=False)
    assert result.spoken_text == "final three to two"
    assert any(item.rule == "sequence.sports" for item in result.source_replacements)
    assert not any(item.rule == "sequence.math" for item in result.source_replacements)
