"""Provider-neutral structured written-to-spoken normalization."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from .mapping import Replacement, resolve_replacements


@dataclass(frozen=True, slots=True)
class StageResult:
    """The exact replacements produced by one structured stage."""

    text: str
    replacements: tuple[Replacement, ...]
    reserved: tuple[tuple[int, int], ...] = ()


_NUMBER = r"[+\-−]?(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?"
_DE_DATE = re.compile(
    r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])\.(?P<month>0?[1-9]|1[0-2])\.(?P<year>\d{4})(?!\d)"
)
_DE_TEXT_DATE = re.compile(
    r"(?P<day>0?[1-9]|[12]\d|3[01])\.\s+(?P<month>Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)(?:\s+(?P<year>\d{4}))?",
    re.IGNORECASE,
)
_DE_TIME = re.compile(r"(?<!\d)(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)(?:\s+Uhr)?(?!\d)")
_DE_CURRENCY = re.compile(
    rf"(?<!\w)(?:(?P<prefix>EUR|CHF|USD|GBP|€|\$|£)\s*)?(?P<number>{_NUMBER})\s*(?P<suffix>EUR|CHF|USD|GBP|€|\$|£)?(?!\w)",
    re.IGNORECASE,
)
_DE_TEMPERATURE = re.compile(
    rf"(?<!\w)(?P<number>{_NUMBER})\s*°?\s*(?P<unit>°?C|°?F)(?!\w)", re.IGNORECASE
)
_DE_QUANTITY = re.compile(
    rf"(?<![\w.])(?P<number>{_NUMBER})\s*(?P<unit>kWh|mAh|GHz|MHz|kHz|ltr\.|Stck\.|Std\.|Min\.|Sek\.|Mio\.|Mrd\.|Tsd\.|Wh|Hz|m³|m3|mg|kg|km|cm|mm|mA|g|m|W|V)(?P<dot>\.)?(?!\w)",
)
_DE_LABEL = re.compile(
    r"(?P<label>laufende\s+Nummer|Lfd\.\s*Nr\.|Nummer|Gleis|Kapitel|Absatz|Seite|S\.)\s+(?P<number>\d+)(?!\w)",
    re.IGNORECASE,
)
_DE_ORDINAL = re.compile(r"(?<![\w.])(?P<number>\d+)\.(?=\s+[A-Za-zÄÖÜäöüß])")

_MONTHS = {
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
}
_UNITS = {
    "kwh": ("Kilowattstunde", "Kilowattstunden"),
    "wh": ("Wattstunde", "Wattstunden"),
    "ghz": ("Gigahertz", "Gigahertz"),
    "mhz": ("Megahertz", "Megahertz"),
    "khz": ("Kilohertz", "Kilohertz"),
    "hz": ("Hertz", "Hertz"),
    "std.": ("Stunde", "Stunden"),
    "min.": ("Minute", "Minuten"),
    "sek.": ("Sekunde", "Sekunden"),
    "stck.": ("Stück", "Stücke"),
    "mah": ("Milliamperestunde", "Milliamperestunden"),
    "ma": ("Milliampere", "Milliampere"),
    "kg": ("Kilogramm", "Kilogramm"),
    "g": ("Gramm", "Gramm"),
    "mg": ("Milligramm", "Milligramm"),
    "km": ("Kilometer", "Kilometer"),
    "cm": ("Zentimeter", "Zentimeter"),
    "mm": ("Millimeter", "Millimeter"),
    "m": ("Meter", "Meter"),
    "m3": ("Kubikmeter", "Kubikmeter"),
    "m³": ("Kubikmeter", "Kubikmeter"),
    "ltr.": ("Liter", "Liter"),
    "w": ("Watt", "Watt"),
    "v": ("Volt", "Volt"),
    "tsd.": ("Tausend", "Tausend"),
    "mio.": ("Million", "Millionen"),
    "mrd.": ("Milliarde", "Milliarden"),
}
_CURRENCIES = {"eur": "Euro", "€": "Euro", "usd": "Dollar", "$": "Dollar", "gbp": "Pfund", "£": "Pfund", "chf": "Schweizer Franken"}
_COMPOSITES = {
    "Prof.": "Professor",
    "ggf.": "gegebenenfalls",
    "ca.": "zirka",
    "zzgl.": "zuzüglich",
    "z.B.": "zum Beispiel",
    "z. B.": "zum Beispiel",
    "zB": "zum Beispiel",
    "d.h.": "das heißt",
    "d. h.": "das heißt",
    "u.a.": "unter anderem",
    "u. a.": "unter anderem",
}
_COMPOSITE_RE = re.compile("|".join(re.escape(item) for item in sorted(_COMPOSITES, key=len, reverse=True)))
_LITERAL_RE = re.compile(r"https?://\S+|www\.\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?<!\w)v\d+(?:\.\d+){2,}(?!\w)", re.IGNORECASE)


def _spell(value: int | Decimal) -> str:
    from num2words import num2words

    return str(num2words(value, lang="de"))


def _year_text(year: int) -> str:
    if 1100 <= year < 2000:
        century, remainder = divmod(year, 100)
        prefix = f"{_spell(century)}hundert"
        return prefix if remainder == 0 else f"{prefix}{_spell(remainder)}"
    return _spell(year)


def _parse_number(raw: str) -> Decimal:
    normalized = raw.replace("−", "-").replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(raw) from exc


def _number_text(raw: str, *, one: str | None = None) -> str:
    value = _parse_number(raw)
    negative = value < 0
    value = abs(value)
    if value == value.to_integral_value():
        result = one if value == 1 and one is not None else _spell(int(value))
    else:
        # num2words' decimal rendering is locale-aware and gives the desired
        # "eins Komma fünf" form for German.
        result = _spell(value)
    return f"minus {result}" if negative else result


def _ordinal(value: int, ending: str) -> str:
    from num2words import num2words

    word = str(num2words(value, lang="de", to="ordinal"))
    if ending == "er" and word.endswith("e"):
        return f"{word[:-1]}er"
    if ending == "e":
        return re.sub(r"(?:er|en|em)$", "e", word)
    if ending == "en":
        return re.sub(r"(?:er|e|em)$", "en", word)
    return word


def _context_ending(text: str, start: int) -> str:
    prefix = text[max(0, start - 24) : start].lower()
    if re.search(r"\b(?:am|im|vom|zum|auf\s+der)\s*$", prefix):
        return "en"
    if re.search(r"\b(?:die|auf\s+die|zur)\s*$", prefix):
        return "e"
    if re.search(r"\bder\s*$", prefix):
        return "e"
    return "er"


def _valid_date(day: int, month: int, year: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _date_replacement(match: re.Match[str], text: str) -> str | None:
    day, month, year = int(match["day"]), int(match["month"]), int(match["year"])
    if not _valid_date(day, month, year):
        return None
    ending = "en" if re.search(r"\b(?:am|zum|vom)\s*$", text[max(0, match.start() - 8) : match.start()], re.I) else "er"
    month_name = list(_MONTHS)[month - 1].capitalize()
    return f"{_ordinal(day, ending)} {month_name} {_year_text(year)}"


def _currency_replacement(match: re.Match[str]) -> str | None:
    currency = (match["prefix"] or match["suffix"] or "").lower()
    if not currency:
        return None
    value = _parse_number(match["number"])
    negative = value < 0
    value = abs(value)
    major = int(value)
    cents = int(round((value - major) * 100))
    result = f"{_spell(major)} {_CURRENCIES[currency]}"
    if cents:
        result += f" {_spell(cents)} Cent"
    return f"minus {result}" if negative else result


def _temperature_replacement(match: re.Match[str]) -> str:
    unit = match["unit"].lower().replace("°", "")
    return f"{_number_text(match['number'])} Grad {'Celsius' if unit == 'c' else 'Fahrenheit'}"


def _quantity_replacement(match: re.Match[str], text: str, *, terminal_end: int | None = None) -> str:
    raw = match["number"]
    unit_key = match["unit"].lower()
    singular, plural = _UNITS[unit_key]
    value = _parse_number(raw)
    noun = singular if value == 1 else plural
    one = "ein" if unit_key in {"kg", "g", "mg", "km", "cm", "mm", "m", "m3", "m³", "ltr.", "w", "v", "kwh", "wh", "ghz", "mhz", "khz", "hz", "std.", "min.", "sek.", "stck.", "mah", "ma", "tsd."} else None
    number = _number_text(raw, one=one)
    if value == 1 and unit_key in {"std.", "min.", "sek.", "ltr.", "mio.", "mrd."}:
        number = {"std.": "eine", "min.": "eine", "sek.": "eine", "ltr.": "ein", "mio.": "eine", "mrd.": "eine"}[unit_key]
    result = f"{number} {noun}"
    if (match["dot"] or unit_key.endswith(".")) and _terminal_dot(text, terminal_end or match.end()):
        result += "."
    return result


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \\t\n\"'”’»)]}")


def iter_structured_replacements(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return exact, non-overlapping semantic replacements for one language."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    base = language.strip().lower().replace("_", "-").split("-", 1)[0]
    if base != "de":
        return ()
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []

    def add(match: re.Match[str], value: str | None, rule: str, kind: str = "structured") -> None:
        if value is None or any(match.start() < end and start < match.end() for start, end in protected):
            return
        candidates.append(Replacement(match.start(), match.end(), value, kind, "de", rule))

    for match in _DE_DATE.finditer(text):
        add(match, _date_replacement(match, text), "de.date")
    for match in _DE_TEXT_DATE.finditer(text):
        month = _MONTHS[match["month"].lower()]
        year = int(match["year"] or 2000)
        if match["year"] and _valid_date(int(match["day"]), month, year):
            ending = _context_ending(text, match.start())
            add(match, f"{_ordinal(int(match['day']), ending)} {match['month']} {match['year']}", "de.text-date")
    for match in _DE_TIME.finditer(text):
        hour, minute = int(match["hour"]), int(match["minute"])
        hour_text = "ein" if hour == 1 else _spell(hour)
        value = f"{hour_text} Uhr" if minute == 0 else f"{hour_text} Uhr {_spell(minute)}"
        add(match, value, "de.time")
    for match in _DE_CURRENCY.finditer(text):
        add(match, _currency_replacement(match), "de.currency")
    for match in _DE_TEMPERATURE.finditer(text):
        add(match, _temperature_replacement(match), "de.temperature")
    for match in _DE_QUANTITY.finditer(text):
        unit_key = match["unit"].lower()
        end = match.end()
        if match["dot"] and not unit_key.endswith("."):
            end -= 1
        value = _quantity_replacement(match, text, terminal_end=end)
        if end != match.end():
            if value.endswith("."):
                value = value[:-1]
            candidate = Replacement(match.start(), end, value, "structured", "de", "de.quantity")
            if not any(candidate.start < right and left < candidate.end for left, right in protected):
                candidates.append(candidate)
            continue
        add(match, value, "de.quantity")
    for match in _DE_LABEL.finditer(text):
        label = match["label"].lower()
        label_text = {
            "s.": "Seite",
            "lfd. nr.": "laufende Nummer",
        }.get(label, label)
        add(match, f"{label_text} {_spell(int(match['number']))}", "de.label")
    for match in _DE_ORDINAL.finditer(text):
        add(match, _ordinal(int(match["number"]), _context_ending(text, match.start())), "de.ordinal")
    # Lexical abbreviations such as Prof., ggf., ca., and z. B. remain owned
    # by abbr2words.  Structured normalization only classifies expressions
    # whose numeric content changes their semantics.
    return resolve_replacements(tuple(candidates), source_length=len(text))


def normalize_structured(
    text: str,
    *,
    language: str,
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> StageResult:
    """Normalize structured values and return exact semantic provenance."""
    replacements = iter_structured_replacements(
        text, language=language, protected_ranges=protected_ranges
    )
    from .mapping import apply_replacements

    result, _, _ = apply_replacements(text, replacements, stage="structured")
    return StageResult(result, replacements)


__all__ = ["StageResult", "iter_structured_replacements", "normalize_structured"]
