from __future__ import annotations

import pytest

from spokenform import prepare

CASES = [
    (
        "Erwähne @eu_kommission in deinem Tweet.",
        "Erwähne at e u Unterstrich kommission in deinem Tweet.",
    ),
    (
        "Die IP-Adresse ist 192.168.1.1.",
        "Die I P Adresse ist eins neun zwei Punkt eins sechs acht Punkt eins Punkt eins.",
    ),
    (
        "Die IBAN lautet DE89 3704 0044 0532 0130 00.",
        "Die I B A N lautet D E acht neun drei sieben null vier null null vier vier null fünf drei zwei null eins drei null null null.",
    ),
    ("½ + ¼ = ¾", "einhalb plus ein Viertel ist drei Viertel"),
    ("2x + 3 = 15", "zwei x plus drei gleich fünfzehn"),
    (
        "3 × (4 + 5) = 27",
        "drei mal vier plus fünf in Klammern ergibt siebenundzwanzig",
    ),
    ("Die Note ist ein A♯.", "Die Note ist ein Ais."),
    ("Jahrgang MCMLXXXIX", "Jahrgang neunzehnhundertneunundachtzig"),
    ("George VI.", "George der Sechste."),
    ("Im 15. Jh. (XV. Jahrhundert)", "Im fünfzehnten Jahrhundert"),
    (
        "Das Ergebnis lautete 6:3, 6:2 in 1:45 Stunden.",
        "Das Ergebnis lautete sechs zu drei, sechs zu zwei in einer Stunde und fünfundvierzig Minuten.",
    ),
    (
        "Besuchen Sie https://www.beispiel.de",
        "Besuchen Sie h t t p s Doppelpunkt Schrägstrich Schrägstrich w w w Punkt beispiel Punkt d e",
    ),
    ("Meine E-Mail ist info@wort.com", "Meine E-Mail ist info at wort Punkt com"),
    (
        "Die Website ist http://portal.org",
        "Die Website ist h t t p Doppelpunkt Schrägstrich Schrägstrich portal Punkt o r g",
    ),
    (
        "Download unter ftp://files.wörter.net",
        "Download unter f t p Doppelpunkt Schrägstrich Schrägstrich files Punkt wörter Punkt n e t",
    ),
    (
        "Registrieren Sie sich unter https://app.service.com/signup",
        "Registrieren Sie sich unter h t t p s Doppelpunkt Schrägstrich Schrägstrich app Punkt service Punkt com Schrägstrich signup",
    ),
    (
        "Die Dokumente sind auf https://docs.google.com verfügbar",
        "Die Dokumente sind auf h t t p s Doppelpunkt Schrägstrich Schrägstrich docs Punkt google Punkt com verfügbar",
    ),
    (
        "Newsletter: newsletter@findemich.de",
        "Newsletter: newsletter at finde mich Punkt d e",
    ),
    (
        "Der Link ist www.portal.de/login",
        "Der Link ist w w w Punkt portal Punkt d e Schrägstrich login",
    ),
    (
        "Bewerbungen an jobs@unternehmen.com",
        "Bewerbungen an jobs at unternehmen Punkt com",
    ),
    (
        "Forum: https://forum.beispiel.org",
        "Forum: h t t p s Doppelpunkt Schrägstrich Schrägstrich forum Punkt beispiel Punkt o r g",
    ),
    (
        "Die Firmware v3.2.1 behebt Fehler.",
        "Die Firmware Version drei Punkt zwei Punkt eins behebt Fehler.",
    ),
    (
        "Ubuntu 20.04 LTS ist stabil.",
        "Ubuntu zwanzig Punkt null vier L T S ist stabil.",
    ),
    (
        "Das Plugin 1.3.5 ist kompatibel.",
        "Das Plugin eins Punkt drei Punkt fünf ist kompatibel.",
    ),
    (
        "Die Bibliothek v5.2.0 ist verfügbar.",
        "Die Bibliothek Version fünf Punkt zwei Punkt null ist verfügbar.",
    ),
    (
        "Der Treiber v6.4.3 ist empfohlen.",
        "Der Treiber Version sechs Punkt vier Punkt drei ist empfohlen.",
    ),
]


@pytest.mark.parametrize(("source", "expected"), CASES)
def test_german_gold_failure_batch(source: str, expected: str) -> None:
    result = prepare(source, language="de", use_spacy=False, normalize_literals=True)
    assert result.spoken_text == expected


@pytest.mark.parametrize(
    ("source", "rule"),
    [
        ("Die IP-Adresse ist 192.168.1.1.", "sequence.ipv4"),
        ("Die IBAN lautet DE89 3704 0044 0532 0130 00.", "sequence.iban"),
        ("½ + ¼ = ¾", "sequence.math"),
        ("2x + 3 = 15", "sequence.math"),
        ("3 × (4 + 5) = 27", "sequence.math"),
        ("Die Note ist ein A♯.", "sequence.music"),
        ("Jahrgang MCMLXXXIX", "sequence.roman"),
        ("George VI.", "sequence.roman"),
        ("Im 15. Jh. (XV. Jahrhundert)", "de.century"),
        ("Das Ergebnis lautete 6:3, 6:2 in 1:45 Stunden.", "sequence.duration"),
        ("Download unter ftp://files.wörter.net", "sequence.url"),
        ("Die Firmware v3.2.1 behebt Fehler.", "sequence.version"),
        ("Ubuntu 20.04 LTS ist stabil.", "sequence.version"),
    ],
)
def test_german_failure_batch_uses_intended_owner(source: str, rule: str) -> None:
    result = prepare(source, language="de", use_spacy=False, normalize_literals=True)
    assert rule in {replacement.rule for replacement in result.source_replacements}


def test_default_profile_still_protects_literals() -> None:
    source = (
        "URL https://www.beispiel.de und FTP ftp://files.wörter.net und Mail info@wort.com v3.2.1"
    )
    result = prepare(source, language="de", use_spacy=False)
    assert "https://www.beispiel.de" in result.spoken_text
    assert "ftp://files.wörter.net" in result.spoken_text
    assert "info@wort.com" in result.spoken_text
    assert "v3.2.1" in result.spoken_text


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("@eu_kommission", "at e u Unterstrich kommission"),
        ("@EU_kommission", "at E U Unterstrich kommission"),
        ("@ab-test", "at a b test"),
        ("#EU_kommission", "Hashtag EU kommission"),
    ],
)
def test_social_identifier_case_and_separator_policy(source: str, expected: str) -> None:
    result = prepare(source, language="de", use_spacy=False, normalize_literals=True)
    assert result.spoken_text == expected


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("192.168.1.1.", "eins neun zwei Punkt eins sechs acht Punkt eins Punkt eins."),
        ("1:00 Stunden", "einer Stunde"),
        ("1:01 Stunden", "einer Stunde und einer Minute"),
        ("2:05 Stunden", "zwei Stunden und fünf Minuten"),
        ("v1.02.003", "Version eins Punkt null zwei Punkt null null drei"),
    ],
)
def test_german_literal_and_duration_edge_cases(source: str, expected: str) -> None:
    result = prepare(source, language="de", use_spacy=False, normalize_literals=True)
    assert result.spoken_text == expected


def test_iban_precedence_beats_phone_candidate() -> None:
    result = prepare(
        "Die IBAN lautet DE89 3704 0044 0532 0130 00.",
        language="de",
        use_spacy=False,
        normalize_literals=True,
    )
    rules = {replacement.rule for replacement in result.source_replacements}
    assert "sequence.iban" in rules
    assert "sequence.phone" not in rules


@pytest.mark.parametrize(
    ("source", "rule"),
    [
        ("Im 15. Jh. (XIV. Jahrhundert)", "de.century"),
        ("999.1.1.1", "sequence.ipv4"),
        ("1.2.3.4.5", "sequence.ipv4"),
        ("1:45", "sequence.duration"),
        ("1.2.3", "sequence.version"),
        ("A-123", "sequence.math"),
    ],
)
def test_german_failure_batch_negative_ownership(source: str, rule: str) -> None:
    result = prepare(source, language="de", use_spacy=False, normalize_literals=True)
    assert rule not in {replacement.rule for replacement in result.source_replacements}


def test_non_german_music_rendering_remains_locale_specific() -> None:
    result = prepare("The note is A♯.", language="en", use_spacy=False, normalize_literals=True)
    assert result.spoken_text == "The note is a sharp."
