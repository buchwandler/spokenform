"""Portuguese semantic grammar owned by spokenform.

``abbr2words`` recognizes Portuguese symbols and returns canonical identities.
This module owns their written-to-spoken realization, including Brazilian and
European Portuguese number wording and grammatical agreement.
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
    gender: str
    singular: str
    plural: str


QUANTITY_GRAMMAR: dict[str, QuantityGrammar] = {
    "duration-second": QuantityGrammar("duration-second", "m", "segundo", "segundos"),
    "duration-minute": QuantityGrammar("duration-minute", "m", "minuto", "minutos"),
    "duration-hour": QuantityGrammar("duration-hour", "f", "hora", "horas"),
    "duration-day": QuantityGrammar("duration-day", "m", "dia", "dias"),
    "length-millimeter": QuantityGrammar("length-millimeter", "m", "milímetro", "milímetros"),
    "length-centimeter": QuantityGrammar("length-centimeter", "m", "centímetro", "centímetros"),
    "length-meter": QuantityGrammar("length-meter", "m", "metro", "metros"),
    "length-kilometer": QuantityGrammar("length-kilometer", "m", "quilômetro", "quilômetros"),
    "volume-milliliter": QuantityGrammar("volume-milliliter", "m", "mililitro", "mililitros"),
    "volume-liter": QuantityGrammar("volume-liter", "m", "litro", "litros"),
    "mass-microgram": QuantityGrammar("mass-microgram", "m", "micrograma", "microgramas"),
    "mass-milligram": QuantityGrammar("mass-milligram", "m", "miligrama", "miligramas"),
    "mass-gram": QuantityGrammar("mass-gram", "m", "grama", "gramas"),
    "mass-kilogram": QuantityGrammar("mass-kilogram", "m", "quilograma", "quilogramas"),
    "mass-tonne": QuantityGrammar("mass-tonne", "f", "tonelada", "toneladas"),
    "temperature-kelvin": QuantityGrammar("temperature-kelvin", "m", "kelvin", "kelvin"),
    "area-square-millimeter": QuantityGrammar(
        "area-square-millimeter", "m", "milímetro quadrado", "milímetros quadrados"
    ),
    "area-square-centimeter": QuantityGrammar(
        "area-square-centimeter", "m", "centímetro quadrado", "centímetros quadrados"
    ),
    "area-square-meter": QuantityGrammar(
        "area-square-meter", "m", "metro quadrado", "metros quadrados"
    ),
    "area-square-kilometer": QuantityGrammar(
        "area-square-kilometer", "m", "quilômetro quadrado", "quilômetros quadrados"
    ),
    "area-hectare": QuantityGrammar("area-hectare", "m", "hectare", "hectares"),
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
        "speed-kilometer-per-hour", "m", "quilômetro por hora", "quilômetros por hora"
    ),
}

_DATE_DMY = re.compile(r"(?<![\w.])(?P<day>\d{1,2})[./](?P<month>\d{1,2})[./](?P<year>\d{4})(?!\d)")
_DATE_ISO = re.compile(r"(?<![\w.])(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})(?!\d)")
_MONTHS = (
    "janeiro",
    "fevereiro",
    "março",
    "abril",
    "maio",
    "junho",
    "julho",
    "agosto",
    "setembro",
    "outubro",
    "novembro",
    "dezembro",
)


def _number_language(language: str) -> str:
    normalized = language.strip().lower().replace("_", "-")
    return "pt_BR" if normalized in {"pt", "pt-br"} else "pt"


def _parts(raw: str) -> tuple[bool, int, str | None]:
    value = raw.replace("−", "-").replace("\u00a0", " ").replace("\u202f", " ")
    negative, unsigned = value.startswith("-"), value.lstrip("+-")
    if unsigned.startswith(","):
        integer, fraction = "0", unsigned[1:]
    elif "," in unsigned:
        integer, fraction = unsigned.split(",", 1)
    else:
        integer, fraction = unsigned, None
    integer = re.sub(r"[.\s]", "", integer) or "0"
    return negative, int(integer), fraction


def _decimal(raw: str) -> Decimal:
    negative, integer, fraction = _parts(raw)
    normalized = f"{'-' if negative else ''}{integer}"
    if fraction is not None:
        normalized += f".{fraction}"
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Cannot parse Portuguese number {raw!r}") from exc


def _spell(value: int, language: str) -> str:
    return str(num2words(value, lang=_number_language(language)))


def _feminize_integer(text: str) -> str:
    """Apply Portuguese cardinal agreement before a feminine noun."""
    text = re.sub(
        r"\b(duzent|trezent|quatrocent|quinhent|seiscent|setecent|oitocent|novecent)os\b",
        r"\1as",
        text,
    )
    if re.search(r"\bdois$", text):
        return f"{text[:-4]}duas"
    if re.search(r"\bum$", text):
        return f"{text[:-2]}uma"
    return text


def _number_text(raw: str, *, language: str, gender: str | None = None) -> str:
    negative, integer, fraction = _parts(raw)
    if fraction is None:
        result = _spell(integer, language)
        if gender == "f":
            result = _feminize_integer(result)
    else:
        result = f"{_spell(integer, language)} vírgula " + " ".join(
            _spell(int(digit), language) for digit in fraction
        )
    return f"menos {result}" if negative else result


def _valid_date(day: int, month: int, year: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _date_text(day: int, month: int, year: int, *, language: str) -> str:
    return f"{_spell(day, language)} de {_MONTHS[month - 1]} de {_spell(year, language)}"


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \t\n\"'”’»)]}")


def _currency_text(raw: str, canonical_id: str, *, language: str) -> str:
    negative, integer, fraction = _parts(raw)
    european = _number_language(language) == "pt"
    minor_singular, minor_plural = ("cêntimo", "cêntimos") if european else ("centavo", "centavos")
    names = {
        "currency-euro": ("euro", "euros", "m"),
        "currency-us-dollar": ("dólar", "dólares", "m"),
        "currency-pound-sterling": ("libra esterlina", "libras esterlinas", "f"),
        "currency-brazilian-real": ("real", "reais", "m"),
    }
    singular, plural, gender = names.get(canonical_id, (canonical_id, canonical_id, "m"))
    major = singular if integer == 1 else plural
    major_raw = f"{'-' if negative else ''}{integer}"
    result = f"{_number_text(major_raw, language=language, gender=gender)} {major}"
    if fraction is not None:
        minor_value = int((fraction + "00")[:2])
        if minor_value:
            minor = minor_singular if minor_value == 1 else minor_plural
            result += f" e {_number_text(str(minor_value), language=language)} {minor}"
    return result


def _quantity_text(match: UnitMatch, text: str, *, language: str) -> str | None:
    canonical_id = match.canonical_id or ""
    if canonical_id.startswith("currency-"):
        return _currency_text(match.value, canonical_id, language=language)
    if canonical_id in {"temperature-celsius", "temperature-fahrenheit"}:
        unit = "Celsius" if canonical_id.endswith("celsius") else "Fahrenheit"
        value = _decimal(match.value)
        noun = f"grau {unit}" if abs(value) == 1 else f"graus {unit}"
        return f"{_number_text(match.value, language=language, gender='m')} {noun}"
    grammar = QUANTITY_GRAMMAR.get(canonical_id)
    if grammar is None:
        return None
    value = _decimal(match.value)
    noun = grammar.singular if abs(value) == 1 else grammar.plural
    result = _number_text(match.value, language=language, gender=grammar.gender)
    if match.symbol.endswith(".") and _terminal_dot(text, match.end):
        noun += "."
    return f"{result} {noun}"


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def iter_replacements(
    text: str,
    *,
    language: str = "pt",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return Portuguese structured candidates before shared conflict resolution."""
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []

    def add(start: int, end: int, value: str | None, rule: str) -> None:
        if value is not None and not _overlaps(start, end, protected):
            candidates.append(Replacement(start, end, value, "structured", "pt", rule))

    for pattern in (_DATE_DMY, _DATE_ISO):
        for match in pattern.finditer(text):
            day, month, year = int(match["day"]), int(match["month"]), int(match["year"])
            if 1 <= month <= 12 and _valid_date(day, month, year):
                add(
                    match.start(),
                    match.end(),
                    _date_text(day, month, year, language=language),
                    "pt.date",
                )

    for match in iter_unit_matches(text, "pt", protected_spans=protected):
        replacement = _quantity_text(match, text, language=language)
        add(
            match.start,
            match.end,
            replacement,
            "pt.currency" if match.category == "currency" else "pt.quantity",
        )
    return tuple(candidates)


__all__ = ["NUMBER_POLICY", "QUANTITY_GRAMMAR", "QuantityGrammar", "iter_replacements"]
