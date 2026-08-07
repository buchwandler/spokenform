"""French semantic grammar owned by spokenform.

The French unit and currency inventory is supplied by :mod:`abbr2words`.
This module only realizes its canonical identities in French grammar and
produces source-aligned semantic candidates for the shared dispatcher.
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
from ..mapping import Replacement

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN


@dataclass(frozen=True, slots=True)
class QuantityGrammar:
    canonical_id: str
    singular: str
    plural: str
    gender: str = "m"


QUANTITY_GRAMMAR: dict[str, QuantityGrammar] = {
    "duration-second": QuantityGrammar("duration-second", "seconde", "secondes", "f"),
    "duration-minute": QuantityGrammar("duration-minute", "minute", "minutes", "f"),
    "duration-hour": QuantityGrammar("duration-hour", "heure", "heures", "f"),
    "duration-day": QuantityGrammar("duration-day", "jour", "jours"),
    "length-millimeter": QuantityGrammar("length-millimeter", "millimètre", "millimètres"),
    "length-centimeter": QuantityGrammar("length-centimeter", "centimètre", "centimètres"),
    "length-meter": QuantityGrammar("length-meter", "mètre", "mètres"),
    "length-kilometer": QuantityGrammar("length-kilometer", "kilomètre", "kilomètres"),
    "volume-milliliter": QuantityGrammar("volume-milliliter", "millilitre", "millilitres"),
    "volume-liter": QuantityGrammar("volume-liter", "litre", "litres"),
    "mass-microgram": QuantityGrammar("mass-microgram", "microgramme", "microgrammes"),
    "mass-milligram": QuantityGrammar("mass-milligram", "milligramme", "milligrammes"),
    "mass-gram": QuantityGrammar("mass-gram", "gramme", "grammes"),
    "mass-kilogram": QuantityGrammar("mass-kilogram", "kilogramme", "kilogrammes"),
    "mass-tonne": QuantityGrammar("mass-tonne", "tonne", "tonnes", "f"),
    "temperature-kelvin": QuantityGrammar("temperature-kelvin", "kelvin", "kelvins"),
    "speed-meter-per-second": QuantityGrammar("speed-meter-per-second", "mètre par seconde", "mètres par seconde"),
    "speed-kilometer-per-hour": QuantityGrammar("speed-kilometer-per-hour", "kilomètre par heure", "kilomètres par heure"),
    "area-square-millimeter": QuantityGrammar("area-square-millimeter", "millimètre carré", "millimètres carrés"),
    "area-square-centimeter": QuantityGrammar("area-square-centimeter", "centimètre carré", "centimètres carrés"),
    "area-square-meter": QuantityGrammar("area-square-meter", "mètre carré", "mètres carrés"),
    "area-square-kilometer": QuantityGrammar("area-square-kilometer", "kilomètre carré", "kilomètres carrés"),
    "area-hectare": QuantityGrammar("area-hectare", "hectare", "hectares"),
    "volume-cubic-millimeter": QuantityGrammar("volume-cubic-millimeter", "millimètre cube", "millimètres cubes"),
    "volume-cubic-centimeter": QuantityGrammar("volume-cubic-centimeter", "centimètre cube", "centimètres cubes"),
    "volume-cubic-meter": QuantityGrammar("volume-cubic-meter", "mètre cube", "mètres cubes"),
}

_NUMBER = r"[+\-−]?(?:(?:\d{1,3}(?:[.\s\u00a0\u202f]\d{3})+|\d+)(?:[.,]\d+)?|[.,]\d+)"
_DATE_DMY = re.compile(r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])[./](?P<month>0?[1-9]|1[0-2])[./](?P<year>\d{4})(?!\d)")
_DATE_ISO = re.compile(r"(?<![\w.])(?P<year>\d{4})-(?P<month>0?[1-9]|1[0-2])-(?P<day>0?[1-9]|[12]\d|3[01])(?!\d)")
_DATE_CANDIDATE = re.compile(r"(?<![\w.])(?:\d{1,2}[./]){2}\d{2,4}(?!\d)")
_TIME_COLON = re.compile(r"(?<![\w.])(?P<hour>\d{1,2}):(?P<minute>\d{2})(?!\d)")
_TIME_H = re.compile(r"(?<![\w.])(?P<hour>\d{1,2})\s*h(?:(?:\s*)(?P<minute>\d{2}))?(?!\w)", re.IGNORECASE)
_TIME_CANDIDATE = re.compile(r"(?<![\w.])\d{1,2}\s*(?::\s*\d{2}|h\s*\d{0,2})(?!\w)", re.IGNORECASE)
_ORDINAL = re.compile(r"(?<![\w.,])(?P<number>\d+)\s*(?P<suffix>er|ère|re|ème|e|nd|nde)\b", re.IGNORECASE)
_PLAIN_NUMBER = re.compile(rf"(?<![\w.])(?P<number>{_NUMBER})(?![\w.])")
_MONTHS = ("janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre")


def _spell(value: int | Decimal, *, ordinal: bool = False) -> str:
    return str(num2words(value, lang="fr", to="ordinal" if ordinal else "cardinal"))


def _parts(raw: str) -> tuple[bool, int, str | None]:
    value = raw.replace("−", "-").replace("\u00a0", " ").replace("\u202f", " ")
    negative, unsigned = value.startswith("-"), value.lstrip("+-")
    if unsigned.startswith((".", ",")):
        integer, fraction = "0", unsigned[1:]
    elif "," in unsigned:
        integer, fraction = unsigned.split(",", 1)
    elif re.search(r"\.\d{1,2}$", unsigned) and unsigned.count(".") == 1:
        integer, fraction = unsigned.split(".", 1)
    else:
        integer, fraction = unsigned, None
    integer = re.sub(r"[.\s]", "", integer) or "0"
    return negative, int(integer), fraction


def _number_text(raw: str) -> str:
    negative, integer, fraction = _parts(raw)
    result = _spell(integer)
    if fraction is not None:
        result += " virgule " + " ".join(_spell(int(digit)) for digit in fraction)
    return f"moins {result}" if negative else result


def _decimal(raw: str) -> Decimal:
    negative, integer, fraction = _parts(raw)
    normalized = f"{'-' if negative else ''}{integer}"
    if fraction is not None:
        normalized += f".{fraction}"
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(raw) from exc


def _valid_date(day: int, month: int, year: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _date_text(day: int, month: int, year: int) -> str:
    day_text = "premier" if day == 1 else _spell(day)
    return f"{day_text} {_MONTHS[month - 1]} {_spell(year)}"


def _time_text(hour: int, minute: int) -> str:
    hour_text = "une heure" if hour == 1 else f"{_spell(hour)} heures"
    return hour_text if minute == 0 else f"{hour_text} {_spell(minute)}"


def _ordinal_text(value: int, suffix: str) -> str:
    suffix = suffix.casefold()
    if value == 1 and suffix in {"ère", "re"}:
        return "première"
    if value == 1:
        return "premier"
    if value == 2 and suffix == "nd":
        return "second"
    if value == 2 and suffix == "nde":
        return "seconde"
    return _spell(value, ordinal=True)


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \t\n\"'”’»)]}")


def _quantity_text(match: UnitMatch, text: str) -> str | None:
    canonical_id = match.canonical_id or ""
    if canonical_id.startswith("currency-"):
        return _currency_text(match.value, canonical_id)
    grammar = QUANTITY_GRAMMAR.get(canonical_id)
    if canonical_id == "temperature-celsius" or canonical_id == "temperature-fahrenheit":
        unit = "Celsius" if canonical_id.endswith("celsius") else "Fahrenheit"
        value = _decimal(match.value)
        noun = f"degré {unit}" if value == 1 else f"degrés {unit}"
        return f"{_number_text(match.value)} {noun}"
    if grammar is None:
        return None
    value = _decimal(match.value)
    noun = grammar.singular if value == 1 else grammar.plural
    result = f"{_number_text(match.value)} {noun}"
    if match.symbol.endswith(".") and _terminal_dot(text, match.end):
        result += "."
    return result


def _currency_text(raw: str, canonical_id: str) -> str:
    negative, integer, fraction = _parts(raw)
    major_names = {
        "currency-euro": ("euro", "euros", "centime", "centimes"),
        "currency-us-dollar": ("dollar", "dollars", "cent", "cents"),
        "currency-pound-sterling": ("livre sterling", "livres sterling", "penny", "pence"),
    }
    singular, plural, minor_singular, minor_plural = major_names.get(
        canonical_id, (canonical_id, canonical_id, "centime", "centimes")
    )
    major = singular if integer == 1 else plural
    result = f"{_spell(integer)} {major}"
    if fraction is not None:
        minor = int((fraction + "00")[:2])
        if minor:
            minor_name = minor_singular if minor == 1 else minor_plural
            result += f" {_spell(minor)} {minor_name}"
    return f"moins {result}" if negative else result


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def iter_replacements(text: str, *, protected_ranges: Iterable[tuple[int, int]] = ()) -> tuple[Replacement, ...]:
    """Return French structured candidates before shared conflict resolution."""
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []

    def add(start: int, end: int, value: str | None, rule: str) -> None:
        if value is not None and not _overlaps(start, end, protected):
            candidates.append(Replacement(start, end, value, "structured", "fr", rule))

    for pattern in (_DATE_DMY, _DATE_ISO):
        for match in pattern.finditer(text):
            day, month, year = int(match["day"]), int(match["month"]), int(match["year"])
            if _valid_date(day, month, year):
                add(match.start(), match.end(), _date_text(day, month, year), "fr.date")
    for match in _TIME_H.finditer(text):
        hour, minute = int(match["hour"]), int(match["minute"] or 0)
        if hour <= 23 and minute <= 59:
            add(match.start(), match.end(), _time_text(hour, minute), "fr.time")
    for match in _TIME_COLON.finditer(text):
        hour, minute = int(match["hour"]), int(match["minute"])
        if hour <= 23 and minute <= 59:
            add(match.start(), match.end(), _time_text(hour, minute), "fr.time")
    for match in _ORDINAL.finditer(text):
        add(match.start(), match.end(), _ordinal_text(int(match["number"]), match["suffix"]), "fr.ordinal")
    for match in iter_unit_matches(text, "fr", protected_spans=protected):
        replacement = _quantity_text(match, text)
        add(match.start, match.end, replacement, "fr.currency" if match.category == "currency" else "fr.quantity")

    excluded = [match.span() for match in _DATE_CANDIDATE.finditer(text)]
    excluded.extend(match.span() for match in _TIME_CANDIDATE.finditer(text))
    for match in _PLAIN_NUMBER.finditer(text):
        if any(left <= match.start() and match.end() <= right for left, right in excluded):
            continue
        add(match.start(), match.end(), _number_text(match["number"]), "fr.number")
    return tuple(candidates)


__all__ = ["NUMBER_POLICY", "QUANTITY_GRAMMAR", "QuantityGrammar", "iter_replacements"]
