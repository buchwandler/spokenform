"""Russian semantic quantity grammar owned by Spokenform.

``abbr2words`` recognizes Russian unit symbols and provides canonical IDs. This
module deliberately keeps the reviewed noun forms explicit instead of deriving
Russian morphology from suffixes.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from abbr2words import UnitMatch, iter_unit_matches

from ..config import NumberPolicy
from ..language import resolve_abbr2words_language
from ..mapping import Replacement
from ..number_words import number_words
from ..numeric_lexeme import (
    NumericLexeme,
    fraction_digit_groups,
    numeric_speech_policy,
    parse_numeric_lexeme,
)

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN
QuantityCategory = Literal["one", "few", "many", "other"]


@dataclass(frozen=True, slots=True)
class QuantityGrammar:
    canonical_id: str
    gender: Literal["masculine", "feminine", "neuter"] | None
    one: str
    few: str
    many: str
    other: str


def _grammar(
    canonical_id: str,
    gender: Literal["masculine", "feminine", "neuter"] | None,
    one: str,
    few: str,
    many: str,
    other: str,
) -> QuantityGrammar:
    return QuantityGrammar(canonical_id, gender, one, few, many, other)


QUANTITY_GRAMMAR: dict[str, QuantityGrammar] = {
    "duration-second": _grammar(
        "duration-second", "feminine", "секунда", "секунды", "секунд", "секунды"
    ),
    "duration-minute": _grammar(
        "duration-minute", "feminine", "минута", "минуты", "минут", "минуты"
    ),
    "duration-hour": _grammar("duration-hour", "masculine", "час", "часа", "часов", "часа"),
    "duration-day": _grammar("duration-day", "masculine", "день", "дня", "дней", "дня"),
    "duration-year": _grammar("duration-year", "masculine", "год", "года", "лет", "года"),
    "length-millimeter": _grammar(
        "length-millimeter", "masculine", "миллиметр", "миллиметра", "миллиметров", "миллиметра"
    ),
    "length-centimeter": _grammar(
        "length-centimeter", "masculine", "сантиметр", "сантиметра", "сантиметров", "сантиметра"
    ),
    "length-meter": _grammar("length-meter", "masculine", "метр", "метра", "метров", "метра"),
    "length-kilometer": _grammar(
        "length-kilometer", "masculine", "километр", "километра", "километров", "километра"
    ),
    "length-nanometer": _grammar(
        "length-nanometer", "masculine", "нанометр", "нанометра", "нанометров", "нанометра"
    ),
    "volume-milliliter": _grammar(
        "volume-milliliter", "masculine", "миллилитр", "миллилитра", "миллилитров", "миллилитра"
    ),
    "volume-liter": _grammar("volume-liter", "masculine", "литр", "литра", "литров", "литра"),
    "mass-microgram": _grammar(
        "mass-microgram", "masculine", "микрограмм", "микрограмма", "микрограммов", "микрограмма"
    ),
    "mass-milligram": _grammar(
        "mass-milligram", "masculine", "миллиграмм", "миллиграмма", "миллиграммов", "миллиграмма"
    ),
    "mass-gram": _grammar("mass-gram", "masculine", "грамм", "грамма", "граммов", "грамма"),
    "mass-kilogram": _grammar(
        "mass-kilogram", "masculine", "килограмм", "килограмма", "килограммов", "килограмма"
    ),
    "mass-tonne": _grammar("mass-tonne", "feminine", "тонна", "тонны", "тонн", "тонны"),
    "temperature-kelvin": _grammar(
        "temperature-kelvin", "masculine", "кельвин", "кельвина", "кельвинов", "кельвина"
    ),
    "temperature-celsius": _grammar(
        "temperature-celsius",
        "masculine",
        "градус Цельсия",
        "градуса Цельсия",
        "градусов Цельсия",
        "градуса Цельсия",
    ),
    "temperature-fahrenheit": _grammar(
        "temperature-fahrenheit",
        "masculine",
        "градус Фаренгейта",
        "градуса Фаренгейта",
        "градусов Фаренгейта",
        "градуса Фаренгейта",
    ),
    "speed-meter-per-second": _grammar(
        "speed-meter-per-second",
        "masculine",
        "метр в секунду",
        "метра в секунду",
        "метров в секунду",
        "метра в секунду",
    ),
    "speed-kilometer-per-hour": _grammar(
        "speed-kilometer-per-hour",
        "masculine",
        "километр в час",
        "километра в час",
        "километров в час",
        "километра в час",
    ),
    "speed-mile-per-hour": _grammar(
        "speed-mile-per-hour", "feminine", "миля в час", "мили в час", "миль в час", "мили в час"
    ),
    "area-square-millimeter": _grammar(
        "area-square-millimeter",
        "masculine",
        "квадратный миллиметр",
        "квадратных миллиметра",
        "квадратных миллиметров",
        "квадратного миллиметра",
    ),
    "area-square-centimeter": _grammar(
        "area-square-centimeter",
        "masculine",
        "квадратный сантиметр",
        "квадратных сантиметра",
        "квадратных сантиметров",
        "квадратного сантиметра",
    ),
    "area-square-meter": _grammar(
        "area-square-meter",
        "masculine",
        "квадратный метр",
        "квадратных метра",
        "квадратных метров",
        "квадратного метра",
    ),
    "area-square-kilometer": _grammar(
        "area-square-kilometer",
        "masculine",
        "квадратный километр",
        "квадратных километра",
        "квадратных километров",
        "квадратного километра",
    ),
    "area-hectare": _grammar(
        "area-hectare", "masculine", "гектар", "гектара", "гектаров", "гектара"
    ),
    "volume-cubic-millimeter": _grammar(
        "volume-cubic-millimeter",
        "masculine",
        "кубический миллиметр",
        "кубических миллиметра",
        "кубических миллиметров",
        "кубического миллиметра",
    ),
    "volume-cubic-centimeter": _grammar(
        "volume-cubic-centimeter",
        "masculine",
        "кубический сантиметр",
        "кубических сантиметра",
        "кубических сантиметров",
        "кубического сантиметра",
    ),
    "volume-cubic-meter": _grammar(
        "volume-cubic-meter",
        "masculine",
        "кубический метр",
        "кубических метра",
        "кубических метров",
        "кубического метра",
    ),
    "flow-cubic-meter-per-second": _grammar(
        "flow-cubic-meter-per-second",
        "masculine",
        "кубический метр в секунду",
        "кубических метра в секунду",
        "кубических метров в секунду",
        "кубического метра в секунду",
    ),
    "fuel-consumption-liter-per-100-kilometer": _grammar(
        "fuel-consumption-liter-per-100-kilometer",
        "masculine",
        "литр на 100 километров",
        "литра на 100 километров",
        "литров на 100 километров",
        "литра на 100 километров",
    ),
    "pressure-pascal": _grammar(
        "pressure-pascal", "masculine", "паскаль", "паскаля", "паскалей", "паскаля"
    ),
    "pressure-kilopascal": _grammar(
        "pressure-kilopascal",
        "masculine",
        "килопаскаль",
        "килопаскаля",
        "килопаскалей",
        "килопаскаля",
    ),
    "pressure-atmosphere": _grammar(
        "pressure-atmosphere", "feminine", "атмосфера", "атмосферы", "атмосфер", "атмосферы"
    ),
    "data-byte": _grammar("data-byte", "masculine", "байт", "байта", "байт", "байта"),
    "data-kilobyte": _grammar(
        "data-kilobyte", "masculine", "килобайт", "килобайта", "килобайт", "килобайта"
    ),
    "data-megabyte": _grammar(
        "data-megabyte", "masculine", "мегабайт", "мегабайта", "мегабайт", "мегабайта"
    ),
    "data-gigabyte": _grammar(
        "data-gigabyte", "masculine", "гигабайт", "гигабайта", "гигабайт", "гигабайта"
    ),
    "power-watt": _grammar("power-watt", "masculine", "ватт", "ватта", "ватт", "ватта"),
    "power-kilowatt": _grammar(
        "power-kilowatt", "masculine", "киловатт", "киловатта", "киловатт", "киловатта"
    ),
    "energy-watt-hour": _grammar(
        "energy-watt-hour", "masculine", "ватт-час", "ватт-часа", "ватт-часов", "ватт-часа"
    ),
    "energy-kilowatt-hour": _grammar(
        "energy-kilowatt-hour",
        "masculine",
        "киловатт-час",
        "киловатт-часа",
        "киловатт-часов",
        "киловатт-часа",
    ),
    "frequency-hertz": _grammar("frequency-hertz", "masculine", "герц", "герца", "герц", "герца"),
    "frequency-kilohertz": _grammar(
        "frequency-kilohertz", "masculine", "килогерц", "килогерца", "килогерц", "килогерца"
    ),
    "frequency-megahertz": _grammar(
        "frequency-megahertz", "masculine", "мегагерц", "мегагерца", "мегагерц", "мегагерца"
    ),
    "frequency-gigahertz": _grammar(
        "frequency-gigahertz", "masculine", "гигагерц", "гигагерца", "гигагерц", "гигагерца"
    ),
    "current-ampere": _grammar("current-ampere", "masculine", "ампер", "ампера", "ампер", "ампера"),
    "current-milliampere": _grammar(
        "current-milliampere", "masculine", "миллиампер", "миллиампера", "миллиампер", "миллиампера"
    ),
    "charge-milliampere-hour": _grammar(
        "charge-milliampere-hour",
        "masculine",
        "миллиампер-час",
        "миллиампер-часа",
        "миллиампер-часов",
        "миллиампер-часа",
    ),
    "voltage-volt": _grammar("voltage-volt", "masculine", "вольт", "вольта", "вольт", "вольта"),
    "luminous-flux-lumen": _grammar(
        "luminous-flux-lumen", "masculine", "люмен", "люмена", "люмен", "люмена"
    ),
    "force-newton": _grammar("force-newton", "masculine", "ньютон", "ньютона", "ньютон", "ньютона"),
    "energy-joule": _grammar("energy-joule", "masculine", "джоуль", "джоуля", "джоулей", "джоуля"),
    "pressure-millimeter-mercury": _grammar(
        "pressure-millimeter-mercury",
        "masculine",
        "миллиметр ртутного столба",
        "миллиметра ртутного столба",
        "миллиметров ртутного столба",
        "миллиметра ртутного столба",
    ),
    "amount-mole": _grammar("amount-mole", "masculine", "моль", "моля", "молей", "моля"),
}


_FINAL_TOKEN = re.compile(r"(?<!\w)(один|два)$")


def quantity_category(lexeme: NumericLexeme) -> QuantityCategory:
    """Return the CLDR Russian cardinal category for a numeric lexeme."""
    if lexeme.fraction_digits is not None:
        return "other"
    value = int(lexeme.integer_digits)
    mod10 = value % 10
    mod100 = value % 100
    if mod10 == 1 and mod100 != 11:
        return "one"
    if 2 <= mod10 <= 4 and not 12 <= mod100 <= 14:
        return "few"
    return "many"


def _agree_integer_number(text: str, *, integer: int, gender: str | None) -> str:
    if gender != "feminine":
        return text
    mod100 = integer % 100
    if 11 <= mod100 <= 14:
        return text
    replacement = {1: "одна", 2: "две"}.get(integer % 10)
    if replacement is None:
        return text
    return _FINAL_TOKEN.sub(replacement, text)


def number_text(lexeme: NumericLexeme, *, language: str, gender: str | None = None) -> str:
    """Render a Russian numeric lexeme while preserving visible precision."""
    integer = int(lexeme.integer_digits)
    result = str(number_words(integer, lang=language))
    if gender and lexeme.fraction_digits is None:
        result = _agree_integer_number(result, integer=integer, gender=gender)
    elif lexeme.fraction_digits is not None:
        policy = numeric_speech_policy(language)
        groups = fraction_digit_groups(lexeme.fraction_digits, language, mode="digitwise")
        rendered = " ".join(str(number_words(int(group), lang=language)) for group in groups)
        result = f"{result} {policy.decimal_word} {rendered}"
    if lexeme.negative:
        result = f"минус {result}"
    elif lexeme.raw.startswith("+"):
        result = f"плюс {result}"
    return result


def _quantity_text(match: UnitMatch, *, language: str) -> str | None:
    if match.category == "currency":
        return None
    grammar = QUANTITY_GRAMMAR.get(match.canonical_id or "")
    if grammar is None:
        return None
    lexeme = parse_numeric_lexeme(match.value, language, context="quantity")
    if lexeme is None:
        return None
    category = quantity_category(lexeme)
    noun = getattr(grammar, category)
    return f"{number_text(lexeme, language=language, gender=grammar.gender)} {noun}"


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def iter_replacements(
    text: str,
    *,
    language: str = "ru",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return reviewed Russian quantity replacements only."""
    protected = tuple(protected_ranges)
    dependency_language = resolve_abbr2words_language(language)
    candidates: list[Replacement] = []
    for match in iter_unit_matches(text, dependency_language, protected_spans=protected):
        if _overlaps(match.start, match.end, protected):
            continue
        try:
            replacement = _quantity_text(match, language=language)
        except (TypeError, ValueError):
            replacement = None
        if replacement is None:
            continue
        candidates.append(
            Replacement(match.start, match.end, replacement, "structured", "ru", "ru.quantity")
        )
    return tuple(candidates)


__all__ = [
    "NUMBER_POLICY",
    "QUANTITY_GRAMMAR",
    "QuantityCategory",
    "QuantityGrammar",
    "iter_replacements",
    "number_text",
    "quantity_category",
]
