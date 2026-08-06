from dataclasses import dataclass

from spokenform import annotations_from_spacy


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
