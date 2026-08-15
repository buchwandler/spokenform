import pytest

from spokenform import prepare


def _rules(source: str, *, language: str = "en") -> set[str]:
    result = prepare(source, language=language, use_spacy=False)
    return {item.rule for item in result.source_replacements if item.rule}


@pytest.mark.parametrize(
    ("source", "forbidden"),
    (
        ("3/4 cup", {"en.date", "sequence.time"}),
        ("1/2 full", {"en.date", "sequence.time"}),
        ("4/7 ratio", {"en.date", "sequence.time"}),
        ("version 3.4", {"en.date", "sequence.version"}),
        ("IPv4 192.168.1.1", {"en.date", "sequence.version"}),
    ),
)
def test_dates_do_not_steal_fraction_version_or_ip_shapes(source: str, forbidden: set[str]) -> None:
    assert not _rules(source) & forbidden


def test_time_does_not_steal_scores_references_or_durations() -> None:
    assert "sequence.time" not in _rules("Team won 6:3")
    assert "sequence.time" not in _rules("John 1:16-17")
    assert "sequence.duration" in _rules("duration 2:15:30")


@pytest.mark.parametrize(
    "source",
    [
        "10-7-3",
        "version 3-2-1",
        "Section 3-2-1",
        "room 3-2-1",
    ],
)
def test_ambiguous_numeric_chains_are_not_scores(source: str) -> None:
    result = prepare(source, language="en", use_spacy=False)

    assert not any(item.rule == "sequence.chained-score" for item in result.source_replacements)


@pytest.mark.parametrize("source", ("ISO-1994", "Model 1858", "PIN 1972", "serial 2014-ABC"))
def test_contextual_identifier_shapes_do_not_become_years(source: str) -> None:
    assert "sequence.year" not in _rules(source)


@pytest.mark.parametrize(
    "source",
    (
        "Registration Clerk",
        "Registration: Edgerley",
        "Chief Product Officer",
        "Business Model Canvas",
        "Tag Team",
    ),
)
def test_code_labels_do_not_rewrite_ordinary_prose(source: str) -> None:
    assert prepare(source, language="en", use_spacy=False).spoken_text == source


def test_foreign_text_is_preserved_by_the_core_normalizer() -> None:
    source = "日本語 PlayStation/"
    assert prepare(source, language="en", use_spacy=False).spoken_text == source


def test_abbreviations_delegate_without_stealing_structured_spans() -> None:
    result = prepare("ABC BBC USA IUCN", language="en", use_spacy=False)
    assert {item.rule for item in result.source_replacements} == {
        "abbr:ABC",
        "abbr:BBC",
        "abbr:USA",
        "abbr:IUCN",
    }
    version = prepare("Python 3.9.7", language="en", use_spacy=False)
    assert any(item.rule == "sequence.version" for item in version.source_replacements)


def test_ambiguous_uppercase_art_is_not_guessed_as_an_initialism() -> None:
    source = "He is called ART. ARTs body is from metal."
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == source
    assert not any(
        item.rule
        in {
            "abbr:initialism",
            "abbr:initialism-conservative",
            "abbr:initialism-undotted",
        }
        for item in result.source_replacements
    )

    conservative = prepare(
        source,
        language="en",
        use_spacy=False,
        generic_acronym_mode="conservative_unknown",
    )
    assert conservative.spoken_text == source
