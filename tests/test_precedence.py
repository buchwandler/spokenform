import pytest

from spokenform import prepare


@pytest.mark.parametrize(
    ("source", "language", "rule", "source_fragment"),
    [
        ("ISBN 978-2-08-121810-5", "en", "sequence.isbn", "ISBN 978-2-08-121810-5"),
        ("2025/03/15", "en", "en.date", "2025/03/15"),
        ("1/2 cup", "en", "sequence.fraction", "1/2"),
        ("Section 12", "en", "sequence.legal", "Section 12"),
        ("final 3-2", "en", "sequence.sports", "3-2"),
        ("ABC", "en", "abbr:ABC", "ABC"),
        ("2 g/cm³", "en", "sequence.compound-unit", "2 g/cm³"),
        ("$25.50", "en", "en.currency", "$25.50"),
    ],
)
def test_structured_precedence_selects_the_semantic_candidate(
    source: str, language: str, rule: str, source_fragment: str
) -> None:
    result = prepare(source, language=language, use_spacy=False)
    if rule == "sequence.isbn":
        assert any(
            item.rule == rule and item.source == "ISBN" for item in result.source_replacements
        )
        assert any(
            item.rule == rule and item.source == source.split(" ", 1)[1]
            for item in result.source_replacements
        )
    else:
        assert any(
            item.rule == rule and item.source == source_fragment
            for item in result.source_replacements
        )


@pytest.mark.parametrize("source", ["https://example.org/1/2", "Brown v. Board", "l/100 km"])
def test_no_false_claim_inputs_do_not_use_fraction_or_phone(source: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert not any(
        item.rule in {"sequence.fraction", "sequence.phone"} for item in result.source_replacements
    )
