from pathlib import Path

import pytest

from spokenform import load_spacy_model, reset_spacy_cache, spacy_annotations

spacy = pytest.importorskip("spacy")


def test_real_spacy_blank_pipeline_annotations() -> None:
    nlp = spacy.blank("en")
    text = "The board is 2 in. wide."
    annotations = spacy_annotations(text, nlp)

    assert annotations
    assert annotations[0].text == "The"
    assert annotations[0].start == 0
    assert annotations[-1].end == len(text)
    assert all(text[item.start : item.end] == item.text for item in annotations)


def test_real_spacy_model_path_loading(tmp_path: Path) -> None:
    model_path = tmp_path / "blank_en"
    spacy.blank("en").to_disk(model_path)

    reset_spacy_cache()
    loaded = load_spacy_model(str(model_path), language="en")
    cached = load_spacy_model(str(model_path), language="en")

    assert loaded.lang == "en"
    assert cached is loaded
