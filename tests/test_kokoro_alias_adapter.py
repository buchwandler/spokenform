from __future__ import annotations

import pytest

pytest.importorskip("kokorog2p")
from kokorog2p.language_codes import normalize_language_code

from spokenform import (
    add_abbreviation,
    has_abbreviation,
    remove_abbreviation,
    reset_abbreviations,
    supports_profile,
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
def test_kokoro_aliases_keep_independent_spokenform_profile(
    alias: str, spokenform_language: str
) -> None:
    assert normalize_language_code(alias) == spokenform_language
    assert supports_profile(spokenform_language)


def test_spokenform_abbreviation_facade_uses_shared_registry() -> None:
    reset_abbreviations("en")
    try:
        add_abbreviation("Xx.", "Example", language="en")
        assert has_abbreviation("Xx.", language="en")
        assert remove_abbreviation("Xx.", language="en")
        assert not has_abbreviation("Xx.", language="en")
    finally:
        reset_abbreviations("en")
