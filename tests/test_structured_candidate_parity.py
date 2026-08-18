from __future__ import annotations

import pytest

from spokenform import iter_structured_replacements, prepare
from spokenform.structured import iter_structured_candidates, resolve_structured_candidates


@pytest.mark.parametrize(
    ("language", "source"),
    [
        ("en", "Python 3.9.7"),
        ("de", "2 kg"),
        ("es", "1:45 p.m."),
        ("fr", "2 kg"),
        ("it", "15ª"),
        ("pt", "2 kg"),
        ("cs", "2 Kč"),
    ],
)
def test_resolve_structured_candidates_matches_runtime_resolution(
    language: str, source: str
) -> None:
    candidates = iter_structured_candidates(source, language=language)

    assert iter_structured_replacements(source, language=language) == resolve_structured_candidates(
        source,
        candidates,
        language=language,
    )


@pytest.mark.parametrize(
    ("source", "spoken", "rules"),
    [
        ("version 3.4", "version three point four", (None,)),
        (
            "IPv4 192.168.1.1",
            "IPv4 one nine two point one six eight point one point one",
            ("sequence.ipv4",),
        ),
        ("Team won 6:3", "Team won six to three", ("sequence.sports",)),
        ("John 1:16-17", "John one sixteenminus seventeen", (None,)),
        ("10-7-3", "ten-seven-three", (None, None, None)),
        ("version 3-2-1", "version three-two-one", (None, None, None)),
        ("Section 3-2-1", "section threeminus two-one", (None, None)),
        ("room 3-2-1", "room three-two-one", (None, None, None)),
        ("ISO-1994", "I S O one nine nine four", ("sequence.product",)),
        ("Model 1858", "model one thousand, eight hundred fifty-eight", ("sequence.product",)),
        ("PIN 1972", "P I N one nine seven two", ("sequence.product",)),
        ("serial 2014-ABC", "serial number two zero one four A B C", ("sequence.product",)),
        ("He is called ART.", "He is called ART.", ()),
        ("resident IDs", "resident IDs", ()),
        ("Python 3.9.7", "Python three dot nine dot seven", ("sequence.version",)),
    ],
)
def test_high_risk_prepare_outputs_remain_unchanged(
    source: str, spoken: str, rules: tuple[str | None, ...]
) -> None:
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == spoken
    assert tuple(item.rule for item in result.source_replacements) == rules
