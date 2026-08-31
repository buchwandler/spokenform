import pytest

from spokenform import (
    GlossaryEntry,
    PreparationConfig,
    SpeechProfile,
    TokenAnnotation,
    add_abbreviation,
    prepare,
    prepare_for_kokorog2p,
    reset_abbreviations,
)


def _lexical_prepare(text: str, profile: SpeechProfile, **kwargs: object):
    return prepare(
        text,
        profile=profile,
        use_spacy=False,
        expand_structured=False,
        expand_numbers=False,
        normalize_whitespace=False,
        **kwargs,
    )


MILITARY = SpeechProfile(
    "military-en",
    glossary=(
        GlossaryEntry("AAR", "after-action review"),
        GlossaryEntry("AO", "area of operations", read_as="letters"),
        GlossaryEntry("AAA", "anti-aircraft artillery", read_as="custom", spoken_form="Triple A"),
    ),
)


def test_profile_mixes_long_form_letters_and_custom() -> None:
    result = _lexical_prepare("AAR AO AAA", MILITARY)
    assert result.spoken_text == "after-action review A O Triple A"


def test_aliases_use_long_form_and_source_spelling() -> None:
    profile = SpeechProfile(
        "aliases",
        glossary=(
            GlossaryEntry("AAR", "after-action review", aliases=("A.A.R.",)),
            GlossaryEntry("AO", "area of operations", read_as="letters", aliases=("A.O.",)),
            GlossaryEntry(
                "AAA",
                "anti-aircraft artillery",
                read_as="custom",
                spoken_form="Triple A",
                aliases=("A.A.A.",),
            ),
        ),
    )
    assert _lexical_prepare("A.A.R. A.O. A.A.A.", profile).spoken_text == (
        "after-action review A O Triple A"
    )


def test_custom_pronunciation_is_not_sentence_cased() -> None:
    result = _lexical_prepare("AAA. AAA", MILITARY)
    assert result.spoken_text == "Triple A. Triple A"


def test_profile_entry_overrides_bundled_entry_without_mutating_shared_registry() -> None:
    profile = SpeechProfile("override", glossary=(GlossaryEntry("St.", "street"),))
    assert _lexical_prepare("St. Patrick", profile).spoken_text == "street Patrick"
    assert prepare("St. Patrick", use_spacy=False).spoken_text == "Saint Patrick"


def test_profiles_are_isolated_from_each_other() -> None:
    first = SpeechProfile("first", glossary=(GlossaryEntry("XYZ", "first meaning"),))
    second = SpeechProfile("second", glossary=(GlossaryEntry("XYZ", "second meaning"),))
    assert _lexical_prepare("XYZ", first).spoken_text == "first meaning"
    assert _lexical_prepare("XYZ", second).spoken_text == "second meaning"
    assert _lexical_prepare("XYZ", first).spoken_text == "first meaning"
    assert (
        prepare("XYZ", use_spacy=False, expand_structured=False, expand_numbers=False).spoken_text
        == "XYZ"
    )


def test_profile_does_not_inherit_shared_customizations() -> None:
    reset_abbreviations("en")
    add_abbreviation("Drx.", "global custom", language="en")
    try:
        profile = SpeechProfile("isolated")
        assert _lexical_prepare("Drx.", profile).spoken_text == "Drx."
        assert prepare("Drx.", use_spacy=False).spoken_text == "global custom"
    finally:
        reset_abbreviations("en")


def test_profile_language_mismatch_uses_selected_config_language() -> None:
    profile = SpeechProfile("english", language="en")
    config = PreparationConfig(language="de", use_spacy=False)
    with pytest.raises(ValueError, match="profile language"):
        prepare("AAR", config=config, profile=profile)


def test_explicit_letters_work_with_default_registered_mode() -> None:
    profile = SpeechProfile(
        "letters",
        glossary=(GlossaryEntry("AO", "area of operations", read_as="letters"),),
    )
    assert _lexical_prepare("AO", profile).spoken_text == "A O"


def test_long_form_remains_semantic_when_profile_also_requests_spelling() -> None:
    profile = SpeechProfile(
        "mixed",
        glossary=(
            GlossaryEntry("AAR", "after-action review"),
            GlossaryEntry("AO", "area of operations", read_as="letters"),
        ),
    )
    assert _lexical_prepare("AAR AO", profile).spoken_text == "after-action review A O"


def test_guards_are_delegated_to_dependency() -> None:
    profile = SpeechProfile(
        "guards",
        glossary=(
            GlossaryEntry(
                "CTX",
                "context term",
                only_if_preceded_by=r"prefix\s*$",
                only_if_followed_by=r"^\s+ready$",
            ),
            GlossaryEntry("POS", "noun term", only_if_pos=("NOUN",)),
        ),
    )
    assert _lexical_prepare("prefix CTX ready", profile).spoken_text == "prefix context term ready"
    assert _lexical_prepare("other CTX ready", profile).spoken_text == "other CTX ready"
    assert (
        _lexical_prepare(
            "POS", profile, annotations=(TokenAnnotation(0, 3, text="POS", pos="NOUN"),)
        ).spoken_text
        == "noun term"
    )
    assert (
        _lexical_prepare(
            "POS", profile, annotations=(TokenAnnotation(0, 3, text="POS", pos="VERB"),)
        ).spoken_text
        == "POS"
    )


def test_case_sensitive_profile_entry() -> None:
    profile = SpeechProfile(
        "case",
        glossary=(GlossaryEntry("MiX", "mixed term", case_sensitive=True),),
    )
    assert _lexical_prepare("MiX mix", profile).spoken_text == "mixed term mix"


def test_protected_span_blocks_profile_replacement_and_metadata() -> None:
    profile = SpeechProfile(
        "protected",
        glossary=(GlossaryEntry("AAR", "after-action review"), GlossaryEntry("AO", "area")),
    )
    source = "AAR AO"
    start = source.index("AO")
    result = _lexical_prepare(source, profile, protected_spans=[(start, start + 2)])
    assert result.spoken_text == "after-action review AO"
    assert all(item.source != "AO" for item in result.source_replacements)


def test_structured_reserved_span_blocks_profile_replacement() -> None:
    profile = SpeechProfile("chemistry", glossary=(GlossaryEntry("H2O", "water"),))
    result = prepare("H2O", profile=profile, use_spacy=False)
    assert result.spoken_text == "H two O"
    assert "water" not in result.spoken_text


def test_exact_profile_replacement_metadata_and_offsets() -> None:
    profile = SpeechProfile(
        "metadata",
        glossary=(GlossaryEntry("AAA", "anti-aircraft", read_as="custom", spoken_form="Triple A"),),
    )
    source = "Use AAA now."
    result = _lexical_prepare(source, profile)
    replacement = next(item for item in result.source_replacements if item.source == "AAA")
    assert replacement.replacement == "Triple A"
    assert source[replacement.source_start : replacement.source_end] == "AAA"
    assert result.map_source_span(replacement.source_start, replacement.source_end) == (
        replacement.output_start,
        replacement.output_end,
    )


@pytest.mark.parametrize("mode", ["known_only", "conservative_unknown", "spell_unknown"])
def test_generic_acronym_policy_is_unchanged_with_profile(mode: str) -> None:
    profile = SpeechProfile("unrelated", glossary=(GlossaryEntry("TERM", "domain term"),))
    no_profile = prepare("NASA", use_spacy=False, generic_acronym_mode=mode)
    with_profile = prepare("NASA", profile=profile, use_spacy=False, generic_acronym_mode=mode)
    assert with_profile.spoken_text == no_profile.spoken_text


@pytest.mark.parametrize("mode", ["expand", "spell"])
def test_unrelated_registered_behavior_is_unchanged(mode: str) -> None:
    profile = SpeechProfile("unrelated", glossary=(GlossaryEntry("TERM", "domain term"),))
    no_profile = prepare("St. Patrick", use_spacy=False, registered_acronym_mode=mode)
    with_profile = prepare(
        "St. Patrick", profile=profile, use_spacy=False, registered_acronym_mode=mode
    )
    assert with_profile.spoken_text == no_profile.spoken_text


def test_profile_cache_is_deterministic_and_adapter_accepts_profile() -> None:
    first = prepare_for_kokorog2p("AAR AO AAA", "en", profile=MILITARY, use_spacy=False)
    second = prepare_for_kokorog2p("AAR AO AAA", "en", profile=MILITARY, use_spacy=False)
    assert first.spoken_text == second.spoken_text == "after-action review A O Triple A"
