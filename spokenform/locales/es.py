"""Spanish semantic grammar owned by spokenform.

Written symbols and lexical abbreviations are recognized by :mod:`abbr2words`.
This module only realizes the canonical identities returned by that API and
emits exact source-aligned semantic replacements.
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
from ..numeric_lexeme import fraction_digit_groups, numeric_speech_policy, parse_numeric_lexeme

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN


@dataclass(frozen=True, slots=True)
class QuantityGrammar:
    canonical_id: str
    gender: str
    singular: str
    plural: str


QUANTITY_GRAMMAR: dict[str, QuantityGrammar] = {
    "duration-second": QuantityGrammar("duration-second", "m", "segundo", "segundos"),
    "duration-minute": QuantityGrammar("duration-minute", "m", "minuto", "minutos"),
    "duration-hour": QuantityGrammar("duration-hour", "f", "hora", "horas"),
    "duration-day": QuantityGrammar("duration-day", "m", "día", "días"),
    "length-millimeter": QuantityGrammar("length-millimeter", "m", "milímetro", "milímetros"),
    "length-centimeter": QuantityGrammar("length-centimeter", "m", "centímetro", "centímetros"),
    "length-meter": QuantityGrammar("length-meter", "m", "metro", "metros"),
    "length-kilometer": QuantityGrammar("length-kilometer", "m", "kilómetro", "kilómetros"),
    "volume-milliliter": QuantityGrammar("volume-milliliter", "m", "mililitro", "mililitros"),
    "volume-liter": QuantityGrammar("volume-liter", "m", "litro", "litros"),
    "mass-microgram": QuantityGrammar("mass-microgram", "m", "microgramo", "microgramos"),
    "mass-milligram": QuantityGrammar("mass-milligram", "m", "miligramo", "miligramos"),
    "mass-gram": QuantityGrammar("mass-gram", "m", "gramo", "gramos"),
    "mass-kilogram": QuantityGrammar("mass-kilogram", "m", "kilogramo", "kilogramos"),
    "mass-tonne": QuantityGrammar("mass-tonne", "f", "tonelada", "toneladas"),
    "area-square-millimeter": QuantityGrammar(
        "area-square-millimeter", "m", "milímetro cuadrado", "milímetros cuadrados"
    ),
    "area-square-centimeter": QuantityGrammar(
        "area-square-centimeter", "m", "centímetro cuadrado", "centímetros cuadrados"
    ),
    "area-square-meter": QuantityGrammar(
        "area-square-meter", "m", "metro cuadrado", "metros cuadrados"
    ),
    "area-square-kilometer": QuantityGrammar(
        "area-square-kilometer", "m", "kilómetro cuadrado", "kilómetros cuadrados"
    ),
    "area-hectare": QuantityGrammar("area-hectare", "m", "hectárea", "hectáreas"),
    "volume-cubic-millimeter": QuantityGrammar(
        "volume-cubic-millimeter", "m", "milímetro cúbico", "milímetros cúbicos"
    ),
    "volume-cubic-centimeter": QuantityGrammar(
        "volume-cubic-centimeter", "m", "centímetro cúbico", "centímetros cúbicos"
    ),
    "volume-cubic-meter": QuantityGrammar(
        "volume-cubic-meter", "m", "metro cúbico", "metros cúbicos"
    ),
    "speed-meter-per-second": QuantityGrammar(
        "speed-meter-per-second", "m", "metro por segundo", "metros por segundo"
    ),
    "speed-kilometer-per-hour": QuantityGrammar(
        "speed-kilometer-per-hour", "m", "kilómetro por hora", "kilómetros por hora"
    ),
}
QUANTITY_GRAMMAR.update(
    {
        "data-byte": QuantityGrammar("data-byte", "m", "byte", "bytes"),
        "data-kilobyte": QuantityGrammar("data-kilobyte", "m", "kilobyte", "kilobytes"),
        "data-megabyte": QuantityGrammar("data-megabyte", "m", "megabyte", "megabytes"),
        "data-gigabyte": QuantityGrammar("data-gigabyte", "m", "gigabyte", "gigabytes"),
        "flow-cubic-meter-per-second": QuantityGrammar("flow-cubic-meter-per-second", "m", "metro cúbico por segundo", "metros cúbicos por segundo"),
        "fuel-consumption-liter-per-100-kilometer": QuantityGrammar("fuel-consumption-liter-per-100-kilometer", "m", "litro por cien kilómetros", "litros por cien kilómetros"),
        "pressure-atmosphere": QuantityGrammar("pressure-atmosphere", "f", "atmósfera", "atmósferas"),
        "pressure-kilopascal": QuantityGrammar("pressure-kilopascal", "m", "kilopascal", "kilopascales"),
        "pressure-pascal": QuantityGrammar("pressure-pascal", "m", "pascal", "pascales"),
        "speed-mile-per-hour": QuantityGrammar("speed-mile-per-hour", "m", "milla por hora", "millas por hora"),
        "temperature-kelvin": QuantityGrammar("temperature-kelvin", "m", "kelvin", "kelvin"),
        "temperature-celsius": QuantityGrammar("temperature-celsius", "m", "grado Celsius", "grados Celsius"),
        "temperature-fahrenheit": QuantityGrammar("temperature-fahrenheit", "m", "grado Fahrenheit", "grados Fahrenheit"),
        "power-watt": QuantityGrammar("power-watt", "m", "vatio", "vatios"),
        "power-kilowatt": QuantityGrammar("power-kilowatt", "m", "kilovatio", "kilovatios"),
        "energy-watt-hour": QuantityGrammar("energy-watt-hour", "m", "vatio-hora", "vatios-hora"),
        "energy-kilowatt-hour": QuantityGrammar("energy-kilowatt-hour", "m", "kilovatio-hora", "kilovatios-hora"),
        "frequency-hertz": QuantityGrammar("frequency-hertz", "m", "hercio", "hercios"),
        "frequency-kilohertz": QuantityGrammar("frequency-kilohertz", "m", "kilohercio", "kilohercios"),
        "frequency-megahertz": QuantityGrammar("frequency-megahertz", "m", "megahercio", "megahercios"),
        "frequency-gigahertz": QuantityGrammar("frequency-gigahertz", "m", "gigahercio", "gigahercios"),
        "length-nanometer": QuantityGrammar("length-nanometer", "m", "nanómetro", "nanómetros"),
        "current-ampere": QuantityGrammar("current-ampere", "m", "amperio", "amperios"),
        "current-milliampere": QuantityGrammar("current-milliampere", "m", "miliamperio", "miliamperios"),
        "charge-milliampere-hour": QuantityGrammar("charge-milliampere-hour", "m", "miliamperio-hora", "miliamperios-hora"),
        "voltage-volt": QuantityGrammar("voltage-volt", "m", "voltio", "voltios"),
        "luminous-flux-lumen": QuantityGrammar("luminous-flux-lumen", "m", "lumen", "lúmenes"),
        "force-newton": QuantityGrammar("force-newton", "m", "newton", "newtons"),
        "energy-joule": QuantityGrammar("energy-joule", "m", "julio", "julios"),
        "pressure-millimeter-mercury": QuantityGrammar("pressure-millimeter-mercury", "m", "milímetro de mercurio", "milímetros de mercurio"),
        "amount-mole": QuantityGrammar("amount-mole", "m", "mol", "moles"),
        "concentration-molar": QuantityGrammar("concentration-molar", "m", "molar", "molares"),
        "customary-pound": QuantityGrammar("customary-pound", "m", "libra", "libras"),
    }
)

_NUMBER = r"[+\-−]?(?:(?:\d{1,3}(?:[.\s\u00a0\u202f]\d{3})+|\d+)(?:,\d+)?|,\d+)"
_DATE_DMY = re.compile(r"(?<![\w.])(?P<day>\d{1,2})[./](?P<month>\d{1,2})[./](?P<year>\d{4})(?!\d)")
_DATE_ISO = re.compile(r"(?<![\w.])(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})(?!\d)")
_DATE_DMY_SHORT = re.compile(r"(?<![\w.])(?P<day>\d{1,2})[./](?P<month>\d{1,2})[./](?P<year>\d{2})(?!\d)")
_DATE_DMY_NO_YEAR = re.compile(
    r"(?<![\w./])(?P<day>0?[1-9]|[12]\d|3[01])/(?P<month>0?[1-9]|1[0-2])(?![\w/])"
)
_DATE_DMY_HYPHEN = re.compile(r"(?<![\w.])(?P<day>\d{1,2})-(?P<month>\d{1,2})-(?P<year>\d{2,4})(?!\d)")
_DATE_CANDIDATE = re.compile(r"(?<![\w.])(?:\d{1,2}[./]){2}\d{4}(?!\d)")
_TIME_CANDIDATE = re.compile(r"(?<![\w.])\d{1,2}:\d{2}(?!\d)")
_TIME_COLON = re.compile(
    r"(?<!\w)(?P<hour>\d{1,2}):(?P<minute>[0-5]\d)(?:\s*(?P<period>a\.?\s*m\.?|p\.?\s*m\.?))?(?!\w)",
    re.IGNORECASE,
)
_TIME_HOURS = re.compile(
    r"(?<!\w)(?P<hour>\d{1,2}):(?P<minute>[0-5]\d)\s*(?:hrs?\.?|horas?)(?!\w)",
    re.IGNORECASE,
)
_MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
_TEXT_DATE = re.compile(
    r"(?P<day>\d{1,2})\s+(?P<month>enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre|ene\.?|feb\.?|mar\.?|abr\.?|may\.?|jun\.?|jul\.?|ago\.?|sep\.?|oct\.?|nov\.?|dic\.?)\s*(?P<year>\d{2,4})?",
    re.IGNORECASE,
)
_TEXT_DATE_DE = re.compile(
    r"(?P<day>\d{1,2})\s+de\s+(?P<month>enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)"
    r"(?:\s+de)?\s*(?P<year>\d{2,4})?",
    re.IGNORECASE,
)
_ORDINAL_SYMBOL = re.compile(
    r"(?<![\w.])(?P<number>\d+)(?P<suffix>\.?[ºª]|er|[oa])(?!\w)", re.IGNORECASE
)


def _parts(raw: str, language: str = "es", *, context: str = "quantity") -> tuple[bool, int, str | None]:
    lexeme = parse_numeric_lexeme(raw, language, context=context)
    if lexeme is None:
        raise ValueError(f"Cannot parse Spanish number {raw!r}")
    return lexeme.negative, int(lexeme.integer_digits), lexeme.fraction_digits


def _decimal(raw: str, language: str = "es") -> Decimal:
    negative, integer, fraction = _parts(raw, language)
    value = f"{'-' if negative else ''}{integer}"
    if fraction is not None:
        value += f".{fraction}"
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Cannot parse Spanish number {raw!r}") from exc


def _spell(value: int, language: str = "es") -> str:
    return str(num2words(value, lang=resolve_num2words_language(language)))


def _apocopate(text: str, gender: str) -> str:
    """Apply reviewed Spanish one-ending agreement before a noun."""
    if gender == "f":
        return text[:-3] + "una" if text.endswith("uno") else text
    if text.endswith("veintiuno"):
        return f"{text[:-8]}veintiún"
    if text.endswith(" y uno"):
        return f"{text[:-5]} y un"
    if text.endswith("uno"):
        return f"{text[:-3]}un"
    return text


def _number_text(
    raw: str,
    *,
    gender: str | None = None,
    apocopate: bool = False,
    language: str = "es",
) -> str:
    negative, integer, fraction = _parts(raw, language)
    if fraction is None:
        result = _spell(integer, language)
        if apocopate:
            result = _apocopate(result, gender or "m")
    else:
        policy = numeric_speech_policy(language)
        result = f"{_spell(integer, language)} {policy.decimal_word} " + " ".join(
            _spell(int(group), language) for group in fraction_digit_groups(fraction, language)
        )
    return f"menos {result}" if negative else result


def _valid_date(day: int, month: int, year: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _date_like_context(text: str, start: int, end: int, *, day: int) -> bool:
    if start == 0 and end == len(text):
        return day >= 4
    left = text[max(0, start - 24) : start].casefold()
    return day > 12 or bool(re.search(r"\b(?:el|del|fecha)\s*$", left))


def _date_text(day: int, month: int, year: int, language: str = "es") -> str:
    return f"{_spell(day, language)} de {_MONTHS[month - 1]} de {_spell(year, language)}"


def _time_text(hour: int, minute: int, period: str | None, language: str = "es") -> str:
    """Render Spanish clock times with an explicit locale policy."""
    if period:
        normalized = period.casefold().replace(".", "").replace(" ", "")
        display_hour = hour % 12 or 12
        suffix = "de la mañana" if normalized == "am" else "de la tarde"
        parts = [_spell(display_hour, language)]
        if minute:
            parts.extend(("y", _spell(minute, language)))
        return f"{' '.join(parts)} {suffix}"
    parts = [_spell(hour, language)]
    if minute:
        parts.extend(("y", _spell(minute, language)))
    return " ".join(parts)


def _ordinal_text(number: int, suffix: str, language: str = "es") -> str:
    """Render high-confidence Spanish ordinal markers with local gender."""
    ordinal = str(num2words(number, lang=resolve_num2words_language(language), to="ordinal"))
    suffix = suffix.casefold().replace(".", "")
    if suffix in {"a", "ª"} and ordinal.endswith("o"):
        return f"{ordinal[:-1]}a"
    if suffix in {"er"} and ordinal.endswith(("ero", "ercero")):
        return ordinal[:-1]
    return str(num2words(number, lang=resolve_num2words_language(language), to="ordinal"))


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \t\n\"'”’»)]}")


def _quantity_text(match: UnitMatch, text: str, language: str = "es") -> str | None:
    canonical_id = match.canonical_id or ""
    if canonical_id.startswith("currency-"):
        return _currency_text(match.value, canonical_id, language)
    if canonical_id in {"temperature-celsius", "temperature-fahrenheit"}:
        unit = "Celsius" if canonical_id.endswith("celsius") else "Fahrenheit"
        value = _decimal(match.value, language)
        noun = f"grado {unit}" if abs(value) == 1 else f"grados {unit}"
        return f"{_number_text(match.value, gender='m', apocopate=',' not in match.value, language=language)} {noun}"
    grammar = QUANTITY_GRAMMAR.get(canonical_id)
    if grammar is None:
        return None
    value = _decimal(match.value, language)
    noun = grammar.singular if abs(value) == 1 else grammar.plural
    result = _number_text(
        match.value,
        gender=grammar.gender,
        apocopate="," not in match.value,
        language=language,
    )
    if match.symbol.endswith(".") and _terminal_dot(text, match.end):
        noun += "."
    return f"{result} {noun}"


def _currency_text(raw: str, canonical_id: str, language: str = "es") -> str:
    negative, integer, fraction = _parts(raw, language)
    names = {
        "currency-euro": ("euro", "euros", "céntimo", "céntimos"),
        "currency-us-dollar": ("dólar", "dólares", "centavo", "centavos"),
        "currency-pound-sterling": ("libra esterlina", "libras esterlinas", "penique", "peniques"),
        "currency-mexican-peso": ("peso mexicano", "pesos mexicanos", "centavo", "centavos"),
        "currency-swiss-franc": ("franco suizo", "francos suizos", "céntimo", "céntimos"),
        "currency-japanese-yen": ("yen", "yenes", None, None),
        "currency-indian-rupee": ("rupia", "rupias", "paisa", "paise"),
        "currency-south-korean-won": ("won", "wones", None, None),
    }
    if canonical_id == "currency-us-dollar" and language.casefold().replace("-", "_") == "es_mx":
        names[canonical_id] = ("dólar estadounidense", "dólares estadounidenses", "centavo", "centavos")
    singular, plural, minor_singular, minor_plural = names.get(
        canonical_id, (canonical_id, canonical_id, "centavo", "centavos")
    )
    major = singular if integer == 1 else plural
    gender = "f" if canonical_id == "currency-pound-sterling" else "m"
    major_raw = f"{'-' if negative else ''}{integer}"
    number = _number_text(major_raw, gender=gender, apocopate=True, language=language)
    if fraction is not None:
        minor_value = int(fraction)
        if minor_value and minor_singular is not None and minor_plural is not None:
            minor = minor_singular if minor_value == 1 else minor_plural
            minor_number = _number_text(
                str(minor_value), gender="m", apocopate=True, language=language
            )
            result = f"{number} {major} con {minor_number} {minor}"
        else:
            result = f"{number} {major}"
    else:
        result = f"{number} {major}"
    return result


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def iter_replacements(
    text: str,
    *,
    language: str = "es",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return Spanish structured and plain-number semantic candidates."""
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []

    def add(start: int, end: int, value: str | None, rule: str) -> None:
        if value is not None and not _overlaps(start, end, protected):
            candidates.append(Replacement(start, end, value, "structured", "es", rule))

    for match in _DATE_DMY_NO_YEAR.finditer(text):
        day, month = int(match["day"]), int(match["month"])
        if _valid_date(day, month, 2000) and _date_like_context(text, match.start(), match.end(), day=day):
            day_text = "primero" if day == 1 else _spell(day, language)
            add(match.start(), match.end(), f"{day_text} de {_MONTHS[month - 1]}", "es.date")
    for pattern in (_DATE_DMY_SHORT, _DATE_DMY_HYPHEN):
        for match in pattern.finditer(text):
            year, _ = expand_year(match["year"])
            day, month = int(match["day"]), int(match["month"])
            if 1 <= month <= 12 and _valid_date(day, month, year):
                add(match.start(), match.end(), _date_text(day, month, year, language), "es.date")
    month_aliases = {name[:3]: index for index, name in enumerate(_MONTHS, 1)}
    for match in (*_TEXT_DATE_DE.finditer(text), *_TEXT_DATE.finditer(text)):
        month_key = match["month"].lower().rstrip(".")
        text_month: int | None = month_aliases.get(month_key[:3])
        if text_month is None:
            continue
        text_year: int | None = None
        if match["year"]:
            text_year, _ = expand_year(match["year"])
        day = int(match["day"])
        if text_year is None or _valid_date(day, text_month, text_year):
            value = _date_text(day, text_month, text_year or 2000, language)
            if text_year is None:
                value = f"{_spell(day, language)} de {_MONTHS[text_month - 1]}"
            add(match.start(), match.end(), value, "es.date")

    for pattern in (_DATE_DMY, _DATE_ISO):
        for match in pattern.finditer(text):
            day, month, year = int(match["day"]), int(match["month"]), int(match["year"])
            if 1 <= month <= 12 and _valid_date(day, month, year):
                add(match.start(), match.end(), _date_text(day, month, year, language), "es.date")

    for pattern in (_TIME_HOURS, _TIME_COLON):
        for match in pattern.finditer(text):
            add(
                match.start(),
                match.end(),
                _time_text(int(match["hour"]), int(match["minute"]), match["period"], language)
                if "period" in match.groupdict()
                else _time_text(int(match["hour"]), int(match["minute"]), None, language),
                "es.time",
            )

    for match in _ORDINAL_SYMBOL.finditer(text):
        value = _ordinal_text(int(match["number"]), match["suffix"], language)
        add(match.start(), match.end(), value, "es.ordinal")

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
            "es.currency" if match.category == "currency" else "es.quantity",
        )

    return tuple(candidates)


__all__ = ["NUMBER_POLICY", "QUANTITY_GRAMMAR", "QuantityGrammar", "iter_replacements"]
