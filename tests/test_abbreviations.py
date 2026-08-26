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

    assert result.spoken_text == "Professor Professor Doktor"
    assert [edit.source for edit in stage.mapped_edits] == ["Prof.", "Prof.", "Dr."]
    assert [edit.replacement for edit in stage.mapped_edits] == [
        item.text.rstrip(".") for item in dependency_result.replacements
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


def test_abbreviation_stage_never_needs_diff(monkeypatch) -> None:
    import spokenform.api as api

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("abbreviation stage must use dependency replacements")

    monkeypatch.setattr(api, "replacements_from_diff", forbidden)
    result = prepare(
        "Prof. Klein",
        language="de",
        expand_structured=False,
        expand_numbers=False,
        normalize_whitespace=False,
        use_spacy=False,
    )

    stage = next(item for item in result.stages if item.name == "abbreviations")
    assert stage.mapped_edits


def test_abbreviation_metadata_uses_public_dependency_contract() -> None:
    dependency_item = abbr2words_with_replacements("Prof. Klein", lang="de").replacements[0]
    converted_item = convert_abbr_replacements((dependency_item,), language="de")[0]

    assert converted_item.rule == dependency_item.rule_id
    assert converted_item.kind == dependency_item.kind
    assert converted_item.language == dependency_item.language
