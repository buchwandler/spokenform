from __future__ import annotations

import json
from pathlib import Path

from spokenform import PreparationConfig, prepare

CASES = json.loads(
    (Path(__file__).parent / "data" / "de_kokorog2p_regressions.json").read_text(encoding="utf-8")
)


def test_legacy_german_semantic_pairs() -> None:
    for source, expected in CASES:
        config = PreparationConfig.for_kokorog2p("de")
        if source == "z.B. 42":
            config = PreparationConfig(
                language="de",
                use_spacy=False,
                expand_abbreviations=False,
            )
        assert prepare(source, config=config).spoken_text == expected, source


def test_german_month_table_is_preserved() -> None:
    months = (
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    )
    for month, expected in enumerate(months, start=1):
        result = prepare(f"15.{month:02d}.2026", language="de", use_spacy=False)
        assert expected in result.spoken_text


def test_german_number_word_semantics_are_public_pipeline_behavior() -> None:
    cases = {
        "0": "null",
        "1": "eins",
        "21": "einundzwanzig",
        "-5": "minus fünf",
        "11": "elf",
        "12": "zwölf",
        "17": "siebzehn",
        "Ich habe 42 Bücher.": "Ich habe zweiundvierzig Bücher.",
    }
    for source, expected in cases.items():
        assert prepare(source, language="de", use_spacy=False).spoken_text == expected

    assert prepare("Preis: 12,50", language="de", use_spacy=False).spoken_text == (
        "Preis: zwölf Komma fünf null"
    )


def test_german_ordinal_contexts_keep_the_original_source_span() -> None:
    source = "im 3. Kapitel, die 4. Version und an der 2. Stelle"
    result = prepare(source, language="de", use_spacy=False)
    assert result.spoken_text == (
        "im dritten Kapitel, die vierte Version und an der zweiten Stelle"
    )
    for replacement in result.source_replacements:
        assert source[replacement.source_start : replacement.source_end] == replacement.source
