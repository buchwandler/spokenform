"""High-confidence atomic recognizers for structured character sequences."""

from __future__ import annotations

import re
from collections.abc import Iterable
from fractions import Fraction

from num2words import num2words

from ..language import base_language, normalize_language, resolve_num2words_language
from ..mapping import Replacement
from ..sequences import render_letters, render_sequence

_FRACTION_CHARS = "½⅓⅔¼¾⅛⅜⅝⅞"
_FRACTION_RE = re.compile(rf"(?<!\w)(?P<whole>\d+)?(?P<fraction>[{_FRACTION_CHARS}])(?!\w)")
_COORDINATE_RE = re.compile(
    r"(?<!\w)(?P<value>[+-]?\d+(?:[.,]\d+)?)\s*°(?:\s*(?P<direction>[NSEW])\b)?(?!\s*[CF]\b)",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(
    r"(?<!\w)(?P<value>[+\-−]?(?:\d+(?:[.,]\d+)?|[.,]\d+))\s*%(?!\w)"
)
_COMPOUND_UNIT_RE = re.compile(
    r"(?<!\w)(?P<number>[+\-−]?\d+(?:[.,]\d+)?)?\s*(?P<unit>g/cm(?:³|3)|mol/l)(?!\w)",
    re.IGNORECASE,
)
_CURRENCY_SYMBOL_RE = re.compile(
    r"(?<!\w)(?:(?P<prefix>[€$£])\s*)?(?P<number>[+\-−]?(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{1,2})?)\s*(?P<suffix>[€$£])?(?!\w)"
)
_CURRENCY_MAGNITUDE_RE = re.compile(
    r"(?<!\w)(?P<symbol>[€$£])\s*(?P<number>[+\-−]?\d+(?:[.,]\d+)?)\s+(?P<magnitude>thousand|million|billion|tausend|million(?:en)?|milliard(?:en)?|mil|millón(?:es)?|milli(?:one|ardi)?)(?!\w)",
    re.IGNORECASE,
)
_ISBN_RE = re.compile(
    r"(?<!\w)(?P<label>ISBN(?:-1[03])?)(?:\s+|:)(?P<value>(?:97[89][ -]?)?\d(?:[\d -]*\d|X|x))(?!\w)",
    re.IGNORECASE,
)
_CODE_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]{2,8}-\d{2,8}(?:-[A-Z0-9]{1,8})*)(?!\w)")
_PLATE_RE = re.compile(r"(?<!\w)(?P<value>[A-Z]{2,3}\d{1,4}[A-Z]{1,3})(?!\w)")
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
_EMERGENCY_RE = re.compile(
    r"\b(?:call|dial|emergency|notruf|emergencia|urgence|emergenza)\s+(?P<value>110|112|911|999)\b",
    re.IGNORECASE,
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
_ADDRESS_RE = re.compile(
    r"(?<!\w)(?P<street>(?:[A-ZÄÖÜÀ-Ý][\wÄÖÜäöüßÀ-ÿ.-]*(?:straße|strasse|platz)|[A-ZÄÖÜÀ-Ý][\wÄÖÜäöüßÀ-ÿ.-]*\s+(?:Street|Road|Avenue|Ave\.?|Rd\.?|Blvd\.?)))\s+"
    r"(?P<number>\d{1,4})(?P<suffix>[A-Za-z])?(?:\s*[-–]\s*(?P<range>\d{1,4}))?(?:\s*/\s*(?P<slash>\d{1,4}))?(?!\w)",
    re.IGNORECASE,
)
_POSTBOX_RE = re.compile(r"\b(?P<label>Postfach|P\.O\.\s*Box)\s+(?P<number>\d{1,6})\b", re.IGNORECASE)
_FLOOR_RE = re.compile(r"(?<!\w)(?P<number>\d{1,2})\.\s*(?P<label>OG|Stockwerk)\b", re.IGNORECASE)
_POSTAL_CITY_RE = re.compile(
    r"(?<!\w)(?P<postal>\d{5})\s+(?P<city>[A-ZÄÖÜÀ-Ý][\wÄÖÜäöüßÀ-ÿ-]+)(?!\w)",
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


def _coordinate_is_valid(value: str, direction: str | None) -> bool:
    try:
        numeric = abs(float(value.replace(",", ".")))
    except ValueError:
        return False
    if direction is None:
        return True
    limit = 90 if direction.upper() in {"N", "S"} else 180
    return numeric <= limit


def _coordinate_text(value: str, direction: str | None, language: str) -> str:
    normalized = value.replace(",", ".")
    unsigned = normalized.lstrip("+-")
    integer, _, fraction = unsigned.partition(".")
    sign = "minus " if normalized.startswith("-") else "plus " if normalized.startswith("+") else ""
    base = base_language(language)
    decimal_word = {
        "cs": "celá",
        "de": "Komma",
        "es": "coma",
        "fr": "virgule",
        "it": "virgola",
        "pt": "vírgula",
    }.get(base, "point")
    direction_words = {
        "en": {"N": "north", "S": "south", "E": "east", "W": "west"},
        "de": {"N": "Nord", "S": "Süd", "E": "Ost", "W": "West"},
        "es": {"N": "norte", "S": "sur", "E": "este", "W": "oeste"},
        "fr": {"N": "nord", "S": "sud", "E": "est", "W": "ouest"},
        "it": {"N": "nord", "S": "sud", "E": "est", "W": "ovest"},
        "pt": {"N": "norte", "S": "sul", "E": "leste", "W": "oeste"},
        "cs": {"N": "sever", "S": "jih", "E": "východ", "W": "západ"},
    }.get(base_language(language), {"N": "north", "S": "south", "E": "east", "W": "west"})
    degree = {
        "cs": "stupňů",
        "de": "Grad",
        "es": "grados",
        "fr": "degrés",
        "it": "gradi",
        "pt": "graus",
    }.get(base, "degrees")
    result = f"{sign}{_cardinal(int(integer), language)}"
    if fraction:
        result += f" {decimal_word} {_digitwise(fraction, language)}"
    result += f" {degree}"
    if direction:
        result += f" {direction_words[direction.upper()]}"
    return result


def _decimal_parts(raw: str, language: str) -> tuple[bool, int, str | None]:
    normalized = raw.replace("−", "-")
    negative = normalized.startswith("-")
    unsigned = normalized.lstrip("+-")
    base = base_language(language)
    decimal_separator = "," if base in {"cs", "de", "es", "fr", "it", "pt"} else "."
    if "," in unsigned and "." in unsigned:
        separator = "," if unsigned.rfind(",") > unsigned.rfind(".") else "."
        integer, fraction = unsigned.rsplit(separator, 1)
        integer = integer.replace(",", "").replace(".", "")
    elif decimal_separator in unsigned:
        integer, fraction = unsigned.split(decimal_separator, 1)
        if len(fraction) > 2 and len(integer) <= 3:
            integer, fraction = unsigned.replace(decimal_separator, ""), None
    elif decimal_separator == "," and "." in unsigned:
        integer, fraction = unsigned.rsplit(".", 1)
        if len(fraction) > 2:
            integer, fraction = unsigned.replace(".", ""), None
    else:
        integer, fraction = unsigned, None
    integer = re.sub(r"[.,]", "", integer) or "0"
    return negative, int(integer), fraction


def _decimal_text(raw: str, language: str) -> str:
    negative, integer, fraction = _decimal_parts(raw, language)
    base = base_language(language)
    decimal_word = {
        "cs": "celá", "de": "Komma", "es": "coma", "fr": "virgule",
        "it": "virgola", "pt": "vírgula",
    }.get(base, "point")
    value = _cardinal(integer, language)
    if fraction:
        value += f" {decimal_word} {_digitwise(fraction, language)}"
    return f"minus {value}" if negative else value


def _percent_text(raw: str, language: str) -> str:
    names = {
        "cs": "procent", "de": "Prozent", "en": "percent", "es": "por ciento",
        "fr": "pour cent", "it": "percento", "pt": "por cento",
    }
    return f"{_decimal_text(raw, language)} {names.get(base_language(language), 'percent')}"


def _currency_symbol_text(raw: str, symbol: str, language: str) -> str:
    base = base_language(language)
    names = {
        "€": {"de": "Euro", "en": "euro", "es": "euros", "fr": "euros", "it": "euro", "pt": "euros", "cs": "euro"},
        "$": {"de": "Dollar", "en": "dollar", "es": "dólares", "fr": "dollars", "it": "dollari", "pt": "dólares", "cs": "dolar"},
        "£": {"de": "Pfund", "en": "pounds", "es": "libras", "fr": "livres", "it": "sterline", "pt": "libras", "cs": "libry"},
    }
    minor_names = {"de": "Cent", "en": "cents", "es": "centavos", "fr": "centimes", "it": "centesimi", "pt": "centavos", "cs": "centů"}
    negative, integer, fraction = _decimal_parts(raw, language)
    major = _cardinal(integer, language)
    if negative:
        major = f"minus {major}"
    currency_name = names[symbol].get(base, names[symbol]["en"])
    if base == "en" and (integer != 1 or fraction):
        currency_name += "s"
    result = f"{major} {currency_name}"
    if fraction:
        minor = int((fraction + "00")[:2])
        if minor:
            result += f" {('und' if base == 'de' else 'and' if base == 'en' else 'e' if base in {'it', 'pt'} else 'con')} {_cardinal(minor, language)} {minor_names.get(base, 'cents')}"
    return result


def _compound_unit_text(number: str | None, unit: str, language: str) -> str:
    base = base_language(language)
    labels = {
        "g/cm³": {"en": "grams per cubic centimeter", "de": "Gramm pro Kubikzentimeter", "es": "gramos por centímetro cúbico", "fr": "grammes par centimètre cube", "it": "grammi per centimetro cubo", "pt": "gramas por centímetro cúbico", "cs": "gramů na centimetr krychlový"},
        "mol/l": {"en": "moles per liter", "de": "Mol pro Liter", "es": "moles por litro", "fr": "moles par litre", "it": "moli per litro", "pt": "moles por litro", "cs": "molů na litr"},
    }
    label = labels[unit.casefold()].get(base, labels[unit.casefold()]["en"])
    return f"{_decimal_text(number, language)} {label}" if number else label


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
            or ("." in value and not re.fullmatch(r"\+?\d{2,4}(?:\.\d{2,4}){1,3}", value))
    ):
        return False
    return len(digits) >= 7 and (value.startswith("+") or bool(re.search(r"[ ()/.-]", value)))


def _marker_text(marker: str, value: str, language: str) -> str:
    marker_words = {
        "#": {
            "cs": "hashtag",
            "de": "Hashtag",
            "en": "hashtag",
            "es": "hashtag",
            "fr": "hashtag",
            "it": "hashtag",
            "pt": "hashtag",
        },
        "@": {
            "cs": "zavináč",
            "de": "at",
            "en": "at",
            "es": "arroba",
            "fr": "arobase",
            "it": "chiocciola",
            "pt": "arroba",
        },
    }
    marker_name = marker_words[marker].get(base_language(language), marker)
    return f"{marker_name} {_render_identifier(value, language)}"


def _identifier_tokens(value: str) -> tuple[tuple[str, str], ...]:
    """Split a social identifier at words, case, digits, and separators."""
    tokens: list[tuple[str, str]] = []
    current: list[str] = []

    def flush() -> None:
        if current:
            token = "".join(current)
            kind = "digit" if token[0].isdigit() else "alpha"
            tokens.append((kind, token))
            current.clear()

    for index, character in enumerate(value):
        if character in "_-" or character.isspace():
            flush()
            continue
        if current and character.isdigit() != current[-1].isdigit():
            flush()
        elif (
            current
            and character.isupper()
            and current[-1].islower()
        ):
            flush()
        elif (
            current
            and character.isupper()
            and current[-1].isupper()
            and index + 1 < len(value)
            and value[index + 1].islower()
        ):
            flush()
        current.append(character)
    flush()
    return tuple(tokens)


def _render_identifier(value: str, language: str) -> str:
    """Render lexical social identifiers without spelling ordinary words."""
    tokens = _identifier_tokens(value)
    alpha = "".join(token for kind, token in tokens if kind == "alpha")
    opaque = bool(alpha) and alpha.isascii() and alpha.isupper() and len(alpha) <= 8
    rendered: list[str] = []
    for kind, token in tokens:
        if kind == "digit":
            rendered.append(_cardinal(int(token), language))
        elif opaque and token.isascii() and token.isupper():
            rendered.append(render_letters(token, language=language))
        else:
            rendered.append(token)
    return " ".join(rendered)


def _formula_is_plausible(value: str) -> bool:
    tokens = re.findall(r"[A-Z][a-z]?", value)
    return len(tokens) >= 2 and bool(re.search(r"[a-z]", value) or re.search(r"[0-9₀-₉]", value))


def _isbn_is_valid(value: str) -> bool:
    compact = re.sub(r"[-\s]", "", value).upper()
    if len(compact) == 10 and re.fullmatch(r"\d{9}[\dX]", compact):
        return sum((10 - index) * (10 if digit == "X" else int(digit)) for index, digit in enumerate(compact)) % 11 == 0
    if len(compact) == 13 and compact.isdigit():
        return sum((1 if index % 2 == 0 else 3) * int(digit) for index, digit in enumerate(compact)) % 10 == 0
    return False


def _formula_text(value: str, language: str) -> str:
    parts: list[str] = []
    for match in re.finditer(r"[A-Z][a-z]?|[()]|[0-9₀-₉]+", value):
        token = match.group(0)
        if token.isdigit() or any(character in "₀₁₂₃₄₅₆₇₈₉" for character in token):
            parts.append(_cardinal(int(token.translate(str.maketrans("₀₁₂₃₄₅₆₇₈₉", "0123456789"))), language))
        elif token in "()":
            parts.append({"(": "open parenthesis", ")": "close parenthesis"}[token])
        else:
            parts.append(render_letters(token, language=language))
    return " ".join(parts)


def _typed_code_text(value: str, language: str) -> str:
    parts: list[str] = []
    for token in re.findall(r"[A-Za-z]+|\d+|[^A-Za-z\d]+", value):
        if token.isdigit():
            parts.append(_digitwise(token, language))
        elif token.isalpha():
            parts.append(render_letters(token, language=language))
        else:
            parts.append(render_sequence(token, language=language))
    return " ".join(parts)


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
    headings = {
        "cs": ("paragraf", "článek"),
        "de": ("Paragraph", "Artikel"),
        "en": ("section", "article"),
        "es": ("párrafo", "artículo"),
        "fr": ("paragraphe", "article"),
        "it": ("paragrafo", "articolo"),
        "pt": ("parágrafo", "artigo"),
    }
    heading_pair = headings.get(base_language(language), headings["en"])
    heading = heading_pair[0] if value.lstrip().startswith("§") else heading_pair[1]
    result = [heading, _cardinal(int(match.group(1)), language)]
    for group in match.groups()[1:3]:
        if group:
            result.append(_cardinal(int(group), language) if group.isdigit() else render_sequence(group, language=language))
    result.append(render_sequence(match.group(4), language=language))
    return " ".join(result)


def _address_text(number: str, suffix: str, street: str, language: str) -> str:
    return f"{render_sequence(number, language=language)} {render_sequence(suffix, language=language)} {street}"


def _street_address_text(match: re.Match[str], language: str) -> str:
    value = _cardinal(int(match["number"]), language)
    if match["suffix"]:
        value += f" {render_letters(match['suffix'], language=language)}"
    if match["range"]:
        value += f" bis {_cardinal(int(match['range']), language)}"
    if match["slash"]:
        separator = {"de": "Schrägstrich", "fr": "barre", "es": "barra", "it": "barra"}.get(base_language(language), "slash")
        value += f" {separator} {_cardinal(int(match['slash']), language)}"
    return f"{match['street']} {value}"


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
    for match in _CURRENCY_MAGNITUDE_RE.finditer(text):
        symbol = match["symbol"]
        value = f"{_decimal_text(match['number'], language)} {match['magnitude']}"
        currency_names = {"€": "euro", "$": "dollars", "£": "pounds"}
        _add(
            candidates,
            match,
            f"{value} {currency_names[symbol]}",
            language,
            "sequence.currency-magnitude",
            protected,
        )
    for match in _CURRENCY_SYMBOL_RE.finditer(text):
        symbol = match["prefix"] or match["suffix"]
        if symbol and base_language(language) in {"de", "it"}:
            _add(
                candidates,
                match,
                _currency_symbol_text(match["number"], symbol, language),
                language,
                "sequence.currency",
                protected,
            )
    for match in _PERCENT_RE.finditer(text):
        _add(
            candidates,
            match,
            _percent_text(match["value"], language),
            language,
            "sequence.percent",
            protected,
        )
    for match in _COMPOUND_UNIT_RE.finditer(text):
        _add(
            candidates,
            match,
            _compound_unit_text(match["number"], match["unit"], language),
            language,
            "sequence.compound-unit",
            protected,
        )
    for match in _FRACTION_RE.finditer(text):
        _add(candidates, match, _fraction_text(match["whole"], match["fraction"], language), language, "sequence.fraction", protected)
    for match in _COORDINATE_RE.finditer(text):
        direction = match["direction"]
        if _coordinate_is_valid(match["value"], direction):
            _add(
                candidates,
                match,
                _coordinate_text(match["value"], direction, language),
                language,
                "sequence.coordinate",
                protected,
            )
    for match in _ISBN_RE.finditer(text):
        if _isbn_is_valid(match["value"]):
            label = render_sequence(match["label"], language=language)
            _add(candidates, match, f"{label} {_typed_code_text(match['value'], language)}", language, "sequence.isbn", protected)
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
    for match in _EMERGENCY_RE.finditer(text):
        _add(candidates, match, match.group(0).replace(match["value"], _digitwise(match["value"], language)), language, "sequence.emergency", protected)
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
            _add(candidates, match, _formula_text(match["value"], language), language, "sequence.formula", protected)
    for match in _TICKER_RE.finditer(text):
        value = f"dollar {render_sequence(match['value'], language=language)}"
        _add(candidates, match, value, language, "sequence.ticker", protected)
    for match in _PRODUCT_RE.finditer(text):
        label = render_sequence(match["label"].replace("/", ""), language=language)
        value = _typed_code_text(match["value"], language)
        _add(candidates, match, f"{label} {value}", language, "sequence.product", protected)
    for match in _CODE_RE.finditer(text):
        _add(candidates, match, _typed_code_text(match["value"], language), language, "sequence.product", protected)
    for match in _PLATE_RE.finditer(text):
        _add(candidates, match, _typed_code_text(match["value"], language), language, "sequence.plate", protected)
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
    for match in _ADDRESS_RE.finditer(text):
        _add(candidates, match, _street_address_text(match, language), language, "sequence.address", protected)
    for match in _POSTBOX_RE.finditer(text):
        _add(
            candidates,
            match,
            f"{match['label']} {_digitwise(match['number'], language)}",
            language,
            "sequence.address",
            protected,
        )
    for match in _FLOOR_RE.finditer(text):
        label = "Obergeschoss" if base_language(language) == "de" and match["label"].casefold() == "og" else match["label"]
        _add(candidates, match, f"{_cardinal(int(match['number']), language)} {label}", language, "sequence.address", protected)
    if base_language(language) == "de":
        for match in _POSTAL_CITY_RE.finditer(text):
            _add(
                candidates,
                match,
                f"{_digitwise(match['postal'], language)} {match['city']}",
                language,
                "sequence.address",
                protected,
            )
    return tuple(candidates)


__all__ = ["iter_sequence_replacements"]
