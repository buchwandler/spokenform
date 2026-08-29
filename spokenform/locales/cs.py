"""Czech semantic grammar owned by spokenform.

The Czech abbr2words inventory supplies recognition and canonical identities;
this module supplies the language-specific number, case, and agreement rules.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from abbr2words import UnitMatch, iter_unit_matches

from ..config import NumberPolicy
from ..dates import _valid_date
from ..language import resolve_abbr2words_language
from ..mapping import Replacement
from ..number_words import number_words
from ..numeric_lexeme import has_excess_fractional_precision

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN


@dataclass(frozen=True, slots=True)
class QuantityGrammar:
    """Czech noun forms for one, two-to-four, many, and decimal quantities."""

    canonical_id: str
    gender: str
    one: str
    few: str
    many: str
    decimal: str | None = None


def _grammar(canonical_id: str, gender: str, one: str, few: str, many: str) -> QuantityGrammar:
    return QuantityGrammar(canonical_id, gender, one, few, many, many)


QUANTITY_GRAMMAR: dict[str, QuantityGrammar] = {
    "duration-second": _grammar("duration-second", "f", "sekunda", "sekundy", "sekund"),
    "duration-minute": _grammar("duration-minute", "f", "minuta", "minuty", "minut"),
    "duration-hour": _grammar("duration-hour", "f", "hodina", "hodiny", "hodin"),
    "duration-day": _grammar("duration-day", "m", "den", "dny", "dnů"),
    "length-millimeter": _grammar("length-millimeter", "m", "milimetr", "milimetry", "milimetrů"),
    "length-centimeter": _grammar(
        "length-centimeter", "m", "centimetr", "centimetry", "centimetrů"
    ),
    "length-meter": _grammar("length-meter", "m", "metr", "metry", "metrů"),
    "length-kilometer": _grammar("length-kilometer", "m", "kilometr", "kilometry", "kilometrů"),
    "volume-milliliter": _grammar("volume-milliliter", "m", "mililitr", "mililitry", "mililitrů"),
    "volume-liter": _grammar("volume-liter", "m", "litr", "litry", "litrů"),
    "mass-microgram": _grammar("mass-microgram", "m", "mikrogram", "mikrogramy", "mikrogramů"),
    "mass-milligram": _grammar("mass-milligram", "m", "miligram", "miligramy", "miligramů"),
    "mass-gram": _grammar("mass-gram", "m", "gram", "gramy", "gramů"),
    "mass-kilogram": _grammar("mass-kilogram", "m", "kilogram", "kilogramy", "kilogramů"),
    "mass-tonne": _grammar("mass-tonne", "f", "tuna", "tuny", "tun"),
    "temperature-kelvin": _grammar("temperature-kelvin", "m", "kelvin", "kelviny", "kelvinů"),
    "speed-meter-per-second": _grammar(
        "speed-meter-per-second", "m", "metr za sekundu", "metry za sekundu", "metrů za sekundu"
    ),
    "speed-kilometer-per-hour": _grammar(
        "speed-kilometer-per-hour",
        "m",
        "kilometr za hodinu",
        "kilometry za hodinu",
        "kilometrů za hodinu",
    ),
    "area-square-millimeter": _grammar(
        "area-square-millimeter",
        "m",
        "milimetr čtvereční",
        "milimetry čtvereční",
        "milimetrů čtverečních",
    ),
    "area-square-centimeter": _grammar(
        "area-square-centimeter",
        "m",
        "centimetr čtvereční",
        "centimetry čtvereční",
        "centimetrů čtverečních",
    ),
    "area-square-meter": _grammar(
        "area-square-meter", "m", "metr čtvereční", "metry čtvereční", "metrů čtverečních"
    ),
    "area-square-kilometer": _grammar(
        "area-square-kilometer",
        "m",
        "kilometr čtvereční",
        "kilometry čtvereční",
        "kilometrů čtverečních",
    ),
    "area-hectare": _grammar("area-hectare", "m", "hektar", "hektary", "hektarů"),
    "volume-cubic-millimeter": _grammar(
        "volume-cubic-millimeter",
        "m",
        "milimetr krychlový",
        "milimetry krychlové",
        "milimetrů krychlových",
    ),
    "volume-cubic-centimeter": _grammar(
        "volume-cubic-centimeter",
        "m",
        "centimetr krychlový",
        "centimetry krychlové",
        "centimetrů krychlových",
    ),
    "volume-cubic-meter": _grammar(
        "volume-cubic-meter", "m", "metr krychlový", "metry krychlové", "metrů krychlových"
    ),
}

_DATE_DMY = re.compile(
    r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])[./](?P<month>0?[1-9]|1[0-2])[./](?P<year>\d{4})(?!\d)"
)
_DATE_ISO = re.compile(
    r"(?<![\w.])(?P<year>\d{4})-(?P<month>0?[1-9]|1[0-2])-(?P<day>0?[1-9]|[12]\d|3[01])(?!\d)"
)
_MONTHS = (
    "ledna",
    "února",
    "března",
    "dubna",
    "května",
    "června",
    "července",
    "srpna",
    "září",
    "října",
    "listopadu",
    "prosince",
)
_DAY_GENITIVE = (
    "prvního",
    "druhého",
    "třetího",
    "čtvrtého",
    "pátého",
    "šestého",
    "sedmého",
    "osmého",
    "devátého",
    "desátého",
    "jedenáctého",
    "dvanáctého",
    "třináctého",
    "čtrnáctého",
    "patnáctého",
    "šestnáctého",
    "sedmnáctého",
    "osmnáctého",
    "devatenáctého",
    "dvacátého",
    "dvacátého prvního",
    "dvacátého druhého",
    "dvacátého třetího",
    "dvacátého čtvrtého",
    "dvacátého pátého",
    "dvacátého šestého",
    "dvacátého sedmého",
    "dvacátého osmého",
    "dvacátého devátého",
    "třicátého",
    "třicátého prvního",
)


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
        raise ValueError(f"Cannot parse Czech number {raw!r}") from exc


def _spell(value: int, language: str = "cs") -> str:
    return str(number_words(value, lang=language))


def _gendered_cardinal(value: int, gender: str | None, language: str = "cs") -> str:
    result = _spell(value, language)
    if gender is None:
        return result
    # Compound counted phrases commonly use genitive plural from five onward,
    # including 21--24, so gender agreement is limited to small cardinals.
    if value > 4:
        return result
    last = {
        "m": {"jedna": "jeden", "dva": "dva"},
        "f": {"jedna": "jedna", "dva": "dvě"},
        "n": {"jedna": "jedno", "dva": "dvě"},
    }.get(gender, {})
    for source, target in last.items():
        if result == source or result.endswith(f" {source}"):
            return f"{result[: -len(source)]}{target}"
    return result


def number_text(raw: str, *, gender: str | None = None, language: str = "cs") -> str:
    """Return reviewed Czech cardinal wording, preserving comma precision."""
    negative, integer, fraction = _parts(raw)
    if fraction is None:
        result = _gendered_cardinal(integer, gender, language)
    else:
        result = f"{_spell(integer, language)} celá " + " ".join(
            _spell(int(digit), language) for digit in fraction
        )
    return f"mínus {result}" if negative else result


def date_text(day: int, month: int, year: int, language: str = "cs") -> str:
    """Return the Czech genitive day/month form used in spoken dates."""
    return f"{_DAY_GENITIVE[day - 1]} {_MONTHS[month - 1]} {_spell(year, language)}"


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \t\n\"'”’»)]}")


def _quantity_noun(grammar: QuantityGrammar, value: Decimal, fraction: str | None) -> str:
    if fraction is not None and grammar.decimal is not None:
        return grammar.decimal
    absolute = abs(int(value))
    if absolute == 1:
        return grammar.one
    if absolute in {2, 3, 4}:
        return grammar.few
    return grammar.many


_CURRENCY_GRAMMAR = {
    "currency-czech-koruna": (("koruna", "koruny", "korun", "f"), ("haléř", "haléře", "haléřů")),
    "currency-euro": (("euro", "eura", "eur", "n"), ("cent", "centy", "centů")),
    "currency-us-dollar": (("dolar", "dolary", "dolarů", "m"), ("cent", "centy", "centů")),
    "currency-pound-sterling": (
        ("libra šterlinků", "libry šterlinků", "liber šterlinků", "f"),
        ("pence", "pence", "pencí"),
    ),
}


def _currency_text(raw: str, canonical_id: str, language: str = "cs") -> str | None:
    grammar = _CURRENCY_GRAMMAR.get(canonical_id)
    if grammar is None:
        return None
    negative, integer, fraction = _parts(raw)
    major_one, major_few, major_many, gender = grammar[0]
    major_noun = major_one if integer == 1 else major_few if integer in {2, 3, 4} else major_many
    major_raw = f"{'-' if negative else ''}{integer}"
    result = f"{number_text(major_raw, gender=gender, language=language)} {major_noun}"
    if has_excess_fractional_precision(fraction):
        return f"{number_text(raw, gender=gender, language=language)} {major_noun}"
    if fraction is not None:
        minor_value = int((fraction + "00")[:2])
        if minor_value:
            minor_one, minor_few, minor_many = grammar[1]
            minor_noun = (
                minor_one
                if minor_value == 1
                else minor_few
                if minor_value in {2, 3, 4}
                else minor_many
            )
            result += f" a {_spell(minor_value, language)} {minor_noun}"
    return result


def _quantity_text(match: UnitMatch, text: str, language: str = "cs") -> str | None:
    canonical_id = match.canonical_id or ""
    if match.category == "currency":
        return _currency_text(match.value, canonical_id, language)
    if canonical_id in {"temperature-celsius", "temperature-fahrenheit"}:
        unit = "Celsia" if canonical_id.endswith("celsius") else "Fahrenheita"
        value = _decimal(match.value)
        absolute = abs(int(value))
        if "," in match.value or absolute not in {1, 2, 3, 4}:
            noun = f"stupňů {unit}"
        elif absolute == 1:
            noun = f"stupeň {unit}"
        else:
            noun = f"stupně {unit}"
        return f"{number_text(match.value, gender='m', language=language)} {noun}"
    grammar = QUANTITY_GRAMMAR.get(canonical_id)
    if grammar is None:
        return None
    negative, integer, fraction = _parts(match.value)
    value = Decimal(f"{'-' if negative else ''}{integer}" + (f".{fraction}" if fraction else ""))
    noun = _quantity_noun(grammar, value, fraction)
    result = number_text(match.value, gender=grammar.gender, language=language)
    if match.symbol.endswith(".") and _terminal_dot(text, match.end):
        noun += "."
    return f"{result} {noun}"


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def iter_replacements(
    text: str,
    *,
    language: str = "cs",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return Czech structured candidates before shared conflict resolution."""
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []

    def add(start: int, end: int, value: str | None, rule: str) -> None:
        if value is not None and not _overlaps(start, end, protected):
            candidates.append(Replacement(start, end, value, "structured", "cs", rule))

    for pattern in (_DATE_DMY, _DATE_ISO):
        for match in pattern.finditer(text):
            day, month, year = int(match["day"]), int(match["month"]), int(match["year"])
            if _valid_date(day, month, year):
                add(match.start(), match.end(), date_text(day, month, year, language), "cs.date")

    for unit_match in iter_unit_matches(
        text, resolve_abbr2words_language(language), protected_spans=protected
    ):
        try:
            replacement = _quantity_text(unit_match, text, language)
        except (TypeError, ValueError):
            replacement = None
        add(
            unit_match.start,
            unit_match.end,
            replacement,
            "cs.currency" if unit_match.category == "currency" else "cs.quantity",
        )
    return tuple(candidates)


__all__ = [
    "NUMBER_POLICY",
    "QUANTITY_GRAMMAR",
    "QuantityGrammar",
    "date_text",
    "iter_replacements",
    "number_text",
]
