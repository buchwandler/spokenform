from __future__ import annotations

import pytest
from kokorog2p.pipeline_api import _spokenform_language, _uses_spokenform_semantics

from spokenform import (
    add_abbreviation,
    has_abbreviation,
    remove_abbreviation,
    reset_abbreviations,
)


@pytest.mark.parametrize(
    ("alias", "spokenform_language"),
    [
        ("en", "en-us"),
        ("eng", "en-us"),
        ("deu", "de-de"),
        ("fra", "fr-fr"),
        ("spa", "es-es"),
        ("ita", "it-it"),
        ("por", "pt-br"),
        ("ces", "cs-cz"),
        ("vie", "vi-vn"),
        ("kor", "ko-kr"),
        ("heb", "he"),
        ("cmn", "zh"),
        ("jpn", "ja-jp"),
        ("ara", "ar"),
        ("swe", "sv-se"),
        ("tha", "th-th"),
        ("rus", "ru-ru"),
        ("kaz", "kk"),
    ],
)
def test_kokoro_aliases_adapt_to_spokenform_without_alias_leakage(
    alias: str, spokenform_language: str
) -> None:
    assert _spokenform_language(alias) == spokenform_language
    assert _uses_spokenform_semantics(alias)


def test_spokenform_abbreviation_facade_uses_shared_registry() -> None:
    reset_abbreviations("en")
    try:
        add_abbreviation("Xx.", "Example", language="en")
        assert has_abbreviation("Xx.", language="en")
        assert remove_abbreviation("Xx.", language="en")
        assert not has_abbreviation("Xx.", language="en")
    finally:
        reset_abbreviations("en")
