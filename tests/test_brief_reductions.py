from spokenform import prepare
from spokenform.precedence import SequencePriority, priority_for_rule


def test_reviewed_free_standing_initialisms_are_owned_by_abbr2words() -> None:
    result = prepare("ABC BBC USA IUCN", language="en", use_spacy=False)
    assert all(item.rule.startswith("abbr:") for item in result.source_replacements)
    assert not any(item.rule == "sequence.acronym" for item in result.source_replacements)


def test_structured_precedence_is_named_and_stable() -> None:
    assert priority_for_rule("sequence.reference") > priority_for_rule("sequence.phone")
    assert priority_for_rule("sequence.isbn") > priority_for_rule("sequence.phone")
    assert priority_for_rule("sequence.version") > priority_for_rule("sequence.ipv4")
    assert priority_for_rule("sequence.duration") > priority_for_rule("sequence.time")
    assert SequencePriority.NUMERIC_RANGE > SequencePriority.PHONE_AMBIGUOUS


def test_ambiguous_numeric_ownership_prefers_typed_semantics() -> None:
    assert any(
        item.rule == "sequence.reference"
        for item in prepare("3:81 (1881)", language="es", use_spacy=False).source_replacements
    )
    assert any(
        item.rule == "sequence.duration"
        for item in prepare("2:15:30", language="en", use_spacy=False).source_replacements
    )
    assert any(
        item.rule == "sequence.isbn"
        for item in prepare("ISBN 978-3-16-148410-0", language="en", use_spacy=False).source_replacements
    )


def test_contextual_years_and_decades_do_not_claim_identifiers() -> None:
    for source in ("in 1858", "since 1972", "until 1994"):
        result = prepare(source, language="en", use_spacy=False)
        assert any(item.rule == "sequence.year" for item in result.source_replacements)
    decade = prepare("Late 1830s", language="en", use_spacy=False)
    assert decade.spoken_text == "Late eighteen thirties"
    assert any(item.rule in {"en.decade", "sequence.decade"} for item in decade.source_replacements)
    for source in ("PIN 1858", "product code 1858", "192.168.1.1"):
        result = prepare(source, language="en", use_spacy=False)
        assert not any(item.rule in {"sequence.year", "sequence.decade"} for item in result.source_replacements)


def test_reference_and_spanish_time_candidates_respect_context() -> None:
    citation = prepare("3:81 (1881)", language="es", use_spacy=False)
    assert any(item.rule == "sequence.reference" for item in citation.source_replacements)
    assert not any(item.rule == "es.time" for item in citation.source_replacements)
    range_like = prepare("1:16-17", language="es", use_spacy=False)
    assert not any(item.rule == "es.time" for item in range_like.source_replacements)
    explicit = prepare("1:45 p.m.", language="es", use_spacy=False)
    assert any(item.rule == "es.time" for item in explicit.source_replacements)
    assert not any(item.rule == "es.time" for item in prepare("3:81", language="es", use_spacy=False).source_replacements)


def test_spaced_isbn_labels_claim_validated_values_before_phone() -> None:
    result = prepare("i s b n 84-8442-724-2", language="es", use_spacy=False)
    assert sum(item.rule == "sequence.isbn" for item in result.source_replacements) == 2
    phone = prepare("123-456-7890", language="es", use_spacy=False)
    assert any(item.rule == "sequence.phone" for item in phone.source_replacements)
    unlabeled = prepare("84-8442-724-2", language="es", use_spacy=False)
    assert not any(item.rule == "sequence.isbn" for item in unlabeled.source_replacements)


def test_typed_versions_beat_decimal_and_ipv4_without_breaking_protection() -> None:
    for source in ("Python 3.9.7", "GTK+ 2.18.2.30"):
        result = prepare(source, language="en", use_spacy=False)
        assert any(item.rule == "sequence.version" for item in result.source_replacements)
        assert "dot" in result.spoken_text
    ip = prepare("192.168.1.1", language="en", use_spacy=False)
    assert any(item.rule == "sequence.ipv4" for item in ip.source_replacements)
    invalid = prepare("256.1.1.1", language="en", use_spacy=False)
    assert not any(item.rule == "sequence.ipv4" for item in invalid.source_replacements)
    protected = prepare("v3.2.1", language="en", use_spacy=False)
    promoted = prepare("v3.2.1", language="en", normalize_literals=True, use_spacy=False)
    assert protected.spoken_text == "v3.2.1"
    assert promoted.spoken_text != protected.spoken_text


def test_contextual_roman_and_typed_code_ownership_stays_narrow() -> None:
    assert prepare("Artikel IX", language="de", use_spacy=False).spoken_text == "Artikel neun"
    assert prepare("Benedikt XVI.", language="de", use_spacy=False).spoken_text == (
        "Benedikt der Sechzehnte."
    )
    assert prepare("Königin Elisabeth II.", language="de", use_spacy=False).spoken_text == (
        "Königin Elisabeth die Zweite."
    )
    standalone = prepare("IV", language="de", use_spacy=False)
    assert not any(item.rule == "sequence.roman" for item in standalone.source_replacements)
    ticker = prepare("stock MSFT", language="en", use_spacy=False)
    assert any(item.rule == "sequence.ticker" for item in ticker.source_replacements)
    plate = prepare("M-XY 4711", language="en", use_spacy=False)
    assert any(item.rule == "sequence.plate" for item in plate.source_replacements)


def test_safe_symbol_tokens_are_category_aware() -> None:
    assert prepare("t²", language="en", use_spacy=False).spoken_text == "t squared"
    assert prepare("3²", language="en", use_spacy=False).spoken_text == "three squared"
    assert prepare("α", language="en", use_spacy=False).spoken_text == "alpha"
    foreign = prepare("日本語 PlayStation/", language="en", use_spacy=False)
    assert "日本語" in foreign.spoken_text


def test_postal_recognizer_does_not_steal_measurements_or_counts() -> None:
    for source, expected in (
        ("1500 Tonnen", "eintausendfünfhundert Tonnen"),
        ("2024 Punkte", "zweitausendvierundzwanzig Punkte"),
        ("4711 Teilnehmer", "viertausendsiebenhundertelf Teilnehmer"),
    ):
        assert prepare(source, language="de", use_spacy=False).spoken_text == expected

    assert prepare("10115 Berlin", language="de", use_spacy=False).spoken_text == (
        "eins null eins eins fünf Berlin"
    )


def test_legal_and_product_claims_require_typed_evidence() -> None:
    assert prepare("Siehe § 3 BGB.", language="de", use_spacy=False).spoken_text == (
        "Siehe Paragraf drei B G B."
    )
    assert prepare("Nach Berlin fahren.", language="de", use_spacy=False).spoken_text == (
        "Nach Berlin fahren."
    )
    assert prepare("model number is unknown", language="en", use_spacy=False).spoken_text == (
        "model number is unknown"
    )
    assert prepare("Model X7", language="en", use_spacy=False).spoken_text == "model X seven"


def test_locale_numeric_policies_are_selected_before_separator_heuristics() -> None:
    assert prepare("42,195 km", language="de_DE", use_spacy=False).spoken_text == (
        "zweiundvierzig Komma eins neun fünf Kilometer"
    )
    assert prepare("3,000", language="es_MX", use_spacy=False).spoken_text == "tres mil"
    assert (
        prepare("45,000", language="es_MX", use_spacy=False).spoken_text == "cuarenta y cinco mil"
    )
    assert (
        prepare("1.75", language="es_MX", use_spacy=False).spoken_text
        == "uno punto setenta y cinco"
    )


def test_typed_and_contextual_renderers_do_not_use_global_code_rules() -> None:
    assert prepare("ISBN 978-3-16-148410-0", language="en", use_spacy=False).spoken_text.startswith(
        "I S B N nine seven eight"
    )
    assert prepare("Chapter IIX", language="en", use_spacy=False).spoken_text == "Chapter IIX"
    assert (
        prepare("Heinrich VIII.", language="de", use_spacy=False).spoken_text
        == "Heinrich der Achte."
    )
    assert prepare("√9 = 3", language="es", use_spacy=False).spoken_text == (
        "raíz cuadrada de nueve igual a tres"
    )
    assert prepare("E. coli strain K-12", language="en", use_spacy=False).spoken_text == (
        "e coli strain K twelve"
    )


def test_typed_locale_numeric_cleanup_is_contextual() -> None:
    assert prepare("1,80 m", language="de", use_spacy=False).spoken_text == ("ein Meter achtzig")
    assert prepare("Código postal 03900", language="es", use_spacy=False).spoken_text == (
        "Código postal cero tres nueve cero cero"
    )
    assert prepare("16.00%", language="es", use_spacy=False).spoken_text == ("dieciséis por ciento")
    assert prepare("15ª", language="it", use_spacy=False).spoken_text == "quindicesima"
