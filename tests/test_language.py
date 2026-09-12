from __future__ import annotations

import pytest

from spokenform.config import NumberPolicy
from spokenform.language import (
    KOKOROG2P_PROFILE_LANGUAGES,
    SUPPORTED_BASE_LANGUAGES,
    SUPPORTED_LOCALES,
    base_language,
    normalize_language,
    resolve_abbr2words_language,
    resolve_numeralform_locale,
    supported_languages,
    supports_language,
)
from spokenform.language_support import SupportTier, language_support

EXPECTED_BASES = {
    "am",
    "ar",
    "az",
    "be",
    "bn",
    "ca",
    "ce",
    "cs",
    "cy",
    "da",
    "de",
    "en",
    "eo",
    "es",
    "fa",
    "fi",
    "fr",
    "he",
    "hi",
    "hu",
    "hy",
    "id",
    "is",
    "it",
    "ja",
    "kk",
    "kn",
    "ko",
    "lt",
    "lv",
    "mn",
    "nl",
    "no",
    "pl",
    "pt",
    "ro",
    "ru",
    "sk",
    "sl",
    "sr",
    "sv",
    "te",
    "tet",
    "tg",
    "th",
    "tr",
    "uk",
    "vi",
    "zh",
}
EXPECTED_LOCALES = {
    "en_GB",
    "en_IN",
    "en_NG",
    "en_US",
    "es_CO",
    "es_CR",
    "es_GT",
    "es_MX",
    "es_NI",
    "es_VE",
    "fr_BE",
    "fr_CH",
    "fr_DZ",
    "pt_BR",
    "zh_CN",
    "zh_HK",
    "zh_TW",
    "pt_PT",
}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("en", "en"),
        ("en-gb", "en_GB"),
        ("EN-gb", "en_GB"),
        ("pt-BR", "pt_BR"),
        ("fr_FR", "fr"),
        ("fr-CH", "fr_CH"),
        ("es-ni", "es_NI"),
        ("JP", "ja"),
        ("cn", "zh_CN"),
        ("swe", "sv"),
        ("swe-SE", "sv"),
        ("rus-RU", "ru"),
        ("vi-VN", "vi"),
        ("kk-kz", "kk"),
    ],
)
def test_normalize_language(value: str, expected: str) -> None:
    assert normalize_language(value) == expected


def test_base_language_and_supported_languages() -> None:
    assert base_language("en_GB") == "en"
    assert base_language("de_DE") == "de"
    assert set(SUPPORTED_BASE_LANGUAGES) == EXPECTED_BASES
    assert set(supported_languages()) == EXPECTED_BASES
    assert set(SUPPORTED_LOCALES) == EXPECTED_LOCALES
    assert set(supported_languages(include_locales=True)) == EXPECTED_BASES | EXPECTED_LOCALES
    assert len(supported_languages(include_locales=True)) == 67


def test_language_validation() -> None:
    with pytest.raises(TypeError, match="language must be a string"):
        normalize_language(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="language must not be empty"):
        normalize_language("  ")
    with pytest.raises(ValueError, match="Unsupported language"):
        normalize_language("EU")
    assert supports_language("nl")
    assert not supports_language("EU")


@pytest.mark.parametrize(
    ("requested", "expected"),
    [("en-gb", "en_GB"), ("ES-ni", "es_NI"), ("pt-br", "pt_BR"), ("zh-hk", "zh_HK")],
)
def test_abbr2words_preserves_exact_registered_overlays(requested: str, expected: str) -> None:
    assert resolve_abbr2words_language(requested) == expected


@pytest.mark.parametrize("requested", ["fr-FR", "de-DE", "vi-VN", "sv-SE"])
def test_dependency_language_falls_back_to_base(requested: str) -> None:
    assert resolve_abbr2words_language(requested) == base_language(requested)


def test_numeralform_uses_exact_variant_when_available() -> None:
    assert resolve_numeralform_locale("en_IN") == "en-IN"
    assert resolve_numeralform_locale("en_GB") == "en-GB"


def test_numeralform_locale_routing() -> None:
    assert resolve_numeralform_locale("ja_JP") == "ja"
    assert resolve_numeralform_locale("ko_KR") == "ko"
    assert resolve_numeralform_locale("zh_CN") == "zh-CN"
    assert resolve_numeralform_locale("pt-PT") == "pt-PT"
    assert resolve_abbr2words_language("zh_CN") == "zh_CN"
    assert resolve_abbr2words_language("cn") == "zh_CN"


def test_kazakh_dependency_aliases_are_independent() -> None:
    assert normalize_language("kz") == "kk"
    assert resolve_abbr2words_language("kk") == "kz"
    assert resolve_numeralform_locale("kk") == "kk"


def test_compatibility_aliases_and_unknowns() -> None:
    assert base_language("rus-RU") == "ru"
    with pytest.raises(ValueError, match="Unsupported language"):
        resolve_abbr2words_language("kr")
    with pytest.raises(ValueError, match="Unsupported language"):
        resolve_abbr2words_language("vn")


def test_kokoro_profile_set_is_independent() -> None:
    assert set(KOKOROG2P_PROFILE_LANGUAGES) == {
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


def test_russian_number_policy() -> None:
    from spokenform.config import number_policy_for_language

    assert number_policy_for_language("ru") is NumberPolicy.STRUCTURED_AND_PLAIN
    assert number_policy_for_language("ru-RU") is NumberPolicy.STRUCTURED_AND_PLAIN


@pytest.mark.parametrize("language", sorted(EXPECTED_BASES | EXPECTED_LOCALES))
def test_language_support_metadata_is_orthogonal(language: str) -> None:
    support = language_support(language)
    assert support.language == normalize_language(language)
    assert support.abbreviation_language == support.language
    if support.base in {
        "cs",
        "de",
        "en",
        "es",
        "fr",
        "it",
        "ja",
        "ko",
        "pt",
        "ru",
        "sv",
        "th",
        "vi",
        "zh",
    }:
        assert support.tier is SupportTier.REVIEWED_STRUCTURED
    else:
        assert support.tier in {SupportTier.FOUNDATION, SupportTier.CONSERVATIVE_INTEGRATION}
    assert support.kokorog2p_profile == (support.base in KOKOROG2P_PROFILE_LANGUAGES)


@pytest.mark.parametrize("language", ["hi", "hy", "mn"])
def test_renderer_availability_is_separate_from_plain_number_ownership(language: str) -> None:
    support = language_support(language)
    assert support.number_backend == "numeralform"
    assert support.number_backend_available
    assert not support.plain_cardinals


def test_supported_language_enumeration_matches_acceptance() -> None:
    accepted = set(supported_languages(include_locales=True))
    for language in accepted:
        assert supports_language(language)
        assert normalize_language(language) in accepted
    assert "pt_PT" in accepted
    assert supports_language("pt-PT")
    assert normalize_language("pt-PT") == "pt_PT"
    assert resolve_numeralform_locale("pt_PT") == "pt-PT"
    assert resolve_abbr2words_language("pt_PT") == "pt"
