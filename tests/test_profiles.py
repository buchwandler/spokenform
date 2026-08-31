from dataclasses import FrozenInstanceError

import pytest

from spokenform import GlossaryConflictError, GlossaryEntry, SpeechProfile


def test_profile_is_hashable_and_immutable() -> None:
    entry = GlossaryEntry("AAR", "after-action review")
    profile = SpeechProfile("operations", glossary=(entry,))

    assert hash(profile)
    assert profile.language == "en"
    with pytest.raises(FrozenInstanceError):
        profile.name = "changed"  # type: ignore[misc]


def test_entry_rejects_empty_required_values() -> None:
    with pytest.raises(ValueError, match="abbreviation"):
        GlossaryEntry("  ", "meaning")
    with pytest.raises(ValueError, match="long_form"):
        GlossaryEntry("TERM", " ")
    with pytest.raises(ValueError, match="name"):
        SpeechProfile(" ")


def test_custom_reading_requires_spoken_form() -> None:
    with pytest.raises(ValueError, match="read_as='custom'"):
        GlossaryEntry("AAA", "anti-aircraft artillery", read_as="custom")


def test_spoken_form_rejected_for_non_custom() -> None:
    with pytest.raises(ValueError, match="only valid"):
        GlossaryEntry("AAR", "after-action review", spoken_form="AAR words")


def test_aliases_and_guards_are_validated() -> None:
    with pytest.raises(ValueError, match="aliases"):
        GlossaryEntry("AAR", "review", aliases=("AAR",))
    with pytest.raises(ValueError, match="aliases"):
        GlossaryEntry("AAR", "review", aliases=("",))
    with pytest.raises(ValueError, match="regular expression"):
        GlossaryEntry("AAR", "review", only_if_followed_by="[")
    with pytest.raises(TypeError, match="only_if_pos"):
        GlossaryEntry("AAR", "review", only_if_pos=["NOUN"])  # type: ignore[arg-type]


def test_duplicate_glossary_surfaces_are_rejected() -> None:
    with pytest.raises(GlossaryConflictError, match="duplicate glossary surface 'aa'"):
        SpeechProfile(
            "military-en",
            glossary=(
                GlossaryEntry("AA", "assembly area"),
                GlossaryEntry("aa", "anti-aircraft"),
            ),
        )


def test_alias_collision_is_rejected() -> None:
    with pytest.raises(GlossaryConflictError, match="duplicate glossary surface 'A.O.'"):
        SpeechProfile(
            "military-en",
            glossary=(
                GlossaryEntry("AO", "area of operations", aliases=("A.O.",)),
                GlossaryEntry("OTHER", "other", aliases=("A.O.",)),
            ),
        )


def test_profile_language_is_normalized() -> None:
    profile = SpeechProfile("german", language="de-DE")
    assert profile.language == "de_DE"
