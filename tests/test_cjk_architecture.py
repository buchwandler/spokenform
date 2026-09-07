from __future__ import annotations

import importlib

from spokenform.config import NumberPolicy, number_policy_for_language
from spokenform.language_support import (
    CONSERVATIVE_INTEGRATION_LANGUAGES,
    REVIEWED_NUMERIC_PUNCTUATION_LANGUAGES,
    REVIEWED_STRUCTURED_LANGUAGES,
    SEQUENCE_POLICY_LANGUAGES,
)
from spokenform.number_words import number_backend_for_language
from spokenform.numeric_lexeme import numeric_punctuation_policy, numeric_speech_policy
from spokenform.sequences import vocabulary

STRUCTURED_LOCALE_LANGUAGES = REVIEWED_STRUCTURED_LANGUAGES | CONSERVATIVE_INTEGRATION_LANGUAGES


def test_runtime_policy_sets_are_explicit() -> None:
    for language in STRUCTURED_LOCALE_LANGUAGES:
        expected_policy = (
            NumberPolicy.NONE
            if language in CONSERVATIVE_INTEGRATION_LANGUAGES
            else NumberPolicy.STRUCTURED_AND_PLAIN
        )
        assert number_policy_for_language(language) is expected_policy
        importlib.import_module(f"spokenform.locales.{language}")
    for language in REVIEWED_NUMERIC_PUNCTUATION_LANGUAGES:
        assert numeric_punctuation_policy(language)
        assert numeric_speech_policy(language)
    for language in SEQUENCE_POLICY_LANGUAGES:
        assert vocabulary(language)


def test_cjk_backend_routing_is_explicit() -> None:
    assert number_backend_for_language("ja") == "num2words"
    assert number_backend_for_language("ko") == "num2words"
    assert number_backend_for_language("zh") == "cn2an"
    assert number_backend_for_language("zh_CN") == "cn2an"
