"""Locale-aware rendering primitives for atomic structured character sequences.

This module intentionally contains no detection rules.  Recognizers decide
which source span is semantic; these helpers only render an already-claimed
span so identifiers are never accidentally split into generic numbers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal, Mapping

from .language import base_language, normalize_language


@dataclass(frozen=True, slots=True)
class SequenceVocabulary:
    """Spoken names for punctuation in a claimed structured sequence."""

    point: str = "point"
    slash: str = "slash"
    hyphen: str = "hyphen"
    underscore: str = "underscore"
    colon: str = "colon"
    at: str = "at"
    hash: str = "hash"
    plus: str = "plus"
    equals: str = "equals"
    open_paren: str = "open parenthesis"
    close_paren: str = "close parenthesis"


_DIGIT_NAMES: dict[str, tuple[str, ...]] = {
    "en": ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"),
    "de": ("null", "eins", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun"),
    "es": ("cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"),
    "fr": ("zéro", "un", "deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf"),
    "it": ("zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove"),
    "pt": ("zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"),
    "cs": ("nula", "jedna", "dva", "tři", "čtyři", "pět", "šest", "sedm", "osm", "devět"),
}

_LETTER_NAMES: dict[str, tuple[str, ...]] = {
    "en": tuple("A B C D E F G H I J K L M N O P Q R S T U V W X Y Z".lower().split()),
    "de": tuple("A B C D E F G H I J K L M N O P Q R S T U V W X Y Z".split()),
    "es": tuple("a be ce de e efe ge hache i jota ka ele eme ene eñe o pe cu erre ese te u uve dobleuve equis ye zeta".split()),
    "fr": tuple("a bé cé dé e effe gé ache i ji ka elle aime aine o pé ku erre esse té u vé doublevé ikse i grec zède".split()),
    "it": tuple("a bi ci di e effe gi acca i elle emme enne o pi cu erre esse ti u vu doppia vu vi zeta".split()),
    "pt": tuple("a bê cê dê e efe gê agá i jota cá ele eme ene ó pê quê erre esse tê u vê dáblio vê xis ípsilon zê".split()),
    "cs": tuple("a bé cé dé é ef gé há i jé ká el em en ó pé kú er es té ú vé dvojité vé iks ypsilon zet".split()),
}

_SUPERSCRIPT_DIGITS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹", "0123456789")
_SUBSCRIPT_DIGITS = str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789")
_DEFAULT_VOCABULARY = {
    "en": SequenceVocabulary(),
    "de": SequenceVocabulary(point="Punkt", slash="Schrägstrich", hyphen="Bindestrich", underscore="Unterstrich", colon="Doppelpunkt", at="at", hash="Hashtag", plus="plus", equals="gleich", open_paren="öffnende Klammer", close_paren="schließende Klammer"),
    "es": SequenceVocabulary(point="punto", slash="barra", hyphen="guion", underscore="guion bajo", colon="dos puntos", at="arroba", hash="almohadilla", plus="más", equals="igual", open_paren="paréntesis izquierdo", close_paren="paréntesis derecho"),
    "fr": SequenceVocabulary(point="point", slash="barre oblique", hyphen="tiret", underscore="soulignement", colon="deux-points", at="arobase", hash="dièse", plus="plus", equals="égal", open_paren="parenthèse ouvrante", close_paren="parenthèse fermante"),
    "it": SequenceVocabulary(point="punto", slash="barra", hyphen="trattino", underscore="trattino basso", colon="due punti", at="chiocciola", hash="cancelletto", plus="più", equals="uguale", open_paren="parentesi aperta", close_paren="parentesi chiusa"),
    "pt": SequenceVocabulary(point="ponto", slash="barra", hyphen="hífen", underscore="sublinhado", colon="dois-pontos", at="arroba", hash="hashtag", plus="mais", equals="igual", open_paren="parêntese esquerdo", close_paren="parêntese direito"),
    "cs": SequenceVocabulary(point="tečka", slash="lomítko", hyphen="spojovník", underscore="podtržítko", colon="dvojtečka", at="zavináč", hash="mřížka", plus="plus", equals="rovná se", open_paren="levá závorka", close_paren="pravá závorka"),
}


def _language(language: str) -> str:
    base = base_language(normalize_language(language))
    return base if base in _DIGIT_NAMES else "en"


def vocabulary(language: str = "en") -> SequenceVocabulary:
    """Return the default punctuation vocabulary for *language*."""
    return _DEFAULT_VOCABULARY[_language(language)]


def normalize_unicode_digits(text: str) -> str:
    """Convert Unicode superscript/subscript decimal digits to ASCII digits."""
    return text.translate(_SUPERSCRIPT_DIGITS).translate(_SUBSCRIPT_DIGITS)


def render_digits(text: str, *, language: str = "en") -> str:
    """Render each decimal digit individually, preserving leading zeroes."""
    names = _DIGIT_NAMES[_language(language)]
    normalized = normalize_unicode_digits(text)
    return " ".join(names[int(character)] if character.isdigit() else character for character in normalized)


def render_letters(text: str, *, language: str = "en") -> str:
    """Spell alphabetic characters individually using locale vocabulary."""
    names = _LETTER_NAMES[_language(language)]
    normalized = normalize_unicode_digits(text)
    alphabet = "abcdefghijklmnopqrstuvwxyz"
    result: list[str] = []
    for character in normalized:
        folded = character.casefold()
        if folded in alphabet:
            result.append(names[alphabet.index(folded)])
        elif folded == "ñ" and _language(language) == "es":
            result.append("eñe")
        else:
            result.append(character)
    return " ".join(result)


def render_alnum(text: str, *, language: str = "en") -> str:
    """Render an alphanumeric run without converting digit groups to cardinals."""
    parts: list[str] = []
    for character in normalize_unicode_digits(text):
        if character.isdigit():
            parts.append(render_digits(character, language=language))
        elif character.isalpha():
            parts.append(render_letters(character, language=language))
        else:
            parts.append(character)
    return " ".join(parts)


def render_sequence(
    text: str,
    *,
    language: str = "en",
    punctuation: Mapping[str, str | None] | None = None,
    digit_mode: Literal["digitwise", "cardinal"] = "digitwise",
) -> str:
    """Render a claimed sequence with configurable punctuation names."""
    vocab = vocabulary(language)
    names = {
        ".": vocab.point,
        "/": vocab.slash,
        "-": vocab.hyphen,
        "_": vocab.underscore,
        ":": vocab.colon,
        "@": vocab.at,
        "#": vocab.hash,
        "+": vocab.plus,
        "=": vocab.equals,
        "(": vocab.open_paren,
        ")": vocab.close_paren,
    }
    if punctuation:
        names.update(punctuation)
    normalized = normalize_unicode_digits(text)
    if digit_mode == "cardinal":
        # Cardinal mode is intentionally explicit; callers should pass a
        # complete numeric token, never an arbitrary identifier chunk.
        from num2words import num2words

        return str(num2words(int(normalized), lang=language.split("_")[0]))
    rendered: list[str] = []
    for character in normalized:
        if character.isdigit():
            rendered.append(render_digits(character, language=language))
        elif character.isalpha():
            rendered.append(render_letters(character, language=language))
        elif character.isspace():
            continue
        else:
            name = names.get(character)
            if name:
                rendered.append(name)
            elif name is not None:
                continue
            else:
                rendered.append(character)
    return " ".join(rendered)


__all__ = [
    "SequenceVocabulary",
    "normalize_unicode_digits",
    "render_alnum",
    "render_digits",
    "render_letters",
    "render_sequence",
    "vocabulary",
]
