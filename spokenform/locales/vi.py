"""Vietnamese semantic grammar owned by spokenform.

``abbr2words`` recognizes Vietnamese abbreviations and reviewed units. This
module owns numeric realization and source-aligned structured replacements.
"""

from __future__ import annotations

from collections.abc import Iterable

from abbr2words import UnitMatch, iter_unit_matches

from ..config import NumberPolicy
from ..language import resolve_abbr2words_language
from ..mapping import Replacement
from ..number_words import number_words
from ..numeric_lexeme import NumericLexeme, parse_numeric_lexeme

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN


def _spell_integer(digits: str, language: str) -> str:
    return str(number_words(int(digits), lang=language))


def number_text(lexeme: NumericLexeme, *, language: str) -> str:
    """Render a Vietnamese numeric lexeme without losing source precision."""
    if lexeme.fraction_digits is None:
        result = _spell_integer(lexeme.integer_digits, language)
    else:
        result = f"{_spell_integer(lexeme.integer_digits, language)} phẩy " + " ".join(
            _spell_integer(digit, language) for digit in lexeme.fraction_digits
        )
    if lexeme.negative:
        return f"âm {result}"
    if lexeme.raw.startswith("+"):
        return f"dương {result}"
    return result


def _quantity_text(match: UnitMatch, *, language: str) -> str | None:
    context = "currency" if match.category == "currency" else "quantity"
    lexeme = parse_numeric_lexeme(match.value, language, context=context)
    if lexeme is None:
        return None

    canonical_id = match.canonical_id or ""
    if canonical_id == "currency-vietnamese-dong":
        if lexeme.fraction_digits is not None:
            return None
        return f"{number_text(lexeme, language=language)} {match.expansion}"
    if match.category == "currency" or not canonical_id or not match.expansion:
        return None
    return f"{number_text(lexeme, language=language)} {match.expansion}"


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def iter_replacements(
    text: str,
    *,
    language: str = "vi",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return Vietnamese structured quantity and currency replacements."""
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
        rule = "vi.currency" if match.category == "currency" else "vi.quantity"
        candidates.append(
            Replacement(match.start, match.end, replacement, "structured", "vi", rule)
        )
    return tuple(candidates)


__all__ = ["NUMBER_POLICY", "iter_replacements", "number_text"]
