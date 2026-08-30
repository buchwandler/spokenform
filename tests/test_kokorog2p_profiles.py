from __future__ import annotations

import pytest

from spokenform import (
    KOKOROG2P_PROFILE_VERSION,
    SUPPORTED_BASE_LANGUAGES,
    NumberPolicy,
    PreparationConfig,
    prepare_for_kokorog2p,
    resolve_abbr2words_language,
    resolve_num2words_language,
    supports_profile,
)

EXPECTED_FAMILIES = {
    "ar",
    "cs",
    "de",
    "en",
    "es",
    "fr",
    "he",
    "it",
    "ja",
    "kk",
    "ko",
    "pt",
    "ru",
    "sv",
    "th",
    "vi",
    "zh",
}


def test_kokorog2p_profile_contract_covers_all_families() -> None:
    assert set(SUPPORTED_BASE_LANGUAGES) == EXPECTED_FAMILIES
    assert KOKOROG2P_PROFILE_VERSION == "0.3.2"
    assert all(supports_profile(language) for language in EXPECTED_FAMILIES)
    assert not supports_profile("en", "other")
    assert not supports_profile("unknown")


@pytest.mark.parametrize("language", ["ar", "ara", "msa", "he", "heb", "kk", "kaz", "kk-kz"])
def test_conservative_profiles_keep_numbers_caller_managed(language: str) -> None:
    config = PreparationConfig.for_kokorog2p(language)
    assert config.number_policy is NumberPolicy.NONE
    assert supports_profile(language)
    result = prepare_for_kokorog2p("123 NASA", language)
    assert result.spoken_text


def test_kazakh_dependency_key_is_explicit() -> None:
    assert resolve_abbr2words_language("kk") == "kz"
    assert resolve_abbr2words_language("kk-kz") == "kz"
    assert resolve_num2words_language("kk") == "kz"


def test_new_profile_replacements_preserve_protected_text() -> None:
    source = "NASA 123"
    result = prepare_for_kokorog2p(source, "ar", protected_spans=[(0, 4)])
    assert source[:4] in result.spoken_text
    assert not any(item.source == "NASA" for item in result.source_replacements)
