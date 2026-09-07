from __future__ import annotations

import json
from pathlib import Path

import pytest
from abbr2words import supported_languages as abbr2words_supported_languages

from spokenform import SpeechProfile, prepare
from spokenform.language import SUPPORTED_BASE_LANGUAGES, supported_languages, supports_language

CONTRACT = json.loads(
    (Path(__file__).parent / "data" / "language_registry_contract.json").read_text()
)


def test_installed_abbr2words_registry_matches_contract() -> None:
    expected = set(CONTRACT["base_keys"]) | set(CONTRACT["locale_keys"])
    assert set(abbr2words_supported_languages(include_locales=True)) == expected


def test_spokenform_registry_matches_dependency_contract() -> None:
    expected_bases = {"kk" if key == "kz" else key for key in CONTRACT["base_keys"]}
    expected_keys = expected_bases | set(CONTRACT["locale_keys"])
    assert set(SUPPORTED_BASE_LANGUAGES) == expected_bases
    assert set(supported_languages(include_locales=True)) == expected_keys
    assert len(SUPPORTED_BASE_LANGUAGES) == 49
    assert len(supported_languages(include_locales=True)) == 66
    assert not supports_language("eu")


@pytest.mark.parametrize(
    "language", sorted(set(CONTRACT["base_keys"]) | set(CONTRACT["locale_keys"]))
)
def test_all_language_pipeline_smoke(language: str) -> None:
    public_language = "kk" if language == "kz" else language
    result = prepare(
        "Plain text",
        language=public_language,
        profile=SpeechProfile("smoke", language=public_language),
        use_spacy=False,
    )
    assert result.language == public_language
    assert result.spoken_text
