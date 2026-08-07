"""Provider-neutral structured written-to-spoken normalization."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from abbr2words import UnitMatch, iter_unit_matches

from .locales.de import QUANTITY_GRAMMAR, QuantityGrammar
from .mapping import Replacement, resolve_replacements


@dataclass(frozen=True, slots=True)
class StageResult:
    """The exact replacements produced by one structured stage."""

    text: str
    replacements: tuple[Replacement, ...]
    reserved: tuple[tuple[int, int], ...] = ()


_NUMBER = r"[+\-−]?(?:(?:\d{1,3}(?:[.\s]\d{3})+|\d+)(?:[.,]\d+)?|[.,]\d+)"
_DE_DATE = re.compile(
    r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])[./](?P<month>0?[1-9]|1[0-2])[./](?P<year>\d{2,4})(?!\d)"
)
_DE_TEXT_DATE = re.compile(
    r"(?P<day>0?[1-9]|[12]\d|3[01])\.\s+(?P<month>Januar|Februar|März|Maerz|Mär|Apr|Mai|Juni|Juli|Aug|September|Sept|Oktober|November|Dezember|Dez)(?:\s+(?P<year>\d{2,4}))?",
    re.IGNORECASE,
)
_DE_TIME = re.compile(r"(?<!\d)(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)(?:\s+Uhr)?(?!\d)")
_CURRENCY_PREFIX = re.compile(
    rf"(?<![\w.])(?P<symbol>[^\W\d_€$£]+|[€$£])\s*(?P<number>{_NUMBER})(?![\w.])",
    re.IGNORECASE,
)
_CURRENCY_SUFFIX = re.compile(
    rf"(?<![\w.])(?P<number>{_NUMBER})\s*(?P<symbol>[^\W\d_€$£]+|[€$£])(?!\w)",
    re.IGNORECASE,
)
_DE_TEMPERATURE = re.compile(
    rf"(?<!\w)(?P<number>{_NUMBER})\s*°?\s*(?P<unit>°?C|°?F)(?!\w)", re.IGNORECASE
)
_DE_LABEL = re.compile(
    r"(?P<label>laufende\s+Nummer|Lfd\.\s*Nr\.|Nummer|Gleis|Kapitel|Absatz|Seite|S\.)\s+(?P<number>\d+)(?!\w)",
    re.IGNORECASE,
)
_DE_ORDINAL = re.compile(r"(?<![\w.])(?P<number>\d+)\.(?=\s+[A-Za-zÄÖÜäöüß])")

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
    normalized = raw.replace("−", "-").replace(" ", "").replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(raw) from exc


def _number_parts(raw: str) -> tuple[bool, int, str | None]:
    value = raw.replace("−", "-")
    negative = value.startswith("-")
    unsigned = value.lstrip("+-")
    if unsigned.startswith((".", ",")):
        integer_lexeme, fraction = "0", unsigned[1:]
    elif "," in unsigned:
        integer_lexeme, fraction = unsigned.split(",", 1)
    elif re.search(r"\.\d{1,2}$", unsigned) and unsigned.count(".") == 1:
        integer_lexeme, fraction = unsigned.split(".", 1)
    else:
        integer_lexeme, fraction = unsigned, None
    integer_lexeme = re.sub(r"[.\s]", "", integer_lexeme) or "0"
    return negative, int(integer_lexeme), fraction


def _number_text(raw: str, *, one: str | None = None) -> str:
    negative, integer, fraction = _number_parts(raw)
    if fraction is None:
        result = one if integer == 1 and one is not None else _spell(integer)
    else:
        fraction_text = " ".join(_spell(int(digit)) for digit in fraction)
        result = f"{_spell(integer)} Komma {fraction_text}"
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
    prefix = re.sub(r"\s+", " ", text[max(0, start - 48) : start].lower()).rstrip()
    for phrase in (
        "am",
        "im",
        "vom",
        "zum",
        "zur",
        "auf der",
        "an der",
        "in dem",
        "in den",
        "auf den",
    ):
        if prefix.endswith(phrase):
            return "en"
    for phrase in ("ans", "ins", "die", "auf die", "der"):
        if prefix.endswith(phrase):
            return "e"
    return "er"


def _valid_date(day: int, month: int, year: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _date_year(raw: str) -> int:
    value = int(raw)
    return value if len(raw) == 4 else 2000 + value


def _date_replacement(match: re.Match[str], text: str) -> str | None:
    day, month, year_raw = int(match["day"]), int(match["month"]), match["year"]
    year = _date_year(year_raw)
    if not _valid_date(day, month, year):
        return None
    ending = _context_ending(text, match.start()) if match.start() else "e"
    month_name = next(name for number, name in _MONTHS.values() if number == month)
    return f"{_ordinal(day, ending)} {month_name} {_year_text(year)}"


def _text_date_replacement(match: re.Match[str], text: str) -> str | None:
    month_number, month_name = _MONTHS[match["month"].lower()]
    year_raw = match["year"]
    year = _date_year(year_raw) if year_raw else None
    day = int(match["day"])
    if year is not None and not _valid_date(day, month_number, year):
        return None
    ending = _context_ending(text, match.start()) if text[: match.start()].strip() else "e"
    result = f"{_ordinal(day, ending)} {month_name}"
    return f"{result} {_year_text(year)}" if year is not None else result


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \t\n\"'”’»)]}")


def _grammar_for(canonical_id: str | None) -> QuantityGrammar | None:
    return QUANTITY_GRAMMAR.get(canonical_id or "")


def _quantity_replacement(match: UnitMatch, text: str) -> str | None:
    grammar = _grammar_for(match.canonical_id)
    if grammar is None:
        return None
    raw = match.value
    value = _parse_number(raw)
    noun = grammar.singular if value == 1 else grammar.plural
    number = _number_text(raw)
    if value == 1:
        number = "eine" if grammar.gender == "f" else "ein"
    if match.symbol.endswith(".") and _terminal_dot(text, match.end):
        noun += "."
    return f"{number} {noun}"


def _probe_currency(symbol: str) -> str | None:
    for match in iter_unit_matches(f"1 {symbol}", "de"):
        if match.category == "currency" and match.canonical_id:
            return match.canonical_id
    return None


def _currency_name(canonical_id: str) -> str:
    return {
        "currency-euro": "Euro",
        "currency-dollar": "Dollar",
        "currency-pound": "Pfund",
        "currency-swiss-franc": "Schweizer Franken",
    }.get(canonical_id, "")


def _currency_replacement(raw: str, canonical_id: str) -> str:
    negative, integer, fraction = _number_parts(raw)
    major = "ein" if integer == 1 else _spell(integer)
    result = f"{major} {_currency_name(canonical_id)}"
    if fraction:
        cents = int((fraction + "00")[:2])
        if cents:
            result += f" {_spell(cents)} Cent"
    return f"minus {result}" if negative else result


def _iter_currency_replacements(text: str) -> Iterable[Replacement]:
    for pattern in (_CURRENCY_PREFIX, _CURRENCY_SUFFIX):
        for match in pattern.finditer(text):
            canonical_id = _probe_currency(match["symbol"])
            if canonical_id is None:
                continue
            yield Replacement(
                match.start(),
                match.end(),
                _currency_replacement(match["number"], canonical_id),
                "structured",
                "de",
                "de.currency",
            )


def _magnitude_currency_replacement(match: UnitMatch, text: str) -> Replacement | None:
    if match.category != "magnitude":
        return None
    tail = re.match(r"\s+(?P<symbol>[^\W\d_€$£]+|[€$£])", text[match.end :])
    if tail is None:
        return None
    canonical_id = _probe_currency(tail["symbol"])
    if canonical_id is None:
        return None
    base = _quantity_replacement(match, text)
    if base is None:
        return None
    end = match.end + tail.end()
    return Replacement(
        match.start,
        end,
        f"{base} {_currency_name(canonical_id)}",
        "structured",
        "de",
        "de.magnitude-currency",
    )


def _temperature_replacement(match: re.Match[str]) -> str:
    unit = match["unit"].lower().replace("°", "")
    return f"{_number_text(match['number'])} Grad {'Celsius' if unit == 'c' else 'Fahrenheit'}"


def _label_replacement(match: re.Match[str]) -> str:
    source_label = match["label"]
    normalized = source_label.casefold().replace(" ", "")
    if normalized in {"s.", "seite"}:
        label = "Seite"
    elif normalized in {"lfd.nr.", "laufendenummer"}:
        label = "laufende Nummer"
    else:
        label = source_label
    return f"{label} {_spell(int(match['number']))}"


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


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

    def add(start: int, end: int, value: str | None, rule: str) -> None:
        if value is not None and not _overlaps(start, end, protected):
            candidates.append(Replacement(start, end, value, "structured", "de", rule))

    for match in _DE_DATE.finditer(text):
        add(match.start(), match.end(), _date_replacement(match, text), "de.date")
    for match in _DE_TEXT_DATE.finditer(text):
        add(match.start(), match.end(), _text_date_replacement(match, text), "de.text-date")
    for match in _DE_TIME.finditer(text):
        hour, minute = int(match["hour"]), int(match["minute"])
        hour_text = "ein" if hour == 1 else _spell(hour)
        value = f"{hour_text} Uhr" if minute == 0 else f"{hour_text} Uhr {_spell(minute)}"
        add(match.start(), match.end(), value, "de.time")
    for currency_candidate in _iter_currency_replacements(text):
        if not _overlaps(currency_candidate.start, currency_candidate.end, protected):
            candidates.append(currency_candidate)
    for match in _DE_TEMPERATURE.finditer(text):
        add(match.start(), match.end(), _temperature_replacement(match), "de.temperature")
    for match in iter_unit_matches(text, "de", protected_spans=protected):
        if match.category == "currency":
            continue
        if match.start and text[match.start - 1] in ".,":
            # abbr2words intentionally accepts a suffix quantity after a
            # separator; here that would be a partial match inside a larger
            # decimal/grouped number, so keep the complete source literal.
            continue
        combined = _magnitude_currency_replacement(match, text)
        if combined is not None:
            if not _overlaps(combined.start, combined.end, protected):
                candidates.append(combined)
            continue
        add(match.start, match.end, _quantity_replacement(match, text), "de.quantity")
    for match in _DE_LABEL.finditer(text):
        add(match.start(), match.end(), _label_replacement(match), "de.label")
    for match in _DE_ORDINAL.finditer(text):
        add(
            match.start(),
            match.end(),
            _ordinal(int(match["number"]), _context_ending(text, match.start())),
            "de.ordinal",
        )
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
