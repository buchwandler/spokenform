import pytest

from spokenform import prepare
from spokenform.recognizers.sequences import _roman_is_valid


@pytest.mark.parametrize("source", ["I", "IV", "IX", "XLII", "CXII", "MCMXC", "MMXXIV"])
def test_roman_validator_accepts_canonical_forms(source: str) -> None:
    assert _roman_is_valid(source)


@pytest.mark.parametrize("source", ["IIII", "VX", "IC", "XM"])
def test_roman_validator_rejects_noncanonical_forms(source: str) -> None:
    assert not _roman_is_valid(source)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("Part IX", "Part nine"),
        ("Block XLII", "Block forty two"),
        ("Section XXI", "Section twenty one"),
        ("The clock showed XII.", "The clock showed twelve."),
        ("The document is numbered CXII.", "The document is numbered one hundred twelve."),
        ("The manuscript is from the XV century.", "The manuscript is from the fifteenth century."),
        (
            "The painting is from the XVIII dynasty.",
            "The painting is from the eighteenth dynasty.",
        ),
        ("The event is scheduled for MMXXIV.", "The event is scheduled for twenty twenty four."),
        ("The document is dated MDCCLXXVI.", "The document is dated seventeen seventy six."),
        ("The coin is from the year MCMXC.", "The coin is from the year nineteen ninety."),
        ("King Henry VIII", "King Henry the eighth"),
    ],
)
def test_english_roman_contexts_cover_new_semantics(source: str, expected: str) -> None:
    result = prepare(source, language="en", use_spacy=False)

    assert result.spoken_text == expected
    assert any(item.rule == "sequence.roman" for item in result.source_replacements)


@pytest.mark.parametrize(
    "source",
    [
        "IV",
        "CD",
        "DVD",
        "MD",
        "CI",
        "MM",
        "IV line",
        "vitamin IV",
        "model IXB",
        "Section IXB",
        "IIII",
        "VX",
        "IC",
    ],
)
def test_english_roman_contexts_remain_conservative(source: str) -> None:
    result = prepare(source, language="en", use_spacy=False)
    assert not any(item.rule == "sequence.roman" for item in result.source_replacements)


def test_roman_provenance_stays_atomic_for_contextual_match() -> None:
    result = prepare("Block XLII", language="en", use_spacy=False)
    replacements = [item for item in result.source_replacements if item.rule == "sequence.roman"]

    assert len(replacements) == 1
    assert replacements[0].source == "XLII"
    assert replacements[0].replacement == "forty two"


@pytest.mark.parametrize(
    ("source", "language", "expected"),
    [
        ("Die Uhr zeigte XII.", "de", "Die Uhr zeigte zwölf."),
        (
            "Das Dokument ist mit CXII nummeriert.",
            "de",
            "Das Dokument ist mit einhundertzwölf nummeriert.",
        ),
        ("... aus dem Jahr MCMXC", "de", "... aus dem Jahr neunzehnhundertneunzig"),
        ("Heinrich VIII.", "de", "Heinrich der Achte."),
        ("Königin Elisabeth II.", "de", "Königin Elisabeth die Zweite."),
        ("Acto IV, Escena II", "es", "Acto cuatro, Escena dos"),
        ("Año MMXXIV.", "es", "Año dos mil veinticuatro."),
        ("Henri VIII", "fr", "Henri huit"),
        ("Partie IX", "fr", "Partie neuf"),
        ("XVe siècle", "fr", "quinzième siècle"),
        ("XVIIIe dynastie", "fr", "dix-huitième dynastie"),
        ("Re Enrico VIII", "it", "Re Enrico ottavo"),
        ("Parte IX", "it", "Parte nove"),
        ("XV secolo", "it", "quindicesimo secolo"),
        ("Rei Henrique VIII", "pt", "Rei Henrique o oitavo"),
        ("Seção XXI", "pt", "Seção vinte e um"),
        ("século XV", "pt", "século décimo quinto"),
    ],
)
def test_multilingual_roman_contexts_are_locale_aware(
    source: str, language: str, expected: str
) -> None:
    result = prepare(source, language=language, use_spacy=False)

    assert result.spoken_text == expected
    assert any(item.rule == "sequence.roman" for item in result.source_replacements)
