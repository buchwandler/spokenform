"""High-confidence atomic recognizers for structured character sequences."""

from __future__ import annotations

import re
from collections.abc import Iterable
from fractions import Fraction

from num2words import num2words

from ..language import base_language, normalize_language, resolve_num2words_language
from ..mapping import Replacement
from ..sequences import render_sequence


_FRACTION_CHARS = "½⅓⅔¼¾⅛⅜⅝⅞"
_FRACTION_RE = re.compile(rf"(?<!\w)(?P<whole>\d+)?(?P<fraction>[{_FRACTION_CHARS}])(?!\w)")
_COORDINATE_RE = re.compile(
    r"(?<!\w)(?P<value>[+-]?\d+(?:[.,]\d+))\s*°\s*(?P<direction>[NSEW])\b",
    re.IGNORECASE,
)
_ISBN_RE = re.compile(
    r"(?<!\w)(?P<label>ISBN(?:-1[03])?)(?:\s+|:)(?P<value>(?:97[89][ -]?)?\d(?:[\d -]*\d|X|x))(?!\w)",
    re.IGNORECASE,
)
_UUID_RE = re.compile(
    r"(?<![\w-])(?P<value>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})(?![\w-])"
)
_IPV4_RE = re.compile(
    r"(?<![\w.])(?P<value>\d{1,3}(?:\.\d{1,3}){3})(?![\w.])"
)
_MAC_RE = re.compile(
    r"(?<![\w:])(?P<value>(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2})(?![\w:])"
)
_IBAN_RE = re.compile(
    r"(?<!\w)(?P<value>[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]){11,32})(?!\w)", re.IGNORECASE
)
_PHONE_RE = re.compile(
    r"(?<![\w,.])(?P<value>\+?[0-9][0-9 ()/.\-]{5,}[0-9])(?!\w)"
)
_VERSION_CONTEXT_RE = re.compile(
    r"(?P<label>\b(?:version|release|ver\.?|build)\s*[=:]?\s*)(?P<value>v?\d+(?:\.\d+){2,}(?:[a-z]+\d*)?)",
    re.IGNORECASE,
)
_HASHTAG_RE = re.compile(r"(?<!\w)#(?P<value>[\wÀ-ž]+)", re.UNICODE)
_MENTION_RE = re.compile(r"(?<!\w)@(?P<value>[\wÀ-ž]+)", re.UNICODE)
_FORMULA_RE = re.compile(
    r"(?<!\w)(?P<value>(?:[A-Z][a-z]?(?:[0-9₀-₉]+)?|\([A-Z][a-z]?(?:[0-9₀-₉]+)?\))+)(?!\w)"
)
_ACRONYM_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]{2,8})(?!\w)")
_TICKER_RE = re.compile(r"(?<!\w)\$(?P<value>[A-Z]{1,5})(?!\w)")
_PRODUCT_RE = re.compile(
    r"(?P<label>SN|S/N|Serial|SKU|Model|VIN|IMEI|ICCID|Part(?:\s+number)?|Product(?:\s+code)?)\s*(?:[:#]\s*|\s+)(?P<value>[A-Za-z0-9][A-Za-z0-9-]{2,})",
    re.IGNORECASE,
)
_LEGAL_RE = re.compile(
    r"(?<!\w)(?P<value>(?:§|Art\.?|Artikel)\s*\d+(?:\s+[IVXLCDM]+)?(?:\s+\d+)?\s+[A-ZÄÖÜ]{2,})(?!\w)",
    re.IGNORECASE,
)
_SPORTS_RE = re.compile(
    r"(?P<context>\b(?:score|final|match|football|basketball|handball|volleyball|set|satz)\b[^\d]{0,24})(?P<value>\d{1,2}:\d{1,2})",
    re.IGNORECASE,
)
_ADDRESS_SUFFIX_RE = re.compile(
    r"(?<!\w)(?P<number>\d{1,4})(?P<suffix>[A-Za-z])\s+(?P<street>[A-ZÄÖÜ][\wÄÖÜäöüß.-]*(?:\s+(?:St\.?|Street|Ave\.?|Avenue|Rd\.?|Road|Blvd\.?))?)(?!\w)",
)

_FRACTIONS: dict[str, Fraction] = {
    "½": Fraction(1, 2),
    "⅓": Fraction(1, 3),
    "⅔": Fraction(2, 3),
    "¼": Fraction(1, 4),
    "¾": Fraction(3, 4),
    "⅛": Fraction(1, 8),
    "⅜": Fraction(3, 8),
    "⅝": Fraction(5, 8),
    "⅞": Fraction(7, 8),
}
_FRACTION_WORDS = {
    "en": {Fraction(1, 2): "one half", Fraction(1, 3): "one third", Fraction(2, 3): "two thirds", Fraction(1, 4): "one quarter", Fraction(3, 4): "three quarters", Fraction(1, 8): "one eighth", Fraction(3, 8): "three eighths", Fraction(5, 8): "five eighths", Fraction(7, 8): "seven eighths"},
    "de": {Fraction(1, 2): "einhalb", Fraction(1, 3): "ein Drittel", Fraction(2, 3): "zwei Drittel", Fraction(1, 4): "ein Viertel", Fraction(3, 4): "drei Viertel", Fraction(1, 8): "ein Achtel", Fraction(3, 8): "drei Achtel", Fraction(5, 8): "fünf Achtel", Fraction(7, 8): "sieben Achtel"},
    "es": {Fraction(1, 2): "un medio", Fraction(1, 3): "un tercio", Fraction(2, 3): "dos tercios", Fraction(1, 4): "un cuarto", Fraction(3, 4): "tres cuartos", Fraction(1, 8): "un octavo", Fraction(3, 8): "tres octavos", Fraction(5, 8): "cinco octavos", Fraction(7, 8): "siete octavos"},
    "fr": {Fraction(1, 2): "un demi", Fraction(1, 3): "un tiers", Fraction(2, 3): "deux tiers", Fraction(1, 4): "un quart", Fraction(3, 4): "trois quarts", Fraction(1, 8): "un huitième", Fraction(3, 8): "trois huitièmes", Fraction(5, 8): "cinq huitièmes", Fraction(7, 8): "sept huitièmes"},
}
_WORD_ACRONYMS = {
    "NASA": "nasa",
    "UNO": "uno",
    "FIFA": "fifa",
    "UNESCO": "unesco",
    "NATO": "nato",
}
_ROMAN_ONLY = re.compile(r"^[IVXLCDM]+$")
_LEXICAL_UPPERCASE = frozenset({"API", "URL", "ISBN", "CHF", "EUR", "USD", "GBP", "HTTP", "HTTPS"})


def _cardinal(value: int, language: str) -> str:
    return str(num2words(value, lang=resolve_num2words_language(language)))


def _digitwise(value: str, language: str) -> str:
    return render_sequence(value, language=language, digit_mode="digitwise")


def _punctuated(value: str, language: str) -> str:
    return render_sequence(value, language=language, digit_mode="digitwise")


def _fraction_text(whole: str | None, symbol: str, language: str) -> str:
    base = base_language(language)
    fraction = _FRACTIONS[symbol]
    fraction_text = _FRACTION_WORDS.get(base, _FRACTION_WORDS["en"]).get(fraction, symbol)
    if whole is None:
        return fraction_text
    return f"{_cardinal(int(whole), language)} {fraction_text}"


def _coordinate_text(value: str, direction: str, language: str) -> str:
    normalized = value.replace(",", ".")
    integer, fraction = normalized.lstrip("+-").split(".", 1)
    sign = "minus " if normalized.startswith("-") else "plus " if normalized.startswith("+") else ""
    decimal_word = {"de": "Punkt", "es": "coma", "fr": "virgule", "it": "virgola", "pt": "vírgula", "cs": "celá"}.get(base_language(language), "point")
    direction_words = {
        "en": {"N": "north", "S": "south", "E": "east", "W": "west"},
        "de": {"N": "Nord", "S": "Süd", "E": "Ost", "W": "West"},
        "es": {"N": "norte", "S": "sur", "E": "este", "W": "oeste"},
        "fr": {"N": "nord", "S": "sud", "E": "est", "W": "ouest"},
    }.get(base_language(language), {"N": "north", "S": "south", "E": "east", "W": "west"})
    degree = {"de": "Grad", "fr": "degrés", "es": "grados", "it": "gradi"}.get(base_language(language), "degrees")
    return f"{sign}{_cardinal(int(integer), language)} {decimal_word} {_digitwise(fraction, language)} {degree} {direction_words[direction.upper()]}"


def _claimed(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return not any(start < right and left < end for left, right in protected)


def _phone_is_plausible(value: str) -> bool:
    digits = re.sub(r"\D", "", value)
    if (
        re.fullmatch(r"\d{1,2}[./]\d{1,2}[./]\d{2,4}", value)
        or re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", value)
        or re.fullmatch(r"\d{1,2}:\d{2}", value)
        or ":" in value
        or "," in value
        or ("." in value and not value.startswith("+"))
    ):
        return False
    return len(digits) >= 7 and (value.startswith("+") or bool(re.search(r"[ ()/.-]", value)))


def _marker_text(marker: str, value: str, language: str) -> str:
    marker_words = {"#": {"de": "Hashtag", "fr": "hashtag", "es": "hashtag"}, "@": {"de": "at", "fr": "arobase", "es": "arroba"}}
    marker_name = marker_words.get(marker, {}).get(base_language(language), "hashtag" if marker == "#" else "at")
    return f"{marker_name} {render_sequence(value, language=language)}"


def _formula_is_plausible(value: str) -> bool:
    tokens = re.findall(r"[A-Z][a-z]?", value)
    return len(tokens) >= 2 and bool(re.search(r"[a-z]", value) or re.search(r"[0-9₀-₉]", value))


def _acronym_text(value: str, language: str) -> str:
    return _WORD_ACRONYMS.get(value, render_sequence(value, language=language))


def _score_text(value: str, language: str) -> str:
    left, right = value.split(":")
    connector = {"de": "zu", "es": "a", "fr": "à", "it": "a"}.get(base_language(language), "to")
    return f"{_cardinal(int(left), language)} {connector} {_cardinal(int(right), language)}"


def _legal_text(value: str, language: str) -> str:
    match = re.match(
        r"(?:§|Art\.?|Artikel)\s*(\d+)(?:\s+([IVXLCDM]+))?(?:\s+(\d+))?\s+([A-ZÄÖÜ]{2,})$",
        value,
        re.IGNORECASE,
    )
    if not match:
        return render_sequence(value, language=language)
    heading = "paragraph" if value.lstrip().startswith("§") else "article"
    result = [heading, _cardinal(int(match.group(1)), language)]
    for group in match.groups()[1:3]:
        if group:
            result.append(_cardinal(int(group), language) if group.isdigit() else render_sequence(group, language=language))
    result.append(render_sequence(match.group(4), language=language))
    return " ".join(result)


def _address_text(number: str, suffix: str, street: str, language: str) -> str:
    return f"{render_sequence(number, language=language)} {render_sequence(suffix, language=language)} {street}"


def _add(candidates: list[Replacement], match: re.Match[str], value: str, language: str, rule: str, protected: tuple[tuple[int, int], ...]) -> None:
    if _claimed(match.start(), match.end(), protected):
        candidates.append(Replacement(match.start(), match.end(), value, "structured", language, rule))


def iter_sequence_replacements(
    text: str,
    *,
    language: str = "en",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Recognize and render high-confidence atomic structured sequences."""
    language = normalize_language(language)
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []
    for match in _FRACTION_RE.finditer(text):
        _add(candidates, match, _fraction_text(match["whole"], match["fraction"], language), language, "sequence.fraction", protected)
    for match in _COORDINATE_RE.finditer(text):
        _add(candidates, match, _coordinate_text(match["value"], match["direction"], language), language, "sequence.coordinate", protected)
    for match in _ISBN_RE.finditer(text):
        label = render_sequence(match["label"], language=language)
        _add(candidates, match, f"{label} {_punctuated(match['value'], language)}", language, "sequence.isbn", protected)
    for match in _UUID_RE.finditer(text):
        _add(candidates, match, _punctuated(match["value"], language), language, "sequence.uuid", protected)
    for match in _IPV4_RE.finditer(text):
        octets = match["value"].split(".")
        if all(int(octet) <= 255 for octet in octets):
            _add(candidates, match, _punctuated(match["value"], language), language, "sequence.ipv4", protected)
    for match in _MAC_RE.finditer(text):
        _add(candidates, match, _punctuated(match["value"], language), language, "sequence.mac", protected)
    for match in _IBAN_RE.finditer(text):
        _add(candidates, match, _punctuated(match["value"].replace(" ", ""), language), language, "sequence.iban", protected)
    for match in _PHONE_RE.finditer(text):
        if _phone_is_plausible(match["value"]):
            _add(candidates, match, _punctuated(match["value"], language), language, "sequence.phone", protected)
    for match in _VERSION_CONTEXT_RE.finditer(text):
        value = match["value"]
        start, end = match.start("value"), match.end("value")
        if not value.casefold().startswith("v") and _claimed(start, end, protected):
            candidates.append(Replacement(start, end, _punctuated(value, language), "structured", language, "sequence.version"))
    for pattern, marker, rule in ((_HASHTAG_RE, "#", "sequence.hashtag"), (_MENTION_RE, "@", "sequence.mention")):
        for match in pattern.finditer(text):
            _add(candidates, match, _marker_text(marker, match["value"], language), language, rule, protected)
    for match in _FORMULA_RE.finditer(text):
        if _formula_is_plausible(match["value"]):
            _add(candidates, match, render_sequence(match["value"], language=language), language, "sequence.formula", protected)
    for match in _TICKER_RE.finditer(text):
        value = f"dollar {render_sequence(match['value'], language=language)}"
        _add(candidates, match, value, language, "sequence.ticker", protected)
    for match in _PRODUCT_RE.finditer(text):
        label = render_sequence(match["label"].replace("/", ""), language=language)
        value = render_sequence(match["value"], language=language)
        _add(candidates, match, f"{label} {value}", language, "sequence.product", protected)
    for match in _ACRONYM_RE.finditer(text):
        value = match["value"]
        if value in _WORD_ACRONYMS or (
            value not in _LEXICAL_UPPERCASE
            and len(value) <= 6
            and not _ROMAN_ONLY.fullmatch(value)
        ):
            _add(candidates, match, _acronym_text(value, language), language, "sequence.acronym", protected)
    for match in _LEGAL_RE.finditer(text):
        _add(candidates, match, _legal_text(match["value"], language), language, "sequence.legal", protected)
    for match in _SPORTS_RE.finditer(text):
        start, end = match.start("value"), match.end("value")
        if _claimed(start, end, protected):
            candidates.append(Replacement(start, end, _score_text(match["value"], language), "structured", language, "sequence.sports"))
    for match in _ADDRESS_SUFFIX_RE.finditer(text):
        _add(candidates, match, _address_text(match["number"], match["suffix"], match["street"], language), language, "sequence.address", protected)
    return tuple(candidates)


__all__ = ["iter_sequence_replacements"]
