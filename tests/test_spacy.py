from dataclasses import dataclass
from types import SimpleNamespace

import pytest

from spokenform import (
    SpacyModelError,
    annotations_from_spacy,
    load_spacy_model,
    prepare,
    reset_spacy_cache,
)


@dataclass
class FakeToken:
    text: str
    idx: int
    pos_: str = ""
    tag_: str = ""
    lemma_: str = ""
    lang_: str = "en"


class FakeNLP:
    def __call__(self, text: str) -> list[FakeToken]:
        return [
            FakeToken("The", 0, "DET", "DT", "the"),
            FakeToken("box", 4, "NOUN", "NN", "box"),
            FakeToken("is", 8, "AUX", "VBZ", "be"),
            FakeToken("2", 11, "NUM", "CD", "2"),
            FakeToken("in.", 13, "NOUN", "NN", "in"),
        ]


def test_injected_pipeline_is_provider_neutral_and_pos_aware() -> None:
    annotations = annotations_from_spacy(FakeNLP()("The box is 2 in."))
    assert annotations[-1].lemma == "in"
    result = prepare("The box is 2 in.", language="en", nlp=FakeNLP())
    assert "two inch" in result.spoken_text


def test_use_spacy_false_does_not_invoke_injected_pipeline() -> None:
    class FailingNLP:
        def __call__(self, text: str) -> object:
            raise AssertionError("must not run")

    result = prepare("2 tests", language="en", nlp=FailingNLP(), use_spacy=False)
    assert result.spoken_text == "two tests"


def test_missing_requested_model_warns_or_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_spacy_cache()
    monkeypatch.setitem(__import__("sys").modules, "spacy", None)
    result = prepare("2 tests", language="en", use_spacy=True, spacy_model="missing")
    assert any(warning.startswith("[SPACY]") for warning in result.warnings)
    with pytest.raises(SpacyModelError):
        prepare("2 tests", language="en", use_spacy=True, spacy_model="missing", strict=True)


def test_model_cache_is_keyed_and_resettable(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def load(model: str) -> object:
        calls.append(model)
        return object()

    monkeypatch.setitem(__import__("sys").modules, "spacy", SimpleNamespace(load=load))
    reset_spacy_cache()
    first = load_spacy_model("fake_model", language="en")
    second = load_spacy_model("fake_model", language="en")
    assert first is second
    assert calls == ["fake_model"]
    reset_spacy_cache()
    assert load_spacy_model("fake_model", language="en") is not first


def test_explicit_annotations_take_precedence_over_model_loading(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailingNLP:
        def __call__(self, text: str) -> object:
            raise AssertionError("explicit annotations must prevent pipeline execution")

    annotations = annotations_from_spacy(FakeNLP()("The box is 2 in."))
    result = prepare(
        "The box is 2 in.",
        language="en",
        annotations=annotations,
        nlp=FailingNLP(),
        spacy_model="unused",
    )
    assert "two inch" in result.spoken_text


def test_model_language_mismatch_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_spacy_cache()
    pipeline = SimpleNamespace(lang="en")
    monkeypatch.setitem(
        __import__("sys").modules,
        "spacy",
        SimpleNamespace(load=lambda model: pipeline),
    )
    with pytest.raises(SpacyModelError, match="not 'de'"):
        load_spacy_model("fake_model", language="de")
