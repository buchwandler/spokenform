import pytest

from spokenform.language import (
    SUPPORTED_BASE_LANGUAGES,
    base_language,
    normalize_language,
    resolve_abbr2words_language,
    resolve_num2words_language,
    supported_languages,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [("en", "en"), ("en-gb", "en_GB"), ("en_GB", "en_GB"), ("EN-gb", "en_GB")],
)
def test_normalize_language(value: str, expected: str) -> None:
    assert normalize_language(value) == expected


def test_base_language_and_supported_languages() -> None:
    assert base_language("en_GB") == "en"
    assert base_language("de_DE") == "de"
    assert supported_languages() == SUPPORTED_BASE_LANGUAGES == (
        "cs",
        "de",
        "en",
        "es",
        "fr",
        "it",
        "pt",
    )


def test_language_validation() -> None:
    with pytest.raises(TypeError, match="language must be a string"):
        normalize_language(None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="language must not be empty"):
        normalize_language("  ")


def test_dependency_language_uses_exact_variant_when_available() -> None:
    assert resolve_num2words_language("en_IN") == "en_IN"
    assert resolve_abbr2words_language("en_IN") in {"en", "en_IN"}


def test_dependency_language_falls_back_to_base_when_variant_is_missing() -> None:
    assert resolve_num2words_language("en_GB") == "en"
    assert resolve_abbr2words_language("en_GB") == "en"
