"""Swedish semantic grammar owned by spokenform.

``abbr2words`` recognizes Swedish abbreviations and units and supplies their
canonical identities. This module owns the Swedish number and noun grammar.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from abbr2words import UnitMatch, iter_unit_matches

from ..config import NumberPolicy
from ..language import resolve_abbr2words_language
from ..mapping import Replacement
from ..number_words import number_words
from ..numeric_lexeme import NumericLexeme, has_excess_fractional_precision, parse_numeric_lexeme

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN


@dataclass(frozen=True, slots=True)
class QuantityGrammar:
    """Swedish singular and plural forms for one canonical unit identity."""

    canonical_id: str
    gender: str | None
    singular: str
    plural: str


def _grammar(canonical_id: str, singular: str, plural: str, gender: str | None) -> QuantityGrammar:
    return QuantityGrammar(canonical_id, gender, singular, plural)


QUANTITY_GRAMMAR: dict[str, QuantityGrammar] = {
    "duration-second": _grammar("duration-second", "sekund", "sekunder", "common"),
    "duration-minute": _grammar("duration-minute", "minut", "minuter", "common"),
    "duration-hour": _grammar("duration-hour", "timme", "timmar", "common"),
    "length-millimeter": _grammar("length-millimeter", "millimeter", "millimeter", "common"),
    "length-centimeter": _grammar("length-centimeter", "centimeter", "centimeter", "common"),
    "length-meter": _grammar("length-meter", "meter", "meter", "common"),
    "length-kilometer": _grammar("length-kilometer", "kilometer", "kilometer", "common"),
    "volume-milliliter": _grammar("volume-milliliter", "milliliter", "milliliter", "common"),
    "volume-liter": _grammar("volume-liter", "liter", "liter", "common"),
    "mass-microgram": _grammar("mass-microgram", "mikrogram", "mikrogram", "neuter"),
    "mass-milligram": _grammar("mass-milligram", "milligram", "milligram", "neuter"),
    "mass-gram": _grammar("mass-gram", "gram", "gram", "neuter"),
    "mass-kilogram": _grammar("mass-kilogram", "kilogram", "kilogram", "neuter"),
    "mass-tonne": _grammar("mass-tonne", "ton", "ton", "neuter"),
    "temperature-kelvin": _grammar("temperature-kelvin", "kelvin", "kelvin", "neuter"),
    "temperature-celsius": _grammar(
        "temperature-celsius", "grad Celsius", "grader Celsius", "common"
    ),
    "temperature-fahrenheit": _grammar(
        "temperature-fahrenheit", "grad Fahrenheit", "grader Fahrenheit", "common"
    ),
    "area-square-meter": _grammar("area-square-meter", "kvadratmeter", "kvadratmeter", "common"),
    "volume-cubic-meter": _grammar("volume-cubic-meter", "kubikmeter", "kubikmeter", "common"),
    "speed-meter-per-second": _grammar(
        "speed-meter-per-second", "meter per sekund", "meter per sekund", "common"
    ),
    "speed-kilometer-per-hour": _grammar(
        "speed-kilometer-per-hour", "kilometer per timme", "kilometer per timme", "common"
    ),
    "energy-kilowatt-hour": _grammar(
        "energy-kilowatt-hour", "kilowattimme", "kilowattimmar", "common"
    ),
}


def _one_word(gender: str | None) -> str:
    if gender == "common":
        return "en"
    if gender == "neuter":
        return "ett"
    return "ett"


def _is_singular(lexeme: NumericLexeme) -> bool:
    return not lexeme.negative and lexeme.integer_digits == "1" and lexeme.fraction_digits is None


def _spell_integer(value: str, language: str) -> str:
    return str(number_words(int(value), lang=language))


def number_text(lexeme: NumericLexeme, *, language: str, gender: str | None = None) -> str:
    """Render a parsed Swedish numeric lexeme without losing source precision."""
    if lexeme.fraction_digits is None:
        result = (
            _one_word(gender)
            if _is_singular(lexeme)
            else _spell_integer(lexeme.integer_digits, language)
        )
    else:
        result = f"{_spell_integer(lexeme.integer_digits, language)} komma " + " ".join(
            _spell_integer(digit, language) for digit in lexeme.fraction_digits
        )
    return f"minus {result}" if lexeme.negative else result


def _currency_text(lexeme: NumericLexeme, *, language: str) -> str:
    major_noun = "krona" if _is_singular(lexeme) else "kronor"
    major = (
        _one_word("common")
        if _is_singular(lexeme)
        else _spell_integer(lexeme.integer_digits, language)
    )
    if lexeme.negative:
        major = f"minus {major}"
    result = f"{major} {major_noun}"
    fraction = lexeme.fraction_digits
    if has_excess_fractional_precision(fraction):
        return f"{number_text(lexeme, language=language)} {major_noun}"
    if fraction is not None:
        minor_value = int((fraction + "00")[:2])
        if minor_value:
            minor_noun = "öre"
            result += f" och {_spell_integer(str(minor_value), language)} {minor_noun}"
    return result


def _quantity_text(match: UnitMatch, *, language: str) -> str | None:
    canonical_id = match.canonical_id or ""
    context = "currency" if match.category == "currency" else "quantity"
    lexeme = parse_numeric_lexeme(match.value, language, context=context)
    if lexeme is None:
        return None
    if canonical_id == "currency-swedish-krona":
        return _currency_text(lexeme, language=language)
    grammar = QUANTITY_GRAMMAR.get(canonical_id)
    if grammar is None:
        return None
    noun = grammar.singular if _is_singular(lexeme) else grammar.plural
    return f"{number_text(lexeme, language=language, gender=grammar.gender)} {noun}"


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def iter_replacements(
    text: str,
    *,
    language: str = "sv",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return Swedish structured quantity and currency replacements."""
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []
    dependency_language = resolve_abbr2words_language(language)
    for match in iter_unit_matches(text, dependency_language, protected_spans=protected):
        if _overlaps(match.start, match.end, protected):
            continue
        try:
            replacement = _quantity_text(match, language=language)
        except (TypeError, ValueError):
            replacement = None
        if replacement is None:
            continue
        rule = "sv.currency" if match.category == "currency" else "sv.quantity"
        candidates.append(
            Replacement(match.start, match.end, replacement, "structured", "sv", rule)
        )
    return tuple(candidates)


__all__ = [
    "NUMBER_POLICY",
    "QUANTITY_GRAMMAR",
    "QuantityGrammar",
    "iter_replacements",
    "number_text",
]
