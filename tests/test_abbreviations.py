from abbr2words import abbr2words_with_replacements

from spokenform import PreparationConfig, convert_abbr_replacements, prepare


def test_abbreviation_stage_uses_exact_replacements_and_metadata() -> None:
    source = "Prof. Prof. Dr."
    dependency_result = abbr2words_with_replacements(source, lang="de")
    result = prepare(
        source,
        config=PreparationConfig(
            language="de",
            expand_structured=False,
            expand_numbers=False,
            normalize_whitespace=False,
            use_spacy=False,
        ),
    )

    stage = next(stage for stage in result.stages if stage.name == "abbreviations")
    converted = convert_abbr_replacements(
        dependency_result.replacements,
        language="de",
    )

    assert result.spoken_text == dependency_result.text
    assert [edit.source for edit in stage.mapped_edits] == ["Prof.", "Prof.", "Dr."]
    assert [edit.replacement for edit in stage.mapped_edits] == [
        item.text for item in dependency_result.replacements
    ]
    assert [item.kind for item in converted] == [
        item.kind for item in dependency_result.replacements
    ]
    assert [edit.language for edit in stage.mapped_edits] == ["de", "de", "de"]
    assert all(edit.rule for edit in stage.mapped_edits)


def test_abbreviation_expansion_does_not_depend_on_repeated_substrings() -> None:
    source = "Dr. Dr."
    result = prepare(
        source,
        language="de",
        expand_structured=False,
        expand_numbers=False,
        normalize_whitespace=False,
        use_spacy=False,
    )

    assert result.spoken_text == "Doktor Doktor"
    stage = next(stage for stage in result.stages if stage.name == "abbreviations")
    assert [(edit.source_start, edit.source_end) for edit in stage.mapped_edits] == [
        (0, 3),
        (4, 7),
    ]
