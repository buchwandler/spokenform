"""English semantic grammar owned by spokenform.

Symbols and unit identities are recognized by :mod:`abbr2words`.  This module
only realizes the canonical identities and reviewed structured forms that are
safe to hand to a downstream English G2P.
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
    """English singular and plural speech nouns for one canonical unit."""

    canonical_id: str
    singular: str
    plural: str


QUANTITY_GRAMMAR: dict[str, QuantityGrammar] = {
    "length-millimeter": QuantityGrammar("length-millimeter", "millimeter", "millimeters"),
    "length-centimeter": QuantityGrammar("length-centimeter", "centimeter", "centimeters"),
    "length-meter": QuantityGrammar("length-meter", "meter", "meters"),
    "length-kilometer": QuantityGrammar("length-kilometer", "kilometer", "kilometers"),
    "area-square-millimeter": QuantityGrammar(
        "area-square-millimeter", "square millimeter", "square millimeters"
    ),
    "area-square-centimeter": QuantityGrammar(
        "area-square-centimeter", "square centimeter", "square centimeters"
    ),
    "area-square-meter": QuantityGrammar("area-square-meter", "square meter", "square meters"),
    "area-square-kilometer": QuantityGrammar(
        "area-square-kilometer", "square kilometer", "square kilometers"
    ),
    "area-hectare": QuantityGrammar("area-hectare", "hectare", "hectares"),
    "volume-cubic-millimeter": QuantityGrammar(
        "volume-cubic-millimeter", "cubic millimeter", "cubic millimeters"
    ),
    "volume-cubic-centimeter": QuantityGrammar(
        "volume-cubic-centimeter", "cubic centimeter", "cubic centimeters"
    ),
    "volume-cubic-meter": QuantityGrammar("volume-cubic-meter", "cubic meter", "cubic meters"),
    "volume-milliliter": QuantityGrammar("volume-milliliter", "milliliter", "milliliters"),
    "volume-liter": QuantityGrammar("volume-liter", "liter", "liters"),
    "mass-microgram": QuantityGrammar("mass-microgram", "microgram", "micrograms"),
    "mass-milligram": QuantityGrammar("mass-milligram", "milligram", "milligrams"),
    "mass-gram": QuantityGrammar("mass-gram", "gram", "grams"),
    "mass-kilogram": QuantityGrammar("mass-kilogram", "kilogram", "kilograms"),
    "mass-tonne": QuantityGrammar("mass-tonne", "tonne", "tonnes"),
    "temperature-kelvin": QuantityGrammar("temperature-kelvin", "kelvin", "kelvins"),
    "temperature-celsius": QuantityGrammar(
        "temperature-celsius", "degree Celsius", "degrees Celsius"
    ),
    "temperature-fahrenheit": QuantityGrammar(
        "temperature-fahrenheit", "degree Fahrenheit", "degrees Fahrenheit"
    ),
    "speed-meter-per-second": QuantityGrammar(
        "speed-meter-per-second", "meter per second", "meters per second"
    ),
    "speed-kilometer-per-hour": QuantityGrammar(
        "speed-kilometer-per-hour", "kilometer per hour", "kilometers per hour"
    ),
    "duration-second": QuantityGrammar("duration-second", "second", "seconds"),
    "duration-minute": QuantityGrammar("duration-minute", "minute", "minutes"),
    "duration-hour": QuantityGrammar("duration-hour", "hour", "hours"),
    "duration-day": QuantityGrammar("duration-day", "day", "days"),
    "duration-year": QuantityGrammar("duration-year", "year", "years"),
    "customary-inch": QuantityGrammar("customary-inch", "inch", "inches"),
    "customary-foot": QuantityGrammar("customary-foot", "foot", "feet"),
    "customary-yard": QuantityGrammar("customary-yard", "yard", "yards"),
    "customary-mile": QuantityGrammar("customary-mile", "mile", "miles"),
    "customary-ounce": QuantityGrammar("customary-ounce", "ounce", "ounces"),
    "customary-pound": QuantityGrammar("customary-pound", "pound", "pounds"),
    "customary-gallon": QuantityGrammar("customary-gallon", "gallon", "gallons"),
    "customary-quart": QuantityGrammar("customary-quart", "quart", "quarts"),
    "customary-pint": QuantityGrammar("customary-pint", "pint", "pints"),
    "customary-teaspoon": QuantityGrammar("customary-teaspoon", "teaspoon", "teaspoons"),
    "customary-tablespoon": QuantityGrammar("customary-tablespoon", "tablespoon", "tablespoons"),
}

_DATE_DMY = re.compile(
    r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])[./](?P<month>0?[1-9]|1[0-2])[./](?P<year>\d{4})(?!\d)"
)
_DATE_ISO = re.compile(
    r"(?<![\w.])(?P<year>\d{4})-(?P<month>0?[1-9]|1[0-2])-(?P<day>0?[1-9]|[12]\d|3[01])(?!\d)"
)
_TIME = re.compile(r"(?<!\w)(?P<hour>\d{1,2}):(?P<minute>\d{2})(?!\w)")
_PLURAL_TENS = re.compile(r"(?<!\w)(?P<value>[2-9]0)(?P<suffix>s)(?!\w)", re.IGNORECASE)
_PLURAL_TENS_WORDS = {
    20: "twenties",
    30: "thirties",
    40: "forties",
    50: "fifties",
    60: "sixties",
    70: "seventies",
    80: "eighties",
    90: "nineties",
}
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _spell(value: int, *, ordinal: bool = False) -> str:
    result = str(num2words(value, lang="en", to="ordinal" if ordinal else "cardinal"))
    return result.replace(",", "").replace("-", " ")


def _parts(raw: str) -> tuple[bool, bool, int, str | None]:
    value = raw.replace("−", "-").replace("\u00a0", " ").replace("\u202f", " ").strip()
    negative = value.startswith("-")
    positive = value.startswith("+")
    unsigned = value.lstrip("+-").replace(" ", "")
    if "." in unsigned:
        integer, fraction = unsigned.split(".", 1)
    else:
        integer, fraction = unsigned.replace(",", ""), None
    if fraction is not None:
        integer = integer.replace(",", "")
    return negative, positive, int(integer or "0"), fraction


def _number_text(raw: str) -> str:
    negative, positive, integer, fraction = _parts(raw)
    if fraction is None:
        result = _spell(integer)
    else:
        result = f"{_spell(integer)} point " + " ".join(_spell(int(digit)) for digit in fraction)
    if negative:
        return f"minus {result}"
    if positive:
        return f"plus {result}"
    return result


def _decimal(raw: str) -> Decimal:
    try:
        negative, _, integer, fraction = _parts(raw)
        value = f"{'-' if negative else ''}{integer}"
        if fraction is not None:
            value += f".{fraction}"
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Cannot parse English number {raw!r}") from exc


def _valid_date(day: int, month: int, year: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _date_text(day: int, month: int, year: int) -> str:
    day_text = str(num2words(day, lang="en", to="ordinal"))
    year_text = str(num2words(year, lang="en"))
    return f"{_MONTHS[month - 1]} {day_text}, {year_text}"


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \t\n\"'”’»)]}")


def _quantity_text(match: UnitMatch, text: str) -> str | None:
    canonical_id = match.canonical_id or ""
    grammar = QUANTITY_GRAMMAR.get(canonical_id)
    if grammar is None:
        return _currency_text(match.value, canonical_id) if match.category == "currency" else None
    try:
        value = _decimal(match.value)
    except ValueError:
        return None
    noun = grammar.singular if abs(value) == 1 else grammar.plural
    result = f"{_number_text(match.value)} {noun}"
    if match.symbol.endswith(".") and _terminal_dot(text, match.end):
        result += "."
    return result


def _currency_text(raw: str, canonical_id: str) -> str | None:
    names = {
        "currency-us-dollar": ("dollar", "dollars", "cent", "cents"),
        "currency-pound-sterling": ("pound", "pounds", "penny", "pence"),
        "currency-euro": ("euro", "euros", "cent", "cents"),
    }
    labels = names.get(canonical_id)
    if labels is None:
        return None
    try:
        negative, positive, integer, fraction = _parts(raw)
    except ValueError:
        return None
    if fraction is not None and len(fraction) > 2:
        return None
    # English currency input accepts comma-separated thousands only.  An
    # ambiguous comma decimal is intentionally left unchanged.
    if "," in raw and not re.fullmatch(r"[+\-−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", raw.strip()):
        return None
    minor = int((fraction or "").ljust(2, "0")) if fraction is not None else 0
    major_singular, major_plural, minor_singular, minor_plural = labels
    major_label = major_singular if integer == 1 else major_plural
    major = _number_text(("-" if negative else "+" if positive else "") + str(integer))
    result = f"{major} {major_label}"
    if minor:
        minor_label = minor_singular if minor == 1 else minor_plural
        result += f" and {_spell(minor)} {minor_label}"
    return result


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def _is_plural_tens_context(text: str, start: int) -> bool:
    """Return whether a round-tens suffix is used as a plural marker."""
    left = text[max(0, start - 48) : start]
    if re.search(
        r"\b(?:high|low|mid|upper|lower|early|late)\s+$",
        left,
        re.IGNORECASE,
    ):
        return True
    return bool(
        re.search(
            r"\b(?:in|from|during|throughout)\s+"
            r"(?:the|his|her|their|my|your|our)\s+$",
            left,
            re.IGNORECASE,
        )
    )


def iter_replacements(
    text: str, *, protected_ranges: Iterable[tuple[int, int]] = ()
) -> tuple[Replacement, ...]:
    """Return exact English structured semantic replacements."""
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []

    def add(start: int, end: int, value: str | None, rule: str) -> None:
        if value is not None and not _overlaps(start, end, protected):
            candidates.append(Replacement(start, end, value, "structured", "en", rule))

    for pattern in (_DATE_DMY, _DATE_ISO):
        for match in pattern.finditer(text):
            day, month, year = int(match["day"]), int(match["month"]), int(match["year"])
            if _valid_date(day, month, year):
                add(match.start(), match.end(), _date_text(day, month, year), "en.date")

    for match in _TIME.finditer(text):
        hour, minute = int(match["hour"]), int(match["minute"])
        if hour > 23 or minute > 59:
            continue
        hour_text = _spell(hour)
        if minute == 0:
            value = f"{hour_text} o'clock"
        elif minute < 10:
            value = f"{hour_text} oh {_spell(minute)}"
        else:
            value = f"{hour_text} {_spell(minute)}"
        add(match.start(), match.end(), value, "en.time")

    plural_tens_spans: list[tuple[int, int]] = []
    for match in _PLURAL_TENS.finditer(text):
        if not _is_plural_tens_context(text, match.start()):
            continue
        start, end = match.span()
        if _overlaps(start, end, protected):
            continue
        plural_tens_spans.append((start, end))
        add(start, end, _PLURAL_TENS_WORDS[int(match["value"])], "en.plural_tens")

    unit_protected = protected + tuple(plural_tens_spans)
    for match in iter_unit_matches(text, "en", protected_spans=unit_protected):
        replacement = _quantity_text(match, text)
        add(
            match.start,
            match.end,
            replacement,
            "en.currency" if match.category == "currency" else "en.quantity",
        )

    return tuple(candidates)


__all__ = ["NUMBER_POLICY", "QUANTITY_GRAMMAR", "QuantityGrammar", "iter_replacements"]
