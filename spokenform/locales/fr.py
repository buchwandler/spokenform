"""French semantic grammar owned by spokenform.

The French unit and currency inventory is supplied by :mod:`abbr2words`.
This module only realizes its canonical identities in French grammar and
produces source-aligned semantic candidates for the shared dispatcher.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from abbr2words import UnitMatch, iter_unit_matches

from ..config import NumberPolicy
from ..dates import _valid_date, expand_year
from ..language import resolve_abbr2words_language
from ..mapping import Replacement
from ..number_words import number_words
from ..numeric_lexeme import fraction_digit_groups, numeric_speech_policy, parse_numeric_lexeme

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
    "speed-meter-per-second": QuantityGrammar(
        "speed-meter-per-second", "mètre par seconde", "mètres par seconde"
    ),
    "speed-kilometer-per-hour": QuantityGrammar(
        "speed-kilometer-per-hour", "kilomètre par heure", "kilomètres par heure"
    ),
    "area-square-millimeter": QuantityGrammar(
        "area-square-millimeter", "millimètre carré", "millimètres carrés"
    ),
    "area-square-centimeter": QuantityGrammar(
        "area-square-centimeter", "centimètre carré", "centimètres carrés"
    ),
    "area-square-meter": QuantityGrammar("area-square-meter", "mètre carré", "mètres carrés"),
    "area-square-kilometer": QuantityGrammar(
        "area-square-kilometer", "kilomètre carré", "kilomètres carrés"
    ),
    "area-hectare": QuantityGrammar("area-hectare", "hectare", "hectares"),
    "volume-cubic-millimeter": QuantityGrammar(
        "volume-cubic-millimeter", "millimètre cube", "millimètres cubes"
    ),
    "volume-cubic-centimeter": QuantityGrammar(
        "volume-cubic-centimeter", "centimètre cube", "centimètres cubes"
    ),
    "volume-cubic-meter": QuantityGrammar("volume-cubic-meter", "mètre cube", "mètres cubes"),
}
QUANTITY_GRAMMAR.update(
    {
        "data-byte": QuantityGrammar("data-byte", "octet", "octets"),
        "data-kilobyte": QuantityGrammar("data-kilobyte", "kilooctet", "kilooctets"),
        "data-megabyte": QuantityGrammar("data-megabyte", "mégaoctet", "mégaoctets"),
        "data-gigabyte": QuantityGrammar("data-gigaoctet", "gigaoctet", "gigaoctets"),
        "flow-cubic-meter-per-second": QuantityGrammar(
            "flow-cubic-meter-per-second", "mètre cube par seconde", "mètres cubes par seconde"
        ),
        "fuel-consumption-liter-per-100-kilometer": QuantityGrammar(
            "fuel-consumption-liter-per-100-kilometer",
            "litre aux cent kilomètres",
            "litres aux cent kilomètres",
        ),
        "pressure-atmosphere": QuantityGrammar("pressure-atmosphere", "atmosphère", "atmosphères"),
        "pressure-kilopascal": QuantityGrammar("pressure-kilopascal", "kilopascal", "kilopascals"),
        "pressure-pascal": QuantityGrammar("pressure-pascal", "pascal", "pascals"),
        "speed-mile-per-hour": QuantityGrammar(
            "speed-mile-per-hour", "mille par heure", "milles par heure"
        ),
        "temperature-celsius": QuantityGrammar(
            "temperature-celsius", "degré Celsius", "degrés Celsius"
        ),
        "temperature-fahrenheit": QuantityGrammar(
            "temperature-fahrenheit", "degré Fahrenheit", "degrés Fahrenheit"
        ),
        "power-watt": QuantityGrammar("power-watt", "watt", "watts"),
        "power-kilowatt": QuantityGrammar("power-kilowatt", "kilowatt", "kilowatts"),
        "energy-watt-hour": QuantityGrammar("energy-watt-hour", "watt-heure", "watt-heures"),
        "energy-kilowatt-hour": QuantityGrammar(
            "energy-kilowatt-hour", "kilowatt-heure", "kilowatt-heures"
        ),
        "frequency-hertz": QuantityGrammar("frequency-hertz", "hertz", "hertz"),
        "frequency-kilohertz": QuantityGrammar("frequency-kilohertz", "kilohertz", "kilohertz"),
        "frequency-megahertz": QuantityGrammar("frequency-megahertz", "mégahertz", "mégahertz"),
        "frequency-gigahertz": QuantityGrammar("frequency-gigahertz", "gigahertz", "gigahertz"),
        "length-nanometer": QuantityGrammar("length-nanometer", "nanomètre", "nanomètres"),
        "current-ampere": QuantityGrammar("current-ampere", "ampère", "ampères"),
        "current-milliampere": QuantityGrammar(
            "current-milliampere", "milliampère", "milliampères"
        ),
        "charge-milliampere-hour": QuantityGrammar(
            "charge-milliampere-hour", "milliampère-heure", "milliampère-heures"
        ),
        "voltage-volt": QuantityGrammar("voltage-volt", "volt", "volts"),
        "luminous-flux-lumen": QuantityGrammar("luminous-flux-lumen", "lumen", "lumens"),
        "force-newton": QuantityGrammar("force-newton", "newton", "newtons"),
        "energy-joule": QuantityGrammar("energy-joule", "joule", "joules"),
        "pressure-millimeter-mercury": QuantityGrammar(
            "pressure-millimeter-mercury", "millimètre de mercure", "millimètres de mercure"
        ),
        "amount-mole": QuantityGrammar("amount-mole", "mole", "moles"),
        "concentration-molar": QuantityGrammar("concentration-molar", "molaire", "molaires"),
        "customary-pound": QuantityGrammar("customary-pound", "livre", "livres"),
        "temperature-kelvin": QuantityGrammar("temperature-kelvin", "kelvin", "kelvins"),
    }
)

_NUMBER = r"[+\-−]?(?:(?:\d+(?:[.,]\d+)+)|(?:\d{1,3}(?:[.\s\u00a0\u202f]\d{3})+)|\d+|[.,]\d+)"
_DATE_DMY = re.compile(
    r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])[./-](?P<month>0?[1-9]|1[0-2])[./-](?P<year>\d{4})(?!\d)"
)
_DATE_ISO = re.compile(
    r"(?<![\w.])(?P<year>\d{4})-(?P<month>0?[1-9]|1[0-2])-(?P<day>0?[1-9]|[12]\d|3[01])(?!\d)"
)
_DATE_DMY_SHORT = re.compile(
    r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])[./-](?P<month>0?[1-9]|1[0-2])[./-](?P<year>\d{2})(?!\d)"
)
_DATE_DMY_NO_YEAR = re.compile(
    r"(?<![\w./])(?P<day>0?[1-9]|[12]\d|3[01])/(?P<month>0?[1-9]|1[0-2])(?![\w/])"
)
_DATE_CANDIDATE = re.compile(r"(?<![\w.])(?:\d{1,2}[./]){2}\d{2,4}(?!\d)")
_TIME_COLON = re.compile(r"(?<![\w.])(?P<hour>\d{1,2}):(?P<minute>\d{2})(?!\d)")
_TIME_H = re.compile(
    r"(?<![\w.])(?P<hour>\d{1,2})\s*h(?:(?:\s*)(?P<minute>\d{2}))?(?!\w)", re.IGNORECASE
)
_TIME_CANDIDATE = re.compile(r"(?<![\w.])\d{1,2}\s*(?::\s*\d{2}|h\s*\d{0,2})(?!\w)", re.IGNORECASE)
_ORDINAL = re.compile(
    r"(?<![\w.,])(?P<number>\d+)\s*(?P<suffix>er|ère|re|ème|e|nd|nde)\b", re.IGNORECASE
)
_PLAIN_NUMBER = re.compile(rf"(?<![\w.])(?P<number>{_NUMBER})(?![.,]\d)(?![\w.])")
_MONTHS = (
    "janvier",
    "février",
    "mars",
    "avril",
    "mai",
    "juin",
    "juillet",
    "août",
    "septembre",
    "octobre",
    "novembre",
    "décembre",
)
_TEXT_DATE = re.compile(
    r"(?P<day>0?[1-9]|[12]\d|3[01])\s+(?P<month>janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre|janv\.?|févr\.?|févr\.?|avr\.?|juil\.?|sept\.?|oct\.?|nov\.?|déc\.?|dec\.?)\s*(?P<year>\d{2,4})?",
    re.IGNORECASE,
)


def _spell(value: int | Decimal, language: str = "fr", *, ordinal: bool = False) -> str:
    return str(
        number_words(
            value,
            lang=language,
            to="ordinal" if ordinal else "cardinal",
        )
    )


def _parts(raw: str, language: str = "fr") -> tuple[bool, int, str | None]:
    lexeme = parse_numeric_lexeme(raw, language, context="quantity")
    if lexeme is None:
        raise ValueError(f"Cannot parse French number {raw!r}")
    return lexeme.negative, int(lexeme.integer_digits), lexeme.fraction_digits


def _number_text(raw: str, language: str = "fr") -> str:
    negative, integer, fraction = _parts(raw, language)
    result = _spell(integer, language)
    if fraction is not None:
        policy = numeric_speech_policy(language)
        result += (
            " "
            + policy.decimal_word
            + " "
            + " ".join(
                _spell(int(group), language) for group in fraction_digit_groups(fraction, language)
            )
        )
    return f"moins {result}" if negative else result


def _decimal(raw: str, language: str = "fr") -> Decimal:
    negative, integer, fraction = _parts(raw, language)
    normalized = f"{'-' if negative else ''}{integer}"
    if fraction is not None:
        normalized += f".{fraction}"
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(raw) from exc


def _date_like_context(text: str, start: int, end: int, *, day: int) -> bool:
    if start == 0 and end == len(text):
        return day >= 4
    left = text[max(0, start - 24) : start].casefold()
    return day > 12 or bool(re.search(r"\b(?:le|du|au|date)\s*$", left))


def _date_text(
    day: int,
    month: int,
    year: int,
    language: str = "fr",
    *,
    year_digits: int | None = None,
) -> str:
    day_text = "premier" if day == 1 else _spell(day, language)
    year_text = _spell(year % 100 if year_digits == 2 else year, language)
    return f"{day_text} {_MONTHS[month - 1]} {year_text}"


def _time_text(hour: int, minute: int, language: str = "fr") -> str:
    hour_text = "une heure" if hour == 1 else f"{_spell(hour, language)} heures"
    return hour_text if minute == 0 else f"{hour_text} {_spell(minute, language)}"


def _ordinal_text(value: int, suffix: str, language: str = "fr") -> str:
    suffix = suffix.casefold()
    if value == 1 and suffix in {"ère", "re"}:
        return "première"
    if value == 1:
        return "premier"
    if value == 2 and suffix == "nd":
        return "second"
    if value == 2 and suffix == "nde":
        return "seconde"
    return _spell(value, language, ordinal=True)


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \t\n\"'”’»)]}")


def _quantity_text(match: UnitMatch, text: str, language: str = "fr") -> str | None:
    canonical_id = match.canonical_id or ""
    if canonical_id.startswith("currency-"):
        return _currency_text(match.value, canonical_id, language)
    grammar = QUANTITY_GRAMMAR.get(canonical_id)
    if canonical_id == "temperature-celsius" or canonical_id == "temperature-fahrenheit":
        unit = "Celsius" if canonical_id.endswith("celsius") else "Fahrenheit"
        value = _decimal(match.value, language)
        noun = f"degré {unit}" if value == 1 else f"degrés {unit}"
        return f"{_number_text(match.value, language)} {noun}"
    if grammar is None:
        return None
    value = _decimal(match.value, language)
    noun = grammar.singular if value == 1 else grammar.plural
    result = f"{_number_text(match.value, language)} {noun}"
    if match.symbol.endswith(".") and _terminal_dot(text, match.end):
        result += "."
    return result


def _currency_text(raw: str, canonical_id: str, language: str = "fr") -> str:
    negative, integer, fraction = _parts(raw, language)
    major_names = {
        "currency-euro": ("euro", "euros", "centime", "centimes"),
        "currency-us-dollar": ("dollar", "dollars", "cent", "cents"),
        "currency-pound-sterling": ("livre sterling", "livres sterling", "penny", "pence"),
        "currency-swiss-franc": ("franc suisse", "francs suisses", "centime", "centimes"),
        "currency-japanese-yen": ("yen", "yens", None, None),
        "currency-mexican-peso": ("peso mexicain", "pesos mexicains", "centime", "centimes"),
        "currency-indian-rupee": ("roupie", "roupies", "païse", "païses"),
        "currency-south-korean-won": ("won", "wons", None, None),
    }
    singular, plural, minor_singular, minor_plural = major_names.get(
        canonical_id, (canonical_id, canonical_id, "centime", "centimes")
    )
    major = singular if integer == 1 else plural
    result = f"{_spell(integer, language)} {major}"
    if fraction is not None:
        minor = int((fraction + "00")[:2])
        if minor and minor_singular is not None and minor_plural is not None:
            minor_name = minor_singular if minor == 1 else minor_plural
            result += f" {_spell(minor, language)} {minor_name}"
    return f"moins {result}" if negative else result


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def _add_candidate(
    candidates: list[Replacement],
    start: int,
    end: int,
    value: str | None,
    rule: str,
    protected: tuple[tuple[int, int], ...],
) -> None:
    if value is not None and not _overlaps(start, end, protected):
        candidates.append(Replacement(start, end, value, "structured", "fr", rule))


def _iter_fr_dates(
    text: str,
    language: str,
    protected: tuple[tuple[int, int], ...],
    candidates: list[Replacement],
) -> None:
    for match in _DATE_DMY_NO_YEAR.finditer(text):
        day, month = int(match["day"]), int(match["month"])
        if _valid_date(day, month, 2000) and _date_like_context(
            text, match.start(), match.end(), day=day
        ):
            _add_candidate(
                candidates,
                match.start(),
                match.end(),
                f"{_spell(day, language)} {_MONTHS[month - 1]}",
                "fr.date",
                protected,
            )
    for match in _DATE_DMY_SHORT.finditer(text):
        year, _ = expand_year(match["year"])
        day, month = int(match["day"]), int(match["month"])
        if _valid_date(day, month, year):
            _add_candidate(
                candidates,
                match.start(),
                match.end(),
                _date_text(day, month, year, language, year_digits=len(match["year"])),
                "fr.date",
                protected,
            )
    aliases = {name[:3]: index for index, name in enumerate(_MONTHS, 1)}
    aliases.update({"fev": 2, "aou": 8, "dec": 12})
    for match in _TEXT_DATE.finditer(text):
        text_month = aliases.get(match["month"].lower().rstrip(".")[:3])
        if text_month is None:
            continue
        text_year = expand_year(match["year"])[0] if match["year"] else None
        day = int(match["day"])
        if text_year is None or _valid_date(day, text_month, text_year):
            value = _date_text(
                day,
                text_month,
                text_year or 2000,
                language,
                year_digits=len(match["year"]) if match["year"] else None,
            )
            if text_year is None:
                value = f"{_spell(day, language)} {_MONTHS[text_month - 1]}"
            _add_candidate(candidates, match.start(), match.end(), value, "fr.date", protected)
    for pattern in (_DATE_DMY, _DATE_ISO):
        for match in pattern.finditer(text):
            day, month, year = int(match["day"]), int(match["month"]), int(match["year"])
            if _valid_date(day, month, year):
                _add_candidate(
                    candidates,
                    match.start(),
                    match.end(),
                    _date_text(day, month, year, language),
                    "fr.date",
                    protected,
                )


def _iter_fr_times(
    text: str, language: str, protected: tuple[tuple[int, int], ...], candidates: list[Replacement]
) -> None:
    for match in _TIME_H.finditer(text):
        hour, minute = int(match["hour"]), int(match["minute"] or 0)
        if hour <= 23 and minute <= 59:
            _add_candidate(
                candidates,
                match.start(),
                match.end(),
                _time_text(hour, minute, language),
                "fr.time",
                protected,
            )
    for match in _TIME_COLON.finditer(text):
        hour, minute = int(match["hour"]), int(match["minute"])
        if hour <= 23 and minute <= 59:
            _add_candidate(
                candidates,
                match.start(),
                match.end(),
                _time_text(hour, minute, language),
                "fr.time",
                protected,
            )


def _iter_fr_ordinals(
    text: str, language: str, protected: tuple[tuple[int, int], ...], candidates: list[Replacement]
) -> None:
    for match in _ORDINAL.finditer(text):
        _add_candidate(
            candidates,
            match.start(),
            match.end(),
            _ordinal_text(int(match["number"]), match["suffix"], language),
            "fr.ordinal",
            protected,
        )


def _iter_fr_quantities(
    text: str, language: str, protected: tuple[tuple[int, int], ...], candidates: list[Replacement]
) -> None:
    for unit_match in iter_unit_matches(
        text, resolve_abbr2words_language(language), protected_spans=protected
    ):
        try:
            replacement = _quantity_text(unit_match, text, language)
        except (InvalidOperation, TypeError, ValueError):
            replacement = None
        rule = "fr.currency" if unit_match.category == "currency" else "fr.quantity"
        _add_candidate(candidates, unit_match.start, unit_match.end, replacement, rule, protected)


def _iter_fr_plain_numbers(
    text: str, language: str, protected: tuple[tuple[int, int], ...], candidates: list[Replacement]
) -> None:
    excluded = [match.span() for match in _DATE_CANDIDATE.finditer(text)]
    excluded.extend(match.span() for match in _TIME_CANDIDATE.finditer(text))
    for match in _PLAIN_NUMBER.finditer(text):
        if any(left <= match.start() and match.end() <= right for left, right in excluded):
            continue
        if re.fullmatch(r"v?\d+(?:\.\d+){2,}", match["number"], re.IGNORECASE):
            continue
        _add_candidate(
            candidates,
            match.start(),
            match.end(),
            _number_text(match["number"], language),
            "fr.number",
            protected,
        )


def iter_replacements(
    text: str,
    *,
    language: str = "fr",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return French structured candidates before shared conflict resolution."""
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []
    _iter_fr_dates(text, language, protected, candidates)
    _iter_fr_times(text, language, protected, candidates)
    _iter_fr_ordinals(text, language, protected, candidates)
    _iter_fr_quantities(text, language, protected, candidates)
    _iter_fr_plain_numbers(text, language, protected, candidates)
    return tuple(candidates)


__all__ = ["NUMBER_POLICY", "QUANTITY_GRAMMAR", "QuantityGrammar", "iter_replacements"]
