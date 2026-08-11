"""Italian semantic grammar owned by spokenform.

``abbr2words`` recognizes the written symbol and returns its canonical
identity. This module owns the Italian number agreement and semantic wording.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from abbr2words import UnitMatch, iter_unit_matches
from num2words import num2words

from ..config import NumberPolicy
from ..dates import expand_year
from ..language import resolve_abbr2words_language, resolve_num2words_language
from ..mapping import Replacement
from ..numeric_lexeme import parse_numeric_lexeme

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN


@dataclass(frozen=True, slots=True)
class QuantityGrammar:
    canonical_id: str
    singular: str
    plural: str
    article: str = "un"


QUANTITY_GRAMMAR: dict[str, QuantityGrammar] = {
    "duration-second": QuantityGrammar("duration-second", "secondo", "secondi"),
    "duration-minute": QuantityGrammar("duration-minute", "minuto", "minuti"),
    "duration-hour": QuantityGrammar("duration-hour", "ora", "ore", "un'"),
    "duration-day": QuantityGrammar("duration-day", "giorno", "giorni"),
    "length-millimeter": QuantityGrammar("length-millimeter", "millimetro", "millimetri"),
    "length-centimeter": QuantityGrammar("length-centimeter", "centimetro", "centimetri"),
    "length-meter": QuantityGrammar("length-meter", "metro", "metri"),
    "length-kilometer": QuantityGrammar("length-kilometer", "chilometro", "chilometri"),
    "volume-milliliter": QuantityGrammar("volume-milliliter", "millilitro", "millilitri"),
    "volume-liter": QuantityGrammar("volume-liter", "litro", "litri"),
    "mass-microgram": QuantityGrammar("mass-microgram", "microgrammo", "microgrammi"),
    "mass-milligram": QuantityGrammar("mass-milligram", "milligrammo", "milligrammi"),
    "mass-gram": QuantityGrammar("mass-gram", "grammo", "grammi"),
    "mass-kilogram": QuantityGrammar("mass-kilogram", "chilogrammo", "chilogrammi"),
    "mass-tonne": QuantityGrammar("mass-tonne", "tonnellata", "tonnellate", "una"),
    "temperature-kelvin": QuantityGrammar("temperature-kelvin", "kelvin", "kelvin"),
    "area-square-millimeter": QuantityGrammar(
        "area-square-millimeter", "millimetro quadrato", "millimetri quadrati"
    ),
    "area-square-centimeter": QuantityGrammar(
        "area-square-centimeter", "centimetro quadrato", "centimetri quadrati"
    ),
    "area-square-meter": QuantityGrammar("area-square-meter", "metro quadrato", "metri quadrati"),
    "area-square-kilometer": QuantityGrammar(
        "area-square-kilometer", "chilometro quadrato", "chilometri quadrati"
    ),
    "area-hectare": QuantityGrammar("area-hectare", "ettaro", "ettari"),
    "volume-cubic-millimeter": QuantityGrammar(
        "volume-cubic-millimeter", "millimetro cubo", "millimetri cubi"
    ),
    "volume-cubic-centimeter": QuantityGrammar(
        "volume-cubic-centimeter", "centimetro cubo", "centimetri cubi"
    ),
    "volume-cubic-meter": QuantityGrammar("volume-cubic-meter", "metro cubo", "metri cubi"),
    "speed-meter-per-second": QuantityGrammar(
        "speed-meter-per-second", "metro al secondo", "metri al secondo"
    ),
    "speed-kilometer-per-hour": QuantityGrammar(
        "speed-kilometer-per-hour", "chilometro all'ora", "chilometri all'ora"
    ),
}
QUANTITY_GRAMMAR.update(
    {
        "data-byte": QuantityGrammar("data-byte", "byte", "byte"),
        "data-kilobyte": QuantityGrammar("data-kilobyte", "kilobyte", "kilobyte"),
        "data-megabyte": QuantityGrammar("data-megabyte", "megabyte", "megabyte"),
        "data-gigabyte": QuantityGrammar("data-gigabyte", "gigabyte", "gigabyte"),
        "flow-cubic-meter-per-second": QuantityGrammar("flow-cubic-meter-per-second", "metro cubo al secondo", "metri cubi al secondo"),
        "fuel-consumption-liter-per-100-kilometer": QuantityGrammar("fuel-consumption-liter-per-100-kilometer", "litro per cento chilometri", "litri per cento chilometri"),
        "pressure-atmosphere": QuantityGrammar("pressure-atmosphere", "atmosfera", "atmosfere", "un'"),
        "pressure-kilopascal": QuantityGrammar("pressure-kilopascal", "chilopascal", "chilopascal"),
        "pressure-pascal": QuantityGrammar("pressure-pascal", "pascal", "pascal"),
        "speed-mile-per-hour": QuantityGrammar("speed-mile-per-hour", "miglio all'ora", "miglia all'ora"),
    }
)

_DATE_DMY = re.compile(r"(?<![\w.])(?P<day>\d{1,2})[./-](?P<month>\d{1,2})[./-](?P<year>\d{4})(?!\d)")
_DATE_ISO = re.compile(r"(?<![\w.])(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})(?!\d)")
_DATE_DMY_SHORT = re.compile(r"(?<![\w.])(?P<day>\d{1,2})[./-](?P<month>\d{1,2})[./-](?P<year>\d{2})(?!\d)")
_MONTHS = (
    "gennaio",
    "febbraio",
    "marzo",
    "aprile",
    "maggio",
    "giugno",
    "luglio",
    "agosto",
    "settembre",
    "ottobre",
    "novembre",
    "dicembre",
)
_TEXT_DATE = re.compile(
    r"(?P<day>\d{1,2})\s+(?P<month>gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre|gen\.?|feb\.?|mar\.?|apr\.?|mag\.?|giu\.?|lug\.?|ago\.?|set\.?|ott\.?|nov\.?|dic\.?)\s*(?P<year>\d{2,4})?",
    re.IGNORECASE,
)
_ORDINAL_SYMBOL = re.compile(
    r"(?<![\w.])(?P<number>\d+)(?:\.?[ºª°])(?!\s*[CF]\b)(?!\w)", re.IGNORECASE
)
_TIME_COLON = re.compile(r"(?<!\w)(?P<hour>\d{1,2}):(?P<minute>[0-5]\d)(?!\w)")


def _parts(raw: str) -> tuple[bool, int, str | None]:
    lexeme = parse_numeric_lexeme(raw, "it", context="quantity")
    if lexeme is None:
        raise ValueError(f"Cannot parse Italian number {raw!r}")
    return lexeme.negative, int(lexeme.integer_digits), lexeme.fraction_digits


def _decimal(raw: str) -> Decimal:
    negative, integer, fraction = _parts(raw)
    normalized = f"{'-' if negative else ''}{integer}"
    if fraction is not None:
        normalized += f".{fraction}"
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Cannot parse Italian number {raw!r}") from exc


def _spell(value: int, language: str = "it") -> str:
    return str(num2words(value, lang=resolve_num2words_language(language)))


def _number_text(
    raw: str, *, singular_article: str | None = None, language: str = "it"
) -> str:
    negative, integer, fraction = _parts(raw)
    if fraction is None:
        result = _spell(integer, language)
        if integer == 1 and singular_article is not None:
            result = singular_article
    else:
        result = f"{_spell(integer, language)} virgola " + " ".join(
            _spell(int(digit), language) for digit in fraction
        )
    return f"meno {result}" if negative else result


def _valid_date(day: int, month: int, year: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _date_text(day: int, month: int, year: int, language: str = "it") -> str:
    return f"{_spell(day, language)} {_MONTHS[month - 1]} {_spell(year, language)}"


def _time_text(hour: int, minute: int, language: str = "it") -> str:
    hour_text = _spell(hour, language)
    return hour_text if minute == 0 else f"{hour_text} e {_spell(minute, language)}"


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \t\n\"'”’»)]}")


def _quantity_text(match: UnitMatch, text: str, language: str = "it") -> str | None:
    canonical_id = match.canonical_id or ""
    if canonical_id.startswith("currency-"):
        return _currency_text(match.value, canonical_id, language)
    if canonical_id in {"temperature-celsius", "temperature-fahrenheit"}:
        unit = "Celsius" if canonical_id.endswith("celsius") else "Fahrenheit"
        value = _decimal(match.value)
        noun = f"grado {unit}" if abs(value) == 1 else f"gradi {unit}"
        article = "un" if "," not in match.value else None
        return f"{_number_text(match.value, singular_article=article, language=language)} {noun}"
    grammar = QUANTITY_GRAMMAR.get(canonical_id)
    if grammar is None:
        return None
    value = _decimal(match.value)
    singular = value == 1
    noun = grammar.singular if singular else grammar.plural
    number = _number_text(
        match.value,
        singular_article=grammar.article if singular else None,
        language=language,
    )
    result = f"{number}{noun}" if singular and grammar.article.endswith("'") else f"{number} {noun}"
    if match.symbol.endswith(".") and _terminal_dot(text, match.end):
        result += "."
    return result


def _currency_text(raw: str, canonical_id: str, language: str = "it") -> str:
    negative, integer, fraction = _parts(raw)
    names = {
        "currency-euro": ("euro", "euro", "centesimo", "centesimi"),
        "currency-us-dollar": ("dollaro", "dollari", "centesimo", "centesimi"),
        "currency-pound-sterling": ("sterlina", "sterline", "centesimo", "centesimi"),
        "currency-swiss-franc": ("franco svizzero", "franchi svizzeri", "centesimo", "centesimi"),
        "currency-japanese-yen": ("yen", "yen", None, None),
        "currency-mexican-peso": ("peso messicano", "pesos messicani", "centesimo", "centesimi"),
        "currency-indian-rupee": ("rupia", "rupie", "paisa", "paise"),
        "currency-south-korean-won": ("won", "won", None, None),
    }
    singular, plural, minor_singular, minor_plural = names[canonical_id]
    major = singular if integer == 1 else plural
    major_raw = f"{'-' if negative else ''}{integer}"
    number = _number_text(
        major_raw, singular_article="un" if integer == 1 else None, language=language
    )
    result = f"{number} {major}"
    if fraction is not None:
        minor_value = int((fraction + "00")[:2])
        if minor_value and minor_singular is not None and minor_plural is not None:
            minor = minor_singular if minor_value == 1 else minor_plural
            minor_number = "un" if minor_value == 1 else _spell(minor_value, language)
            result += f" e {minor_number} {minor}"
    return result


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def iter_replacements(
    text: str,
    *,
    language: str = "it",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return exact Italian structured and semantic replacement candidates."""
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []

    def add(start: int, end: int, value: str | None, rule: str) -> None:
        if value is not None and not _overlaps(start, end, protected):
            candidates.append(Replacement(start, end, value, "structured", "it", rule))

    for match in _DATE_DMY_SHORT.finditer(text):
        year, _ = expand_year(match["year"])
        day, month = int(match["day"]), int(match["month"])
        if _valid_date(day, month, year):
            add(match.start(), match.end(), _date_text(day, month, year, language), "it.date")
    aliases = {name[:3]: index for index, name in enumerate(_MONTHS, 1)}
    for match in _TEXT_DATE.finditer(text):
        text_month: int | None = aliases.get(match["month"].lower().rstrip(".")[:3])
        if text_month is None:
            continue
        text_year: int | None = None
        if match["year"]:
            text_year, _ = expand_year(match["year"])
        day = int(match["day"])
        if text_year is None or _valid_date(day, text_month, text_year):
            value = _date_text(day, text_month, text_year or 2000, language)
            if text_year is None:
                value = f"{_spell(day, language)} {_MONTHS[text_month - 1]}"
            add(match.start(), match.end(), value, "it.date")

    for pattern in (_DATE_DMY, _DATE_ISO):
        for match in pattern.finditer(text):
            day, month, year = int(match["day"]), int(match["month"]), int(match["year"])
            if 1 <= month <= 12 and _valid_date(day, month, year):
                add(match.start(), match.end(), _date_text(day, month, year, language), "it.date")

    for match in _TIME_COLON.finditer(text):
        add(
            match.start(),
            match.end(),
            _time_text(int(match["hour"]), int(match["minute"]), language),
            "it.time",
        )

    for match in _ORDINAL_SYMBOL.finditer(text):
        value = str(num2words(int(match["number"]), lang=resolve_num2words_language(language), to="ordinal"))
        add(match.start(), match.end(), value, "it.ordinal")

    for match in iter_unit_matches(
        text, resolve_abbr2words_language(language), protected_spans=protected
    ):
        try:
            replacement = _quantity_text(match, text, language)
        except (TypeError, ValueError):
            replacement = None
        add(
            match.start,
            match.end,
            replacement,
            "it.currency" if match.category == "currency" else "it.quantity",
        )
    return tuple(candidates)


__all__ = ["NUMBER_POLICY", "QUANTITY_GRAMMAR", "QuantityGrammar", "iter_replacements"]
