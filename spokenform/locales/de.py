"""German semantic grammar owned by spokenform."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from abbr2words import UnitMatch, iter_unit_matches

from ..config import NumberPolicy
from ..dates import expand_year, parsed_date, render_year
from ..language import resolve_abbr2words_language, resolve_num2words_language
from ..mapping import Replacement
from ..numeric_lexeme import fraction_digit_groups, numeric_speech_policy, parse_numeric_lexeme


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
QUANTITY_GRAMMAR.update(
    {
        "data-byte": QuantityGrammar("data-byte", "m", "Byte", "Byte"),
        "data-kilobyte": QuantityGrammar("data-kilobyte", "m", "Kilobyte", "Kilobyte"),
        "data-megabyte": QuantityGrammar("data-megabyte", "m", "Megabyte", "Megabyte"),
        "data-gigabyte": QuantityGrammar("data-gigabyte", "m", "Gigabyte", "Gigabyte"),
        "flow-cubic-meter-per-second": QuantityGrammar(
            "flow-cubic-meter-per-second", "m", "Kubikmeter pro Sekunde", "Kubikmeter pro Sekunde"
        ),
        "fuel-consumption-liter-per-100-kilometer": QuantityGrammar(
            "fuel-consumption-liter-per-100-kilometer",
            "m",
            "Liter pro hundert Kilometer",
            "Liter pro hundert Kilometer",
        ),
        "pressure-atmosphere": QuantityGrammar(
            "pressure-atmosphere", "f", "Atmosphäre", "Atmosphären"
        ),
        "pressure-kilopascal": QuantityGrammar(
            "pressure-kilopascal", "m", "Kilopascal", "Kilopascal"
        ),
        "pressure-pascal": QuantityGrammar("pressure-pascal", "m", "Pascal", "Pascal"),
        "speed-mile-per-hour": QuantityGrammar(
            "speed-mile-per-hour", "m", "Meile pro Stunde", "Meilen pro Stunde"
        ),
        "temperature-celsius": QuantityGrammar(
            "temperature-celsius", "n", "Grad Celsius", "Grad Celsius"
        ),
        "temperature-fahrenheit": QuantityGrammar(
            "temperature-fahrenheit", "n", "Grad Fahrenheit", "Grad Fahrenheit"
        ),
        "power-kilowatt": QuantityGrammar("power-kilowatt", "m", "Kilowatt", "Kilowatt"),
        "energy-joule": QuantityGrammar("energy-joule", "m", "Joule", "Joule"),
        "length-nanometer": QuantityGrammar("length-nanometer", "m", "Nanometer", "Nanometer"),
        "current-ampere": QuantityGrammar("current-ampere", "n", "Ampere", "Ampere"),
        "luminous-flux-lumen": QuantityGrammar("luminous-flux-lumen", "m", "Lumen", "Lumen"),
        "force-newton": QuantityGrammar("force-newton", "m", "Newton", "Newton"),
        "pressure-millimeter-mercury": QuantityGrammar(
            "pressure-millimeter-mercury",
            "m",
            "Millimeter Quecksilbersäule",
            "Millimeter Quecksilbersäule",
        ),
        "amount-mole": QuantityGrammar("amount-mole", "n", "Mol", "Mol"),
        "concentration-molar": QuantityGrammar("concentration-molar", "n", "molar", "molar"),
        "customary-pound": QuantityGrammar("customary-pound", "n", "Pfund", "Pfund"),
    }
)

_NUMBER = r"[+\-−]?(?:(?:\d{1,3}(?:[.\s]\d{3})+|\d+)(?:[.,]\d+)?|[.,]\d+)"
_DATE = re.compile(
    r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])[./](?P<month>0?[1-9]|1[0-2])[./](?P<year>\d{2,4})(?!\d)"
)
_TEXT_DATE = re.compile(
    r"(?P<day>0?[1-9]|[12]\d|3[01])\.\s+(?P<month>Januar|Februar|März|Maerz|April|Mai|Juni|Juli|August|September|Oktober|November|Nov\.?|Dezember|Mär\.?|Apr\.?|Aug\.?|Sept\.?|Dez\.?)((?!\w))(?:\s+(?P<year>\d{2,4}))?",
    re.IGNORECASE,
)
_MIXED_TEXT_DATE = re.compile(
    r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])(?P<suffix>st|nd|rd|th)\s+"
    r"(?P<month>Jan(?:uary)?\.?|Feb(?:ruary)?\.?|Mar(?:ch)?\.?|Apr(?:il)?\.?|"
    r"May|Jun(?:e)?\.?|Jul(?:y)?\.?|Aug(?:ust)?\.?|Sep(?:tember)?\.?|"
    r"Oct(?:ober)?\.?|Nov(?:ember)?\.?|Dec(?:ember)?\.?)"
    r"(?:\s+(?P<year>\d{4})(?!\d))?",
    re.IGNORECASE,
)
_TEXT_DATE_RANGE = re.compile(
    r"(?P<start>0?[1-9]|[12]\d|3[01])\.-(?P<end>0?[1-9]|[12]\d|3[01])\.\s+"
    r"(?P<month>Januar|Februar|März|Maerz|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember|Mär\.?|Apr\.?|Aug\.?|Sept\.?|Dez\.?)"
    r"(?:\s+(?P<year>\d{2,4}))?",
    re.IGNORECASE,
)
_HYPHEN_DATE = re.compile(
    r"(?P<day>0?[1-9]|[12]\d|3[01])-(?P<month>\d{1,2}|Jan(?:uar)?\.?|Feb(?:ruar)?\.?|März?\.?|Apr(?:il)?\.?|Mai|Jun(?:i)?\.?|Jul(?:i)?\.?|Aug(?:ust)?\.?|Sep(?:t(?:ember)?)?\.?|Okt(?:ober)?\.?|Nov(?:ember)?\.?|Dez(?:ember)?\.?)-(?P<year>\d{2,4})",
    re.IGNORECASE,
)
_DAY_MONTH = re.compile(
    r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])\.(?P<month>0?[1-9]|1[0-2])\.(?!\d)"
)
_APOSTROPHE_YEAR = re.compile(r"(?<!\w)[’'](?P<year>\d{2})(?!\w)")
_TIME = re.compile(r"(?<!\d)(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)(?:\s+Uhr)?(?!\d)")
_TIME_RANGE = re.compile(
    r"(?<!\d)(?P<start_hour>[01]?\d|2[0-3]):(?P<start_minute>[0-5]\d)\s*[–-]\s*"
    r"(?P<end_hour>[01]?\d|2[0-3]):(?P<end_minute>[0-5]\d)(?:\s+Uhr)?(?!\d)|"
    r"(?<!\d)(?P<start_hour_bis>[01]?\d|2[0-3]):(?P<start_minute_bis>[0-5]\d)\s+bis\s+"
    r"(?P<end_hour_bis>[01]?\d|2[0-3]):(?P<end_minute_bis>[0-5]\d)(?:\s+Uhr)?(?!\d)"
)
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
    "jan": (1, "Januar"),
    "februar": (2, "Februar"),
    "feb": (2, "Februar"),
    "märz": (3, "März"),
    "maerz": (3, "März"),
    "mär": (3, "März"),
    "april": (4, "April"),
    "apr": (4, "April"),
    "mai": (5, "Mai"),
    "juni": (6, "Juni"),
    "jun": (6, "Juni"),
    "juli": (7, "Juli"),
    "jul": (7, "Juli"),
    "august": (8, "August"),
    "aug": (8, "August"),
    "september": (9, "September"),
    "sep": (9, "September"),
    "sept": (9, "September"),
    "oktober": (10, "Oktober"),
    "okt": (10, "Oktober"),
    "november": (11, "November"),
    "nov": (11, "November"),
    "dezember": (12, "Dezember"),
    "dez": (12, "Dezember"),
}
_MIXED_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


def _spell(value: int | Decimal, language: str = "de") -> str:
    from num2words import num2words

    return str(num2words(value, lang=resolve_num2words_language(language)))


def _parts(raw: str, language: str = "de") -> tuple[bool, int, str | None]:
    lexeme = parse_numeric_lexeme(raw, language, context="quantity")
    if lexeme is None:
        raise ValueError(f"Cannot parse German number {raw!r}")
    return lexeme.negative, int(lexeme.integer_digits), lexeme.fraction_digits


def _number(raw: str, *, one: str | None = None, language: str = "de") -> str:
    negative, integer, fraction = _parts(raw, language)
    if fraction is None:
        result = one if integer == 1 and one else _spell(integer, language)
    else:
        policy = numeric_speech_policy(language)
        result = f"{_spell(integer, language)} {policy.decimal_word} " + " ".join(
            _spell(int(group), language) for group in fraction_digit_groups(fraction, language)
        )
    return f"minus {result}" if negative else result


def _year(value: int, language: str = "de", *, year_digits: int | None = None) -> str:
    return render_year(value, language=language, source_digits=year_digits)


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
        ("am", "im", "vom", "zum", "zur", "bis", "auf der", "an der", "in dem", "in den", "auf den")
    ):
        return "en"
    if prefix.endswith(("ans", "ins", "die", "das", "auf die", "der")):
        return "e"
    if prefix.endswith(("ihren", "deren")):
        return "en"
    return "er"


def _valid(day: int, month: int, year: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _valid_english_ordinal_suffix(day: int, suffix: str) -> bool:
    """Require a valid English ordinal marker in the mixed-language shape."""
    if 10 < day % 100 < 14:
        expected = "th"
    else:
        expected = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return suffix.casefold() == expected


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \t\n\"'”’»)]}")


def _quantity(match: UnitMatch, text: str, language: str = "de") -> str | None:
    grammar = QUANTITY_GRAMMAR.get(match.canonical_id or "")
    if grammar is None:
        return None
    negative, integer, fraction = _parts(match.value, language)
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
        "currency-us-dollar": "US-Dollar",
        "currency-dollar": "Dollar",
        "currency-pound": "Pfund",
        "currency-swiss-franc": "Schweizer Franken",
        "currency-japanese-yen": "Yen",
        "currency-indian-rupee": "Indische Rupien",
        "currency-south-korean-won": "Won",
        "currency-mexican-peso": "Mexikanische Pesos",
    }.get(canonical_id, "")


def _currency(raw: str, canonical_id: str, language: str = "de") -> str:
    negative, integer, fraction = _parts(raw)
    result = (
        f"{'ein' if integer == 1 else _spell(integer, language)} {_currency_name(canonical_id)}"
    )
    if fraction:
        cents = int((fraction + "00")[:2])
        if cents:
            result += f" {_spell(cents, language)}"
    return f"minus {result}" if negative else result


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def _add_candidate(
    candidates: list[Replacement],
    match: re.Match[str],
    replacement: str | None,
    rule: str,
    protected: tuple[tuple[int, int], ...],
) -> None:
    if replacement is not None and not _overlaps(match.start(), match.end(), protected):
        candidates.append(
            Replacement(match.start(), match.end(), replacement, "structured", "de", rule)
        )


def _iter_de_dates(
    text: str, language: str, protected: tuple[tuple[int, int], ...], candidates: list[Replacement]
) -> None:
    for match in _DATE.finditer(text):
        day, month, year_raw = int(match["day"]), int(match["month"]), match["year"]
        separator = "." if "." in match.group(0) else "/"
        year_digits = len(year_raw)
        date_year = (
            int(year_raw)
            if len(year_raw) == 4
            else (int(year_raw) if separator == "." else 2000 + int(year_raw))
        )
        if _valid(day, month, date_year):
            month_name = next(name for number, name in _MONTHS.values() if number == month)
            month_text = (
                _ordinal(month, "en", language)
                if separator == "/" or (separator == "." and len(year_raw) == 2)
                else month_name
            )
            value = f"{_ordinal(day, _ending(text, match.start()) if match.start() else 'e', language)} {month_text} {_year(date_year, language, year_digits=year_digits if separator == '.' else None)}"
            _add_candidate(candidates, match, value, "de.date", protected)
    for match in _DAY_MONTH.finditer(text):
        day, month = int(match["day"]), int(match["month"])
        if parsed_date(match["day"], match["month"]).valid():
            month_name = _ordinal(month, _ending(text, match.start()), language)
            value = f"{_ordinal(day, _ending(text, match.start()), language)} {month_name}"
            if match.group(0).endswith("."):
                value += "."
            _add_candidate(candidates, match, value, "de.date", protected)
    for match in _HYPHEN_DATE.finditer(text):
        raw_month = match["month"].lower().rstrip(".")
        month = int(raw_month) if raw_month.isdigit() else _MONTHS.get(raw_month, (0, ""))[0]
        year = expand_year(match["year"])[0]
        if month and _valid(int(match["day"]), month, year):
            month_name = next(name for number, name in _MONTHS.values() if number == month)
            value = f"{_ordinal(int(match['day']), _ending(text, match.start()), language)} {month_name} {_year(year, language, year_digits=len(match['year']))}"
            _add_candidate(candidates, match, value, "de.date", protected)
    for match in _TEXT_DATE_RANGE.finditer(text):
        month, month_name = _MONTHS[match["month"].lower().rstrip(".")]
        range_year = expand_year(match["year"])[0] if match["year"] else None
        if not range_year or (
            _valid(int(match["start"]), month, range_year)
            and _valid(int(match["end"]), month, range_year)
        ):
            ending = _ending(text, match.start())
            value = f"{_ordinal(int(match['start']), ending, language)} bis {_ordinal(int(match['end']), ending, language)} {month_name}"
            value = (
                f"{value} {_year(range_year, language, year_digits=len(match['year']) if match['year'] else None)}"
                if range_year
                else value
            )
            _add_candidate(candidates, match, value, "de.date-range", protected)
    for match in _APOSTROPHE_YEAR.finditer(text):
        year, year_digits = expand_year(match["year"])
        _add_candidate(
            candidates,
            match,
            _year(year, language, year_digits=year_digits),
            "de.short-year",
            protected,
        )
    for match in _TEXT_DATE.finditer(text):
        month, month_name = _MONTHS[match["month"].lower().rstrip(".")]
        year_raw, day = match["year"], int(match["day"])
        text_year = (
            int(year_raw)
            if year_raw and len(year_raw) == 4
            else (int(year_raw) if year_raw else None)
        )
        if text_year is None or _valid(day, month, text_year):
            value = f"{_ordinal(day, _ending(text, match.start()) if text[: match.start()].strip() else 'er', language)} {month_name}"
            value = (
                f"{value} {_year(text_year, language, year_digits=len(year_raw) if year_raw else None)}"
                if text_year
                else value
            )
            _add_candidate(candidates, match, value, "de.text-date", protected)
    for match in _MIXED_TEXT_DATE.finditer(text):
        day = int(match["day"])
        month = _MIXED_MONTHS[match["month"].lower().rstrip(".")]
        mixed_year = int(match["year"]) if match["year"] else None
        if _valid_english_ordinal_suffix(day, match["suffix"]) and _valid(
            day, month, mixed_year or 2000
        ):
            month_name = next(name for number, name in _MONTHS.values() if number == month)
            value = f"{_ordinal(day, _ending(text, match.start()), language)} {month_name}"
            if mixed_year:
                value += f" {_year(mixed_year, language)}"
            _add_candidate(candidates, match, value, "de.mixed-text-date", protected)


def _iter_de_times(
    text: str, language: str, protected: tuple[tuple[int, int], ...], candidates: list[Replacement]
) -> None:
    for match in _TIME_RANGE.finditer(text):
        start_hour = int(match["start_hour"] or match["start_hour_bis"])
        start_minute = int(match["start_minute"] or match["start_minute_bis"])
        end_hour = int(match["end_hour"] or match["end_hour_bis"])
        end_minute = int(match["end_minute"] or match["end_minute_bis"])
        start = "ein" if start_hour == 1 else _spell(start_hour, language)
        end = "ein" if end_hour == 1 else _spell(end_hour, language)
        if start_minute == 0 and end_minute == 0:
            value = f"{start} bis {end} Uhr"
        else:
            start_value = (
                start if start_minute == 0 else f"{start} Uhr {_spell(start_minute, language)}"
            )
            end_value = (
                f"{end} Uhr" if end_minute == 0 else f"{end} Uhr {_spell(end_minute, language)}"
            )
            value = f"{start_value} bis {end_value}"
        _add_candidate(candidates, match, value, "de.time-range", protected)
    for match in _TIME.finditer(text):
        hour, minute = int(match["hour"]), int(match["minute"])
        value = (
            f"{'ein' if hour == 1 else _spell(hour, language)} Uhr"
            if minute == 0
            else f"{'ein' if hour == 1 else _spell(hour, language)} Uhr {_spell(minute, language)}"
        )
        _add_candidate(candidates, match, value, "de.time", protected)


def _iter_de_currency_temperature(
    text: str, language: str, protected: tuple[tuple[int, int], ...], candidates: list[Replacement]
) -> None:
    for pattern in (_CURRENCY_PREFIX, _CURRENCY_SUFFIX):
        for match in pattern.finditer(text):
            canonical_id = _currency_id(match["symbol"], language)
            if canonical_id:
                _add_candidate(
                    candidates,
                    match,
                    _currency(match["number"], canonical_id, language),
                    "de.currency",
                    protected,
                )
    for match in _TEMPERATURE.finditer(text):
        unit = match["unit"].lower().replace("°", "")
        value = f"{_number(match['number'], language=language)} Grad {'Celsius' if unit == 'c' else 'Fahrenheit'}"
        _add_candidate(candidates, match, value, "de.temperature", protected)


def _iter_de_unit_matches(
    text: str, language: str, protected: tuple[tuple[int, int], ...], candidates: list[Replacement]
) -> None:
    for unit_match in iter_unit_matches(
        text, resolve_abbr2words_language(language), protected_spans=protected
    ):
        if unit_match.category == "currency" or (
            unit_match.start and text[unit_match.start - 1] in ".,"
        ):
            continue
        if unit_match.category == "magnitude":
            tail = re.match(r"\s+(?P<symbol>[^\W\d_€$£]+|[€$£])", text[unit_match.end :])
            canonical_id = _currency_id(tail["symbol"], language) if tail else None
            if tail and canonical_id:
                base = _quantity(unit_match, text, language)
                if base and not _overlaps(unit_match.start, unit_match.end + tail.end(), protected):
                    candidates.append(
                        Replacement(
                            unit_match.start,
                            unit_match.end + tail.end(),
                            f"{base} {_currency_name(canonical_id)}",
                            "structured",
                            "de",
                            "de.magnitude-currency",
                        )
                    )
                continue
        if not _overlaps(unit_match.start, unit_match.end, protected):
            try:
                replacement = _quantity(unit_match, text, language)
            except (TypeError, ValueError):
                replacement = None
            if replacement:
                candidates.append(
                    Replacement(
                        unit_match.start,
                        unit_match.end,
                        replacement,
                        "structured",
                        "de",
                        "de.quantity",
                    )
                )


def _iter_de_labels(
    text: str, language: str, protected: tuple[tuple[int, int], ...], candidates: list[Replacement]
) -> None:
    for match in _LABEL.finditer(text):
        label = match["label"]
        normalized = label.casefold().replace(" ", "")
        if normalized in {"s.", "seite"}:
            label = "Seite"
        elif normalized in {"lfd.nr.", "laufendenummer"}:
            label = "laufende Nummer"
        _add_candidate(
            candidates, match, f"{label} {_spell(int(match['number']))}", "de.label", protected
        )
    for match in _ORDINAL.finditer(text):
        _add_candidate(
            candidates,
            match,
            _ordinal(int(match["number"]), _ending(text, match.start())),
            "de.ordinal",
            protected,
        )


def iter_replacements(
    text: str,
    *,
    language: str = "de",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []
    _iter_de_dates(text, language, protected, candidates)
    _iter_de_times(text, language, protected, candidates)
    _iter_de_currency_temperature(text, language, protected, candidates)
    _iter_de_unit_matches(text, language, protected, candidates)
    _iter_de_labels(text, language, protected, candidates)
    return tuple(candidates)


__all__ = ["NUMBER_POLICY", "QUANTITY_GRAMMAR", "QuantityGrammar", "iter_replacements"]
