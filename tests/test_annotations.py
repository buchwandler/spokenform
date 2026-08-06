from dataclasses import dataclass

from spokenform import TokenAnnotation, annotations_from_spacy
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
