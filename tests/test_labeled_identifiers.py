from __future__ import annotations

import pytest

from spokenform import prepare


@pytest.mark.parametrize(
    ("source", "expected"),
    (
        (
            "barcode 123456789012",
            "barcode one two three four five six seven eight nine zero one two",
        ),
        (
            "IMEI 123456789012345",
            "I M E I one two three four five six seven eight nine zero one two three four five",
        ),
        (
            "ICCID 123456789012345",
            "I C C I D one two three four five six seven eight nine zero one two three four five",
        ),
        (
            "routing number 123456789012",
            "routing number one two three four five six seven eight nine zero one two",
        ),
        (
            "PIN 123456",
            "P I N one two three four five six",
        ),
        (
            "serial 123456789012",
            "serial number one two three four five six seven eight nine zero one two",
        ),
        (
            "tag 123456789012",
            "tag one two three four five six seven eight nine zero one two",
        ),
        (
            "account 123456789012",
            "account one two three four five six seven eight nine zero one two",
        ),
    ),
)
def test_labeled_numeric_identifiers_are_spoken_digitwise(source: str, expected: str) -> None:
    assert prepare(source, language="en", use_spacy=False).spoken_text == expected


@pytest.mark.parametrize(
    "source",
    ("population 123456789012", "revenue 123456789012", "a 12-digit number 123456789012"),
)
def test_unlabeled_long_numbers_keep_the_default_policy(source: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert not any(item.rule == "sequence.product" for item in result.source_replacements)
