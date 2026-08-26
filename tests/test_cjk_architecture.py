from __future__ import annotations

import importlib

from spokenform.config import NumberPolicy, number_policy_for_language
from spokenform.language import SUPPORTED_BASE_LANGUAGES
from spokenform.number_words import number_backend_for_language
from spokenform.numeric_lexeme import numeric_punctuation_policy, numeric_speech_policy
from spokenform.sequences import vocabulary


def test_every_supported_language_has_explicit_runtime_policies() -> None:
    for language in SUPPORTED_BASE_LANGUAGES:
        assert number_policy_for_language(language) is NumberPolicy.STRUCTURED_AND_PLAIN
        assert numeric_punctuation_policy(language)
        assert numeric_speech_policy(language)
        assert vocabulary(language)
        importlib.import_module(f"spokenform.locales.{language}")


def test_cjk_backend_routing_is_explicit() -> None:
    assert number_backend_for_language("ja") == "num2words"
    assert number_backend_for_language("ko") == "num2words"
    assert number_backend_for_language("zh") == "cn2an"
    assert number_backend_for_language("zh_CN") == "cn2an"
