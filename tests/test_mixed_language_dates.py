from spokenform import prepare


def test_german_mixed_language_dates_use_the_german_date_renderer() -> None:
    assert prepare(
        "Die Lieferung erfolgt bis 31st Dec 2024.", language="de", use_spacy=False
    ).spoken_text == (
        "Die Lieferung erfolgt bis einunddreißigsten Dezember zweitausendvierundzwanzig."
    )
    assert prepare("Die Prüfung ist am 20th May.", language="de", use_spacy=False).spoken_text == (
        "Die Prüfung ist am zwanzigsten Mai."
    )


def test_mixed_language_date_requires_valid_ordinal_and_calendar_shape() -> None:
    negatives = (
        "Model 31st Dec 2024",
        "The 31st Dec 2024 report",
        "Die Lieferung erfolgt bis 31th Dec 2024.",
    )
    for source in negatives:
        result = prepare(source, language="de", use_spacy=False)
        assert "mixed-text-date" not in {
            replacement.rule for replacement in result.source_replacements
        }


def test_mixed_language_date_has_named_date_precedence_and_provenance() -> None:
    result = prepare("bis 31st Dec 2024", language="de", use_spacy=False)
    replacement = next(
        item for item in result.source_replacements if item.rule == "de.mixed-text-date"
    )
    assert replacement.source == "31st Dec 2024"
    assert replacement.source_start == 4
