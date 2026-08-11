"""German semantic grammar owned by spokenform."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from abbr2words import UnitMatch, iter_unit_matches

from ..config import NumberPolicy
from ..language import resolve_abbr2words_language, resolve_num2words_language
from ..mapping import Replacement


@dataclass(frozen=True, slots=True)
class QuantityGrammar:
    canonical_id: str
    gender: str
    singular: str
    plural: str
    invariant_plural: bool = False


NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN
QUANTITY_GRAMMAR: dict[str, QuantityGrammar] = {
    "duration-second": QuantityGrammar("duration-second", "f", "Sekunde", "Sekunden"),
    "duration-minute": QuantityGrammar("duration-minute", "f", "Minute", "Minuten"),
    "duration-hour": QuantityGrammar("duration-hour", "f", "Stunde", "Stunden"),
    "duration-day": QuantityGrammar("duration-day", "m", "Tag", "Tage"),
    "length-millimeter": QuantityGrammar("length-millimeter", "m", "Millimeter", "Millimeter"),
    "length-centimeter": QuantityGrammar("length-centimeter", "m", "Zentimeter", "Zentimeter"),
    "length-meter": QuantityGrammar("length-meter", "m", "Meter", "Meter"),
    "length-kilometer": QuantityGrammar("length-kilometer", "m", "Kilometer", "Kilometer"),
    "area-square-millimeter": QuantityGrammar(
        "area-square-millimeter", "m", "Quadratmillimeter", "Quadratmillimeter"
    ),
    "area-square-centimeter": QuantityGrammar(
        "area-square-centimeter", "m", "Quadratzentimeter", "Quadratzentimeter"
    ),
    "area-square-meter": QuantityGrammar("area-square-meter", "m", "Quadratmeter", "Quadratmeter"),
    "area-square-kilometer": QuantityGrammar(
        "area-square-kilometer", "m", "Quadratkilometer", "Quadratkilometer"
    ),
    "area-hectare": QuantityGrammar("area-hectare", "m", "Hektar", "Hektar"),
    "volume-milliliter": QuantityGrammar("volume-milliliter", "m", "Milliliter", "Milliliter"),
    "volume-liter": QuantityGrammar("volume-liter", "m", "Liter", "Liter"),
    "volume-cubic-millimeter": QuantityGrammar(
        "volume-cubic-millimeter", "m", "Kubikmillimeter", "Kubikmillimeter"
    ),
    "volume-cubic-centimeter": QuantityGrammar(
        "volume-cubic-centimeter", "m", "Kubikzentimeter", "Kubikzentimeter"
    ),
    "volume-cubic-meter": QuantityGrammar("volume-cubic-meter", "m", "Kubikmeter", "Kubikmeter"),
    "speed-meter-per-second": QuantityGrammar(
        "speed-meter-per-second", "m", "Meter pro Sekunde", "Meter pro Sekunde"
    ),
    "speed-kilometer-per-hour": QuantityGrammar(
        "speed-kilometer-per-hour", "m", "Kilometer pro Stunde", "Kilometer pro Stunde"
    ),
    "mass-microgram": QuantityGrammar("mass-microgram", "m", "Mikrogramm", "Mikrogramm"),
    "mass-milligram": QuantityGrammar("mass-milligram", "n", "Milligramm", "Milligramm"),
    "mass-gram": QuantityGrammar("mass-gram", "n", "Gramm", "Gramm"),
    "mass-kilogram": QuantityGrammar("mass-kilogram", "n", "Kilogramm", "Kilogramm"),
    "mass-tonne": QuantityGrammar("mass-tonne", "f", "Tonne", "Tonnen"),
    "energy-kilowatt-hour": QuantityGrammar(
        "energy-kilowatt-hour", "f", "Kilowattstunde", "Kilowattstunden"
    ),
    "energy-watt-hour": QuantityGrammar("energy-watt-hour", "f", "Wattstunde", "Wattstunden"),
    "charge-milliampere-hour": QuantityGrammar(
        "charge-milliampere-hour", "f", "Milliamperestunde", "Milliamperestunden"
    ),
    "current-milliampere": QuantityGrammar(
        "current-milliampere", "n", "Milliampere", "Milliampere"
    ),
    "frequency-gigahertz": QuantityGrammar("frequency-gigahertz", "m", "Gigahertz", "Gigahertz"),
    "frequency-megahertz": QuantityGrammar("frequency-megahertz", "m", "Megahertz", "Megahertz"),
    "frequency-kilohertz": QuantityGrammar("frequency-kilohertz", "m", "Kilohertz", "Kilohertz"),
    "frequency-hertz": QuantityGrammar("frequency-hertz", "m", "Hertz", "Hertz"),
    "power-watt": QuantityGrammar("power-watt", "m", "Watt", "Watt"),
    "voltage-volt": QuantityGrammar("voltage-volt", "m", "Volt", "Volt"),
    "count-piece": QuantityGrammar("count-piece", "n", "Stück", "Stück", True),
    "magnitude-thousand": QuantityGrammar("magnitude-thousand", "m", "Tausend", "Tausend"),
    "magnitude-million": QuantityGrammar("magnitude-million", "f", "Million", "Millionen"),
    "magnitude-billion": QuantityGrammar("magnitude-billion", "f", "Milliarde", "Milliarden"),
}

_NUMBER = r"[+\-−]?(?:(?:\d{1,3}(?:[.\s]\d{3})+|\d+)(?:[.,]\d+)?|[.,]\d+)"
_DATE = re.compile(
    r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])[./](?P<month>0?[1-9]|1[0-2])[./](?P<year>\d{2,4})(?!\d)"
)
_TEXT_DATE = re.compile(
    r"(?P<day>0?[1-9]|[12]\d|3[01])\.\s+(?P<month>Januar|Februar|März|Maerz|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember|Mär\.?|Apr\.?|Aug\.?|Sept\.?|Dez\.?)((?!\w))(?:\s+(?P<year>\d{2,4}))?",
    re.IGNORECASE,
)
_TIME = re.compile(r"(?<!\d)(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)(?:\s+Uhr)?(?!\d)")
_CURRENCY_PREFIX = re.compile(
    rf"(?<![\w.])(?P<symbol>[^\W\d_€$£]+|[€$£])\s*(?P<number>{_NUMBER})(?![\w.])", re.IGNORECASE
)
_CURRENCY_SUFFIX = re.compile(
    rf"(?<![\w.])(?P<number>{_NUMBER})\s*(?P<symbol>[^\W\d_€$£]+|[€$£])(?!\w)", re.IGNORECASE
)
_TEMPERATURE = re.compile(
    rf"(?<!\w)(?P<number>{_NUMBER})(?:(?:\s*°\s*)|(?:\s+))(?P<unit>C|F)(?!\w)", re.IGNORECASE
)
_LABEL = re.compile(
    r"(?P<label>laufende\s+Nummer|Lfd\.\s*Nr\.|Nummer|Gleis|Kapitel|Absatz|Seite|S\.)\s+(?P<number>\d+)(?!\w)",
    re.IGNORECASE,
)
_ORDINAL = re.compile(r"(?<![\w.])(?P<number>\d+)\.(?=\s+[A-Za-zÄÖÜäöüß])")
_MONTHS = {
    "januar": (1, "Januar"),
    "februar": (2, "Februar"),
    "märz": (3, "März"),
    "maerz": (3, "März"),
    "mär": (3, "März"),
    "april": (4, "April"),
    "apr": (4, "April"),
    "mai": (5, "Mai"),
    "juni": (6, "Juni"),
    "juli": (7, "Juli"),
    "august": (8, "August"),
    "aug": (8, "August"),
    "september": (9, "September"),
    "sept": (9, "September"),
    "oktober": (10, "Oktober"),
    "november": (11, "November"),
    "dezember": (12, "Dezember"),
    "dez": (12, "Dezember"),
}


def _spell(value: int | Decimal, language: str = "de") -> str:
    from num2words import num2words

    return str(num2words(value, lang=resolve_num2words_language(language)))


def _parts(raw: str) -> tuple[bool, int, str | None]:
    value = raw.replace("−", "-")
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


def _number(raw: str, *, one: str | None = None, language: str = "de") -> str:
    negative, integer, fraction = _parts(raw)
    if fraction is None:
        result = one if integer == 1 and one else _spell(integer, language)
    else:
        result = f"{_spell(integer, language)} Komma " + " ".join(
            _spell(int(digit), language) for digit in fraction
        )
    return f"minus {result}" if negative else result


def _year(value: int, language: str = "de") -> str:
    if 1100 <= value < 2000:
        century, remainder = divmod(value, 100)
        prefix = f"{_spell(century, language)}hundert"
        return prefix if remainder == 0 else prefix + _spell(remainder, language)
    return _spell(value, language)


def _ordinal(value: int, ending: str, language: str = "de") -> str:
    from num2words import num2words

    word = str(num2words(value, lang=resolve_num2words_language(language), to="ordinal"))
    if ending == "er" and word.endswith("e"):
        return word[:-1] + "er"
    if ending == "e":
        return re.sub(r"(?:er|en|em)$", "e", word)
    if ending == "en":
        return re.sub(r"(?:er|e|em)$", "en", word)
    return word


def _ending(text: str, start: int) -> str:
    prefix = re.sub(r"\s+", " ", text[max(0, start - 48) : start].lower()).rstrip()
    if prefix.endswith(
        ("am", "im", "vom", "zum", "zur", "auf der", "an der", "in dem", "in den", "auf den")
    ):
        return "en"
    if prefix.endswith(("ans", "ins", "die", "auf die", "der")):
        return "e"
    return "er"


def _valid(day: int, month: int, year: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \t\n\"'”’»)]}")


def _quantity(match: UnitMatch, text: str, language: str = "de") -> str | None:
    grammar = QUANTITY_GRAMMAR.get(match.canonical_id or "")
    if grammar is None:
        return None
    negative, integer, fraction = _parts(match.value)
    value = Decimal(
        f"{'-' if negative else ''}{integer}.{fraction}"
        if fraction
        else f"{'-' if negative else ''}{integer}"
    )
    noun = grammar.singular if value == 1 else grammar.plural
    number = _number(match.value, language=language)
    if value == 1:
        number = "eine" if grammar.gender == "f" else "ein"
    if match.symbol.endswith(".") and _terminal_dot(text, match.end):
        noun += "."
    return f"{number} {noun}"


def _currency_id(symbol: str, language: str = "de") -> str | None:
    for match in iter_unit_matches(f"1 {symbol}", resolve_abbr2words_language(language)):
        if match.category == "currency":
            return match.canonical_id
    return None


def _currency_name(canonical_id: str) -> str:
    return {
        "currency-euro": "Euro",
        "currency-dollar": "Dollar",
        "currency-pound": "Pfund",
        "currency-swiss-franc": "Schweizer Franken",
    }.get(canonical_id, "")


def _currency(raw: str, canonical_id: str, language: str = "de") -> str:
    negative, integer, fraction = _parts(raw)
    result = f"{'ein' if integer == 1 else _spell(integer, language)} {_currency_name(canonical_id)}"
    if fraction:
        cents = int((fraction + "00")[:2])
        if cents:
            result += f" {_spell(cents, language)} Cent"
    return f"minus {result}" if negative else result


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def iter_replacements(
    text: str,
    *,
    language: str = "de",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []

    def add(match: re.Match[str], replacement: str | None, rule: str) -> None:
        if replacement is not None and not _overlaps(match.start(), match.end(), protected):
            candidates.append(
                Replacement(match.start(), match.end(), replacement, "structured", "de", rule)
            )

    for match in _DATE.finditer(text):
        day, month, year_raw = int(match["day"]), int(match["month"]), match["year"]
        separator = "." if "." in match.group(0) else "/"
        date_year = int(year_raw) if len(year_raw) == 4 else (
            int(year_raw) if separator == "." else 2000 + int(year_raw)
        )
        if _valid(day, month, date_year):
            month_name = next(name for number, name in _MONTHS.values() if number == month)
            month_text = (
                _ordinal(month, "en", language)
                if separator == "/" and len(year_raw) == 4
                else month_name
            )
            add(
                match,
                f"{_ordinal(day, _ending(text, match.start()) if match.start() else 'e', language)} {month_text} {_year(date_year, language)}",
                "de.date",
            )
    for match in _TEXT_DATE.finditer(text):
        month, month_name = _MONTHS[match["month"].lower().rstrip(".")]
        year_raw, day = match["year"], int(match["day"])
        text_year: int | None = (
            int(year_raw)
            if year_raw and len(year_raw) == 4
            else (int(year_raw) if year_raw else None)
        )
        if text_year is None or _valid(day, month, text_year):
            value = f"{_ordinal(day, _ending(text, match.start()) if text[: match.start()].strip() else 'e', language)} {month_name}"
            add(match, f"{value} {_year(text_year, language)}" if text_year else value, "de.text-date")
    for match in _TIME.finditer(text):
        hour, minute = int(match["hour"]), int(match["minute"])
        value = (
            f"{'ein' if hour == 1 else _spell(hour, language)} Uhr"
            if minute == 0
            else f"{'ein' if hour == 1 else _spell(hour, language)} Uhr {_spell(minute, language)}"
        )
        add(match, value, "de.time")
    for pattern in (_CURRENCY_PREFIX, _CURRENCY_SUFFIX):
        for match in pattern.finditer(text):
            canonical_id = _currency_id(match["symbol"], language)
            if canonical_id:
                add(match, _currency(match["number"], canonical_id, language), "de.currency")
    for match in _TEMPERATURE.finditer(text):
        unit = match["unit"].lower().replace("°", "")
        add(
            match,
            f"{_number(match['number'], language=language)} Grad {'Celsius' if unit == 'c' else 'Fahrenheit'}",
            "de.temperature",
        )
    for match in iter_unit_matches(
        text, resolve_abbr2words_language(language), protected_spans=protected
    ):
        if match.category == "currency" or (match.start and text[match.start - 1] in ".,"):
            continue
        if match.category == "magnitude":
            tail = re.match(r"\s+(?P<symbol>[^\W\d_€$£]+|[€$£])", text[match.end :])
            canonical_id = _currency_id(tail["symbol"], language) if tail else None
            if tail and canonical_id:
                base = _quantity(match, text, language)
                if base and not _overlaps(match.start, match.end + tail.end(), protected):
                    candidates.append(
                        Replacement(
                            match.start,
                            match.end + tail.end(),
                            f"{base} {_currency_name(canonical_id)}",
                            "structured",
                            "de",
                            "de.magnitude-currency",
                        )
                    )
                continue
        if not _overlaps(match.start, match.end, protected):
            try:
                replacement = _quantity(match, text, language)
            except (TypeError, ValueError):
                replacement = None
            if replacement:
                candidates.append(
                    Replacement(
                        match.start, match.end, replacement, "structured", "de", "de.quantity"
                    )
                )
    for match in _LABEL.finditer(text):
        label = match["label"]
        normalized = label.casefold().replace(" ", "")
        if normalized in {"s.", "seite"}:
            label = "Seite"
        elif normalized in {"lfd.nr.", "laufendenummer"}:
            label = "laufende Nummer"
        add(match, f"{label} {_spell(int(match['number']))}", "de.label")
    for match in _ORDINAL.finditer(text):
        add(match, _ordinal(int(match["number"]), _ending(text, match.start())), "de.ordinal")
    return tuple(candidates)


__all__ = ["NUMBER_POLICY", "QUANTITY_GRAMMAR", "QuantityGrammar", "iter_replacements"]
