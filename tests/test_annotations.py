from dataclasses import dataclass

import pytest

from spokenform import TokenAnnotation, annotations_from_spacy, validate_annotations
from spokenform.annotations import to_abbr2words_annotations


@dataclass
class FakeToken:
    text: str
    idx: int
    pos_: str
    tag_: str


def test_spacy_adapter_needs_no_spacy_import() -> None:
    annotations = annotations_from_spacy(
        [FakeToken("in", 0, "ADP", "IN"), FakeToken(".", 2, "PUNCT", ".")]
    )
    assert annotations[0].start == 0
    assert annotations[0].end == 2
    assert annotations[0].pos == "ADP"
    assert isinstance(annotations[0], TokenAnnotation)


def test_public_annotations_adapt_to_abbr2words() -> None:
    adapted = to_abbr2words_annotations(
        (TokenAnnotation(0, 2, text="in", pos="ADP", tag="IN", lemma="in"),)
    )
    assert adapted is not None
    assert adapted[0].start == 0
    assert adapted[0].pos == "ADP"


def test_annotation_validation_rejects_misaligned_text() -> None:
    with pytest.raises(ValueError, match="does not match"):
        validate_annotations(
            "hello",
            (TokenAnnotation(0, 5, text="other", pos="NOUN"),),
        )


def test_annotation_validation_rejects_overlap() -> None:
    with pytest.raises(ValueError, match="overlaps"):
        validate_annotations(
            "hello",
            (
                TokenAnnotation(0, 3, text="hel"),
                TokenAnnotation(2, 5, text="llo"),
            ),
        )


def test_annotations_are_remapped_after_protected_spans(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import spokenform.api as api

    source = "https://example.org/long-path 2 in."
    token_start = source.index("in.")
    annotations = (TokenAnnotation(token_start, token_start + 3, text="in.", pos="NOUN"),)
    captured: dict[str, object] = {}

    def capture(
        text: str,
        *,
        lang: str,
        context: bool,
        annotations: object,
        protected_spans: object,
    ) -> object:
        captured["text"] = text
        captured["annotations"] = annotations
        from abbr2words import abbr2words_with_replacements

        return abbr2words_with_replacements(
            text,
            lang=lang,
            context=context,
            annotations=annotations,
            protected_spans=protected_spans,
        )

    monkeypatch.setattr(api, "abbr2words_with_replacements", capture)
    api.prepare(
        source,
        language="en",
        annotations=annotations,
        expand_numbers=False,
        normalize_whitespace=False,
    )

    transformed = captured["text"]
    adapted = captured["annotations"]
    assert isinstance(transformed, str)
    assert adapted is not None
    first = adapted[0]  # type: ignore[index]
    assert transformed[first.start : first.end] == "in."


def test_annotations_are_remapped_between_structured_and_abbreviation_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from abbr2words import abbr2words_with_replacements

    import spokenform.api as api

    source = "Am 01.01.2024 Dr. Klein"
    token_start = source.index("Dr.")
    annotations = (TokenAnnotation(token_start, token_start + 3, text="Dr.", pos="PROPN"),)
    captured: dict[str, object] = {}

    def capture(text: str, **kwargs: object) -> object:
        captured["text"] = text
        captured["annotations"] = kwargs["annotations"]
        return abbr2words_with_replacements(text, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(api, "abbr2words_with_replacements", capture)
    result = api.prepare(
        source,
        language="de",
        annotations=annotations,
        expand_numbers=False,
        normalize_whitespace=False,
        use_spacy=False,
    )

    transformed = captured["text"]
    adapted = captured["annotations"]
    assert isinstance(transformed, str)
    assert adapted is not None
    first = adapted[0]  # type: ignore[index]
    assert transformed[first.start : first.end] == "Dr."
    assert result.spoken_text.endswith("Doktor Klein")


def test_annotation_validation_rejects_empty_spans() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        validate_annotations("hello", (TokenAnnotation(2, 2),))


def test_annotation_validation_rejects_non_string_labels() -> None:
    with pytest.raises(TypeError, match="pos"):
        validate_annotations(
            "hello",
            (TokenAnnotation(0, 5, text="hello", pos=1),),  # type: ignore[arg-type]
        )
