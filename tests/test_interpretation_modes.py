from __future__ import annotations

import pytest

from spokenform import InterpretationMode, prepare
from spokenform.structured import iter_structured_replacements

_CONTEXTUAL_CASES = (
    "in 1989",
    "final 3-2",
    "stock symbol AAPL",
    "George VI",
    "BRCA2 gene",
    "123 Main St",
)


def test_contextual_is_the_backward_compatible_default() -> None:
    for source in _CONTEXTUAL_CASES:
        implicit = prepare(source, language="en", use_spacy=False)
        explicit = prepare(
            source,
            language="en",
            use_spacy=False,
            interpretation_mode=InterpretationMode.CONTEXTUAL,
        )
        assert implicit.to_dict() == explicit.to_dict()


def test_surface_excludes_contextual_structured_rules() -> None:
    replacements = iter_structured_replacements(
        "in 1989 final 3-2 stock symbol AAPL George VI BRCA2 gene",
        language="en",
        interpretation_mode="surface",
    )
    assert not {
        item.rule
        for item in replacements
        if item.rule
        in {
            "sequence.year",
            "sequence.sports",
            "sequence.ticker",
            "sequence.roman",
            "sequence.biomedical",
            "sequence.address",
        }
    }


def test_surface_context_does_not_activate_contextual_rules() -> None:
    before = prepare("3-2", language="en", use_spacy=False, interpretation_mode="surface")
    after = prepare(
        "final 3-2",
        language="en",
        use_spacy=False,
        interpretation_mode="surface",
    )
    assert all(item.rule != "sequence.sports" for item in before.source_replacements)
    assert all(item.rule != "sequence.sports" for item in after.source_replacements)


def test_surface_skips_spacy_and_explicit_strict_use_is_rejected() -> None:
    class FailingNLP:
        def __call__(self, text: str) -> object:
            raise AssertionError("surface mode must not invoke NLP")

    result = prepare("final 3-2", language="en", interpretation_mode="surface", nlp=FailingNLP())
    assert result.spoken_text == "final 3-2"
    with pytest.raises(ValueError, match="surface mode"):
        prepare(
            "final 3-2",
            language="en",
            interpretation_mode="surface",
            use_spacy=True,
            strict=True,
        )


def test_surface_contextual_long_number_mode_preserves_and_warns() -> None:
    result = prepare(
        "account 844361",
        language="en",
        use_spacy=False,
        interpretation_mode="surface",
        long_number_mode="contextual",
    )
    assert result.spoken_text == "account 844361"
    assert any("contextual long numbers as preserve" in warning for warning in result.warnings)


def test_protection_remains_absolute_in_surface_mode() -> None:
    result = prepare(
        "H2O",
        language="en",
        interpretation_mode="surface",
        protected_spans=[(0, 3)],
    )
    assert result.spoken_text == "H2O"
    assert not result.source_replacements
