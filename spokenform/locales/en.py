"""English semantic grammar owned by spokenform.

Symbols and unit identities are recognized by :mod:`abbr2words`.  This module
only realizes the canonical identities and reviewed structured forms that are
safe to hand to a downstream English G2P.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from abbr2words import UnitMatch, iter_unit_matches
from num2words import num2words

from ..config import NumberPolicy
from ..dates import DateCandidate, expand_year, render_english_year
from ..language import resolve_abbr2words_language, resolve_num2words_language
from ..mapping import Replacement
from ..numeric_lexeme import fraction_digit_groups, numeric_speech_policy, parse_numeric_lexeme

NUMBER_POLICY = NumberPolicy.STRUCTURED_AND_PLAIN


@dataclass(frozen=True, slots=True)
class QuantityGrammar:
    """English singular and plural speech nouns for one canonical unit."""

    canonical_id: str
    singular: str
    plural: str


QUANTITY_GRAMMAR: dict[str, QuantityGrammar] = {
    "length-millimeter": QuantityGrammar("length-millimeter", "millimeter", "millimeters"),
    "length-centimeter": QuantityGrammar("length-centimeter", "centimeter", "centimeters"),
    "length-meter": QuantityGrammar("length-meter", "meter", "meters"),
    "length-kilometer": QuantityGrammar("length-kilometer", "kilometer", "kilometers"),
    "area-square-millimeter": QuantityGrammar(
        "area-square-millimeter", "square millimeter", "square millimeters"
    ),
    "area-square-centimeter": QuantityGrammar(
        "area-square-centimeter", "square centimeter", "square centimeters"
    ),
    "area-square-meter": QuantityGrammar("area-square-meter", "square meter", "square meters"),
    "area-square-kilometer": QuantityGrammar(
        "area-square-kilometer", "square kilometer", "square kilometers"
    ),
    "area-hectare": QuantityGrammar("area-hectare", "hectare", "hectares"),
    "volume-cubic-millimeter": QuantityGrammar(
        "volume-cubic-millimeter", "cubic millimeter", "cubic millimeters"
    ),
    "volume-cubic-centimeter": QuantityGrammar(
        "volume-cubic-centimeter", "cubic centimeter", "cubic centimeters"
    ),
    "volume-cubic-meter": QuantityGrammar("volume-cubic-meter", "cubic meter", "cubic meters"),
    "volume-milliliter": QuantityGrammar("volume-milliliter", "milliliter", "milliliters"),
    "volume-liter": QuantityGrammar("volume-liter", "liter", "liters"),
    "mass-microgram": QuantityGrammar("mass-microgram", "microgram", "micrograms"),
    "mass-milligram": QuantityGrammar("mass-milligram", "milligram", "milligrams"),
    "mass-gram": QuantityGrammar("mass-gram", "gram", "grams"),
    "mass-kilogram": QuantityGrammar("mass-kilogram", "kilogram", "kilograms"),
    "mass-tonne": QuantityGrammar("mass-tonne", "tonne", "tonnes"),
    "temperature-kelvin": QuantityGrammar("temperature-kelvin", "kelvin", "kelvins"),
    "temperature-celsius": QuantityGrammar(
        "temperature-celsius", "degree Celsius", "degrees Celsius"
    ),
    "temperature-fahrenheit": QuantityGrammar(
        "temperature-fahrenheit", "degree Fahrenheit", "degrees Fahrenheit"
    ),
    "speed-meter-per-second": QuantityGrammar(
        "speed-meter-per-second", "meter per second", "meters per second"
    ),
    "speed-kilometer-per-hour": QuantityGrammar(
        "speed-kilometer-per-hour", "kilometer per hour", "kilometers per hour"
    ),
    "duration-second": QuantityGrammar("duration-second", "second", "seconds"),
    "duration-minute": QuantityGrammar("duration-minute", "minute", "minutes"),
    "duration-hour": QuantityGrammar("duration-hour", "hour", "hours"),
    "duration-day": QuantityGrammar("duration-day", "day", "days"),
    "duration-year": QuantityGrammar("duration-year", "year", "years"),
    "customary-inch": QuantityGrammar("customary-inch", "inch", "inches"),
    "customary-foot": QuantityGrammar("customary-foot", "foot", "feet"),
    "customary-yard": QuantityGrammar("customary-yard", "yard", "yards"),
    "customary-mile": QuantityGrammar("customary-mile", "mile", "miles"),
    "customary-ounce": QuantityGrammar("customary-ounce", "ounce", "ounces"),
    "customary-pound": QuantityGrammar("customary-pound", "pound", "pounds"),
    "customary-gallon": QuantityGrammar("customary-gallon", "gallon", "gallons"),
    "customary-quart": QuantityGrammar("customary-quart", "quart", "quarts"),
    "customary-pint": QuantityGrammar("customary-pint", "pint", "pints"),
    "customary-teaspoon": QuantityGrammar("customary-teaspoon", "teaspoon", "teaspoons"),
    "customary-tablespoon": QuantityGrammar("customary-tablespoon", "tablespoon", "tablespoons"),
}
QUANTITY_GRAMMAR.update(
    {
        "data-byte": QuantityGrammar("data-byte", "byte", "bytes"),
        "data-kilobyte": QuantityGrammar("data-kilobyte", "kilobyte", "kilobytes"),
        "data-megabyte": QuantityGrammar("data-megabyte", "megabyte", "megabytes"),
        "data-gigabyte": QuantityGrammar("data-gigabyte", "gigabyte", "gigabytes"),
        "flow-cubic-meter-per-second": QuantityGrammar(
            "flow-cubic-meter-per-second", "cubic meter per second", "cubic meters per second"
        ),
        "fuel-consumption-liter-per-100-kilometer": QuantityGrammar(
            "fuel-consumption-liter-per-100-kilometer",
            "liter per 100 kilometers",
            "liters per 100 kilometers",
        ),
        "pressure-atmosphere": QuantityGrammar("pressure-atmosphere", "atmosphere", "atmospheres"),
        "pressure-kilopascal": QuantityGrammar("pressure-kilopascal", "kilopascal", "kilopascals"),
        "pressure-pascal": QuantityGrammar("pressure-pascal", "pascal", "pascals"),
        "speed-mile-per-hour": QuantityGrammar(
            "speed-mile-per-hour", "mile per hour", "miles per hour"
        ),
        "power-watt": QuantityGrammar("power-watt", "watt", "watts"),
        "power-kilowatt": QuantityGrammar("power-kilowatt", "kilowatt", "kilowatts"),
        "energy-watt-hour": QuantityGrammar("energy-watt-hour", "watt-hour", "watt-hours"),
        "energy-kilowatt-hour": QuantityGrammar(
            "energy-kilowatt-hour", "kilowatt-hour", "kilowatt-hours"
        ),
        "frequency-hertz": QuantityGrammar("frequency-hertz", "hertz", "hertz"),
        "frequency-kilohertz": QuantityGrammar("frequency-kilohertz", "kilohertz", "kilohertz"),
        "frequency-megahertz": QuantityGrammar("frequency-megahertz", "megahertz", "megahertz"),
        "frequency-gigahertz": QuantityGrammar("frequency-gigahertz", "gigahertz", "gigahertz"),
        "length-nanometer": QuantityGrammar("length-nanometer", "nanometer", "nanometers"),
        "current-ampere": QuantityGrammar("current-ampere", "ampere", "amperes"),
        "current-milliampere": QuantityGrammar(
            "current-milliampere", "milliampere", "milliamperes"
        ),
        "charge-milliampere-hour": QuantityGrammar(
            "charge-milliampere-hour", "milliampere-hour", "milliampere-hours"
        ),
        "voltage-volt": QuantityGrammar("voltage-volt", "volt", "volts"),
        "luminous-flux-lumen": QuantityGrammar("luminous-flux-lumen", "lumen", "lumens"),
        "force-newton": QuantityGrammar("force-newton", "newton", "newtons"),
        "energy-joule": QuantityGrammar("energy-joule", "joule", "joules"),
        "pressure-millimeter-mercury": QuantityGrammar(
            "pressure-millimeter-mercury", "millimeter of mercury", "millimeters of mercury"
        ),
        "amount-mole": QuantityGrammar("amount-mole", "mole", "moles"),
        "concentration-molar": QuantityGrammar("concentration-molar", "molar", "molar"),
    }
)

_DATE_DMY = re.compile(
    r"(?<![\w.])(?P<day>0?[1-9]|[12]\d|3[01])[./](?P<month>0?[1-9]|1[0-2])[./](?P<year>\d{4})(?!\d)"
)
_DATE_ISO = re.compile(
    r"(?<![\w.])(?P<year>\d{4})-(?P<month>0?[1-9]|1[0-2])-(?P<day>0?[1-9]|[12]\d|3[01])(?!\d)"
)
_DATE_ISO_SLASH = re.compile(
    r"(?<![\w.])(?P<year>\d{4})/(?P<month>0?[1-9]|1[0-2])/(?P<day>0?[1-9]|[12]\d|3[01])(?!\d)"
)
_DATE_MDY = re.compile(
    r"(?<![\w.])(?P<month>0?[1-9]|1[0-2])[/.-](?P<day>0?[1-9]|[12]\d|3[01])[/.-](?P<year>\d{2,4})(?!\d)"
)
_DATE_MD_NO_YEAR = re.compile(
    r"(?<![\w.])(?P<month>0?[1-9]|1[0-2])/(?P<day>0?[1-9]|[12]\d|3[01])(?![\w/])"
)
_TIME = re.compile(r"(?<!\w)(?P<hour>\d{1,2}):(?P<minute>\d{2})(?!\w)")
_ORDINAL_SUFFIX = re.compile(r"(?<!\w)(?P<number>\d+)(?P<suffix>st|nd|rd|th)\b", re.IGNORECASE)
_PLURAL_TENS = re.compile(r"(?<!\w)(?P<value>[2-9]0)(?P<suffix>s)(?!\w)", re.IGNORECASE)
_DECADE = re.compile(r"(?<!\w)(?P<value>(?:19|20)\d{2})s(?!\w)", re.IGNORECASE)
_VERSION_DECIMAL = re.compile(
    r"(?<![\w.])(?P<integer>\d+)\.0(?!\w|\.\d)",
)
_PLURAL_TENS_WORDS = {
    20: "twenties",
    30: "thirties",
    40: "forties",
    50: "fifties",
    60: "sixties",
    70: "seventies",
    80: "eighties",
    90: "nineties",
}


def _decade_text(value: int) -> str:
    if value % 100 == 0:
        return "two thousands" if value == 2000 else f"{value // 100} hundreds"
    tens = _PLURAL_TENS_WORDS.get(value % 100)
    if tens is not None:
        century = "nineteen" if value < 2000 else "twenty"
        return f"{century} {tens}"
    return f"{render_english_year(value)}s"


_VERSION_LABEL_WORDS = frozenset(
    {
        "version",
        "release",
        "revision",
        "rev",
        "model",
        "edition",
        "generation",
        "gen",
    }
)
_VERSION_PRODUCT_WORDS = frozenset(
    {
        "bot",
        "api",
        "app",
        "software",
        "firmware",
        "protocol",
        "platform",
        "engine",
        "system",
        "web",
    }
)
_VERSION_COMMON_WORDS = frozenset(
    {
        "a",
        "an",
        "our",
        "their",
        "the",
        "this",
        "that",
        "your",
        "my",
        "his",
        "her",
        "its",
        "we",
    }
)
_MONTHS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
_MONTH_NAME_RE = (
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
    r"Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|Jul\.?|Aug\.?|Sep\.?|Oct\.?|Nov\.?|Dec\.?)"
)
_TEXT_DATE = re.compile(
    rf"(?<![A-Za-z0-9])(?P<month>{_MONTH_NAME_RE})(?![A-Za-z])\s+"
    r"(?P<day>0?[1-9]|[12]\d|3[01])(?!\d)(?:st|nd|rd|th)?(?:,)?\s*(?P<year>\d{2,4})?",
    re.IGNORECASE,
)
_TEXT_DATE_DMY = re.compile(
    rf"(?<![A-Za-z0-9])(?P<day>0?[1-9]|[12]\d|3[01])(?:st|nd|rd|th)?\s+"
    rf"(?P<month>{_MONTH_NAME_RE})(?![A-Za-z])"
    r"(?:,)?\s*(?P<year>\d{2,4})?",
    re.IGNORECASE,
)
_TEXT_DATE_RANGE = re.compile(
    rf"(?<![A-Za-z0-9])(?P<month>{_MONTH_NAME_RE})(?![A-Za-z])\s+"
    r"(?P<start>0?[1-9]|[12]\d|3[01])(?!\d)(?:st|nd|rd|th)?\s*[-–]\s*(?P<end>0?[1-9]|[12]\d|3[01])(?!\d)(?:st|nd|rd|th)?(?:,)?\s*(?P<year>\d{2,4})",
    re.IGNORECASE,
)


def _spell(value: int, language: str = "en", *, ordinal: bool = False) -> str:
    result = str(
        num2words(
            value,
            lang=resolve_num2words_language(language),
            to="ordinal" if ordinal else "cardinal",
        )
    )
    return result.replace(",", "").replace("-", " ")


def _parts(
    raw: str, language: str = "en", *, context: str = "plain"
) -> tuple[bool, bool, int, str | None]:
    lexeme = parse_numeric_lexeme(raw, language, context=context)
    if lexeme is None:
        raise ValueError(f"Cannot parse English number {raw!r}")
    return (
        lexeme.negative,
        raw.strip().startswith("+"),
        int(lexeme.integer_digits),
        lexeme.fraction_digits,
    )


def _cardinal(value: int, language: str = "en", *, omit_conjunction: bool | None = None) -> str:
    result = _spell(value, language)
    if omit_conjunction is None:
        omit_conjunction = numeric_speech_policy(language).omit_cardinal_conjunction
    return result.replace(" and ", " ") if omit_conjunction else result


def _number_text(raw: str, language: str = "en") -> str:
    negative, positive, integer, fraction = _parts(raw, language, context="quantity")
    if fraction is None:
        result = _cardinal(integer, language)
    else:
        policy = numeric_speech_policy(language)
        result = f"{_cardinal(integer, language)} {policy.decimal_word} " + " ".join(
            _cardinal(int(group), language) for group in fraction_digit_groups(fraction, language)
        )
    if negative:
        return f"minus {result}"
    if positive:
        return f"plus {result}"
    return result


def _decimal(raw: str) -> Decimal:
    try:
        negative, _, integer, fraction = _parts(raw, context="quantity")
        value = f"{'-' if negative else ''}{integer}"
        if fraction is not None:
            value += f".{fraction}"
        return Decimal(value)
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"Cannot parse English number {raw!r}") from exc


def _valid_date(day: int, month: int, year: int) -> bool:
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _date_text(
    day: int,
    month: int,
    year: int,
    language: str = "en",
    *,
    year_digits: int | None = None,
    source_order: Literal["mdy", "dmy", "ymd"] = "mdy",
) -> str:
    return _render_date_candidate(
        DateCandidate(
            day=day,
            month=month,
            year=year,
            year_digits=year_digits,
            month_style="numeric",
            source_order=source_order,
            separator=None,
        ),
        language,
    )


def _ordinal_text(value: int, language: str = "en") -> str:
    rendered = str(num2words(value, lang=resolve_num2words_language(language), to="ordinal"))
    return " ".join(rendered.replace(",", " ").replace("-", " ").split())


def _render_date_candidate(candidate: DateCandidate, language: str = "en") -> str:
    """Render an English date without discarding its source ordering."""
    day_text = _ordinal_text(candidate.day, language)
    month_text = _MONTHS[candidate.month - 1]
    if candidate.year is None:
        return (
            f"the {day_text} of {month_text}"
            if candidate.source_order == "dmy"
            else f"{month_text} {day_text}"
        )
    year_text = render_english_year(
        candidate.year,
        language=language,
        source_digits=candidate.source_year_digits,
    )
    if candidate.source_order == "dmy":
        return f"the {day_text} of {month_text} {year_text}"
    return f"{month_text} {day_text} {year_text}"


def _date_like_context(text: str, start: int, end: int, *, day: int) -> bool:
    """Recognize no-year month/day forms without stealing fractions."""
    if start == 0 and end == len(text):
        return day >= 4
    left = text[max(0, start - 32) : start].casefold()
    right = text[end : end + 32].casefold()
    if day > 12 or re.search(r"\b(?:on|by|from|until|date|dated)\s*$", left):
        return not re.match(r"\s*(?:cup|kg|g|m|cm|in|of)\b", right)
    return False


def _valid_ordinal_suffix(number: int, suffix: str) -> bool:
    """Validate English ordinal suffixes before rendering the ordinal."""
    suffix = suffix.casefold()
    if 10 < number % 100 < 14:
        return suffix == "th"
    return suffix == {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")


def _terminal_dot(text: str, end: int) -> bool:
    return not text[end:].strip(" \t\n\"'”’»)]}")


def _quantity_text(match: UnitMatch, text: str, language: str = "en") -> str | None:
    canonical_id = match.canonical_id or ""
    grammar = QUANTITY_GRAMMAR.get(canonical_id)
    if grammar is None:
        return _currency_text(match.value, canonical_id) if match.category == "currency" else None
    try:
        value = _decimal(match.value)
    except ValueError:
        return None
    noun = grammar.singular if abs(value) == 1 else grammar.plural
    result = f"{_number_text(match.value, language)} {noun}"
    if match.symbol.endswith(".") and _terminal_dot(text, match.end):
        result += "."
    return result


def _quantity_is_plausible(match: UnitMatch, text: str) -> bool:
    """Use abbr2words ambiguity metadata as semantic evidence, not decoration."""
    ambiguity = getattr(match, "ambiguity", "none")
    if ambiguity == "none":
        return True
    left = text[max(0, match.start - 48) : match.start]
    right = text[match.end : match.end + 48]
    if ambiguity == "lexical":
        if re.search(r"\b(?:channel|album|age|record|rank)\s+\d+\s*$", left, re.IGNORECASE):
            return False
        if re.match(r"\s+(?:19|20)\d{2}\b", right):
            return False
        if re.match(r"\s+[A-Z][A-Za-z]+\b", right) and re.search(
            r"\b(?:channel|album|age|record|rank)\s+\d+\s*$", left, re.IGNORECASE
        ):
            return False
        return True
    if ambiguity == "bare_symbol":
        if re.search(
            r"\b(?:part|model|product|identifier|registration|tag|plate|license|firmware|id)\s*$",
            left,
            re.IGNORECASE,
        ):
            return False
        if re.match(r"\s*\d", right):
            return False
        formula_like = re.search(r"(?<!\w)[A-Z]\s+\d+\s+[A-Z]\s+\d+(?!\w)", text)
        if formula_like and formula_like.start() <= match.start < formula_like.end():
            return False
        return True
    return False


def _currency_text(raw: str, canonical_id: str) -> str | None:
    names = {
        "currency-us-dollar": ("dollar", "dollars", "cent", "cents"),
        "currency-pound-sterling": ("pound", "pounds", "penny", "pence"),
        "currency-euro": ("euro", "euros", "cent", "cents"),
        "currency-japanese-yen": ("yen", "yen", None, None),
        "currency-swiss-franc": ("Swiss franc", "Swiss francs", "centime", "centimes"),
        "currency-indian-rupee": ("rupee", "rupees", "paise", "paise"),
        "currency-south-korean-won": ("won", "won", None, None),
        "currency-mexican-peso": ("Mexican peso", "Mexican pesos", "centavo", "centavos"),
    }
    labels = names.get(canonical_id)
    if labels is None:
        return None
    try:
        negative, positive, integer, fraction = _parts(raw, context="currency")
    except ValueError:
        return None
    if fraction is not None and len(fraction) > 2:
        return None
    # English currency input accepts comma-separated thousands only.  An
    # ambiguous comma decimal is intentionally left unchanged.
    if "," in raw and not re.fullmatch(r"[+\-−]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", raw.strip()):
        return None
    minor = int((fraction or "").ljust(2, "0")) if fraction is not None else 0
    major_singular, major_plural, minor_singular, minor_plural = labels
    major_label = major_singular if integer == 1 else major_plural
    major = _number_text(
        ("-" if negative else "+" if positive else "") + str(integer), language="en"
    )
    result = f"{major} {major_label}"
    if minor and minor_singular is not None and minor_plural is not None:
        minor_label = minor_singular if minor == 1 else minor_plural
        result += f" and {_spell(minor)} {minor_label}"
    return result


def _overlaps(start: int, end: int, protected: tuple[tuple[int, int], ...]) -> bool:
    return any(start < right and left < end for left, right in protected)


def _is_plural_tens_context(text: str, start: int) -> bool:
    """Return whether a round-tens suffix is used as a plural marker."""
    left = text[max(0, start - 48) : start]
    if re.search(
        r"\b(?:high|low|mid|upper|lower|early|late)\s+$",
        left,
        re.IGNORECASE,
    ):
        return True
    return bool(
        re.search(
            r"\b(?:in|from|during|throughout)\s+"
            r"(?:the|his|her|their|my|your|our)\s+$",
            left,
            re.IGNORECASE,
        )
    )


def _is_version_decimal_context(text: str, start: int) -> bool:
    """Return whether a single-dot decimal is a reviewed product label."""
    left = text[max(0, start - 64) : start]
    label_match = re.search(r"\b([A-Za-z]+)\s+$", left)
    if label_match is None:
        return False
    token = label_match.group(1)
    lowered = token.casefold()
    if lowered in _VERSION_LABEL_WORDS or lowered in _VERSION_PRODUCT_WORDS:
        return True
    if lowered in _VERSION_COMMON_WORDS:
        return False
    return (token.isupper() and len(token) >= 2) or (
        token[0].isupper() and any(character.islower() for character in token[1:])
    )


def _version_decimal_text(raw: str, language: str = "en") -> str:
    """Render a reviewed ``N.0`` label with release-style ``point oh`` speech."""
    negative, positive, integer, fraction = _parts(raw)
    if fraction != "0":
        raise ValueError(f"Expected a single fractional zero, got {raw!r}")
    result = f"{_spell(integer, language)} point oh"
    if negative:
        return f"minus {result}"
    if positive:
        return f"plus {result}"
    return result


def iter_replacements(
    text: str,
    *,
    language: str = "en",
    protected_ranges: Iterable[tuple[int, int]] = (),
) -> tuple[Replacement, ...]:
    """Return exact English structured semantic replacements."""
    protected = tuple(protected_ranges)
    candidates: list[Replacement] = []

    def add(start: int, end: int, value: str | None, rule: str) -> None:
        if value is not None and not _overlaps(start, end, protected):
            candidates.append(Replacement(start, end, value, "structured", "en", rule))

    for match in _DATE_MDY.finditer(text):
        year, year_digits = expand_year(match["year"])
        if _valid_date(int(match["day"]), int(match["month"]), year):
            add(
                match.start(),
                match.end(),
                _date_text(
                    int(match["day"]),
                    int(match["month"]),
                    year,
                    language,
                    year_digits=year_digits,
                ),
                "en.date",
            )
    for match in _DATE_MD_NO_YEAR.finditer(text):
        day, month = int(match["day"]), int(match["month"])
        if _valid_date(day, month, 2000) and _date_like_context(
            text, match.start(), match.end(), day=day
        ):
            add(
                match.start(),
                match.end(),
                _render_date_candidate(
                    DateCandidate(
                        day=day,
                        month=month,
                        year=None,
                        year_digits=None,
                        month_style="numeric",
                        source_order="mdy",
                        separator=None,
                    ),
                    language,
                ),
                "en.date",
            )
    for match in _TEXT_DATE_DMY.finditer(text):
        month_name = match["month"].rstrip(".").title()
        month_index = next(
            (
                index
                for index, name in enumerate(_MONTHS, 1)
                if name.casefold().startswith(month_name.casefold())
            ),
            None,
        )
        if month_index is None:
            continue
        text_year: int | None = None
        dmy_year_digits: int | None = None
        if match["year"]:
            text_year, dmy_year_digits = expand_year(match["year"])
        day = int(match["day"])
        if text_year is None or _valid_date(day, month_index, text_year):
            value = (
                _render_date_candidate(
                    DateCandidate(
                        day=day,
                        month=month_index,
                        year=None,
                        year_digits=None,
                        month_style="name",
                        source_order="dmy",
                        separator=None,
                    ),
                    language,
                )
                if text_year is None
                else _render_date_candidate(
                    DateCandidate(
                        day=day,
                        month=month_index,
                        year=text_year,
                    year_digits=dmy_year_digits,
                        month_style="name",
                        source_order="dmy",
                        separator=None,
                    ),
                    language,
                )
            )
            add(match.start(), match.end(), value, "en.date.dmy_text")
    for match in _TEXT_DATE_RANGE.finditer(text):
        month_name = match["month"].rstrip(".").title()
        month_index = next(
            (
                index
                for index, name in enumerate(_MONTHS, 1)
                if name.casefold().startswith(month_name.casefold())
            ),
            None,
        )
        if month_index is None:
            continue
        year, _ = expand_year(match["year"])
        if _valid_date(int(match["start"]), month_index, year) and _valid_date(
            int(match["end"]), month_index, year
        ):
            if numeric_speech_policy(language).year_mode == "locale":
                year_text = render_english_year(year, language=language)
                value = f"{_MONTHS[month_index - 1]} {_spell(int(match['start']), language, ordinal=True)} through {_spell(int(match['end']), language, ordinal=True)} {year_text}"
            else:
                value = f"{_MONTHS[month_index - 1]} {_spell(int(match['start']), language, ordinal=True)} through {_spell(int(match['end']), language, ordinal=True)}, {_spell(year, language)}"
            add(match.start(), match.end(), value, "en.date-range")
    for match in _TEXT_DATE.finditer(text):
        month_name = match["month"].rstrip(".").title()
        month_index = next(
            (
                index
                for index, name in enumerate(_MONTHS, 1)
                if name.casefold().startswith(month_name.casefold())
            ),
            None,
        )
        if month_index is None:
            continue
        text_year_dmy: int | None = int(match["year"]) if match["year"] else None
        if text_year_dmy is not None:
            text_year_dmy, _ = expand_year(match["year"])
        if text_year_dmy is None or _valid_date(int(match["day"]), month_index, text_year_dmy):
            value = _render_date_candidate(
                DateCandidate(
                    day=int(match["day"]),
                    month=month_index,
                    year=text_year_dmy,
                    year_digits=len(match["year"]) if match["year"] else None,
                    month_style="name",
                    source_order="mdy",
                    separator=None,
                ),
                language,
            )
            add(match.start(), match.end(), value, "en.date.mdy_text")

    for match in _ORDINAL_SUFFIX.finditer(text):
        number = int(match["number"])
        if _valid_ordinal_suffix(number, match["suffix"]):
            add(
                match.start(),
                match.end(),
                _spell(number, language, ordinal=True),
                "en.ordinal",
            )

    for pattern in (_DATE_DMY, _DATE_ISO, _DATE_ISO_SLASH):
        for match in pattern.finditer(text):
            day, month, year = int(match["day"]), int(match["month"]), int(match["year"])
            if _valid_date(day, month, year):
                add(
                    match.start(),
                    match.end(),
                    _date_text(
                        day,
                        month,
                        year,
                        language,
                        year_digits=4,
                        source_order="dmy" if pattern is _DATE_DMY else "mdy",
                    ),
                    "en.date",
                )

    for match in _TIME.finditer(text):
        hour, minute = int(match["hour"]), int(match["minute"])
        if hour > 23 or minute > 59:
            continue
        hour_text = _spell(hour, language)
        following = text[match.end() :]
        if minute == 0 and re.match(r"\s+noon\b", following, re.IGNORECASE):
            value = hour_text
        elif minute == 0:
            value = f"{hour_text} o'clock"
        elif minute < 10:
            value = f"{hour_text} oh {_spell(minute, language)}"
        else:
            value = f"{hour_text} {_spell(minute, language)}"
        add(match.start(), match.end(), value, "en.time")

    plural_tens_spans: list[tuple[int, int]] = []
    decade_spans: list[tuple[int, int]] = []
    for match in _DECADE.finditer(text):
        start, end = match.span()
        if _overlaps(start, end, protected):
            continue
        decade_spans.append((start, end))
        add(start, end, _decade_text(int(match["value"])), "en.decade")
    for match in _PLURAL_TENS.finditer(text):
        if not _is_plural_tens_context(text, match.start()):
            continue
        start, end = match.span()
        if _overlaps(start, end, protected):
            continue
        plural_tens_spans.append((start, end))
        add(start, end, _PLURAL_TENS_WORDS[int(match["value"])], "en.plural_tens")

    dependency_language = resolve_abbr2words_language(language)
    quantity_matches = tuple(
        iter_unit_matches(text, dependency_language, protected_spans=protected)
    )
    quantity_spans = tuple((match.start, match.end) for match in quantity_matches)
    for match in _VERSION_DECIMAL.finditer(text):
        start, end = match.span()
        if _is_version_decimal_context(text, start) and not _overlaps(start, end, quantity_spans):
            add(
                start,
                end,
                _version_decimal_text(match.group(0), language),
                "en.version_decimal",
            )

    unit_protected = protected + tuple(plural_tens_spans) + tuple(decade_spans)
    for unit_match in iter_unit_matches(text, dependency_language, protected_spans=unit_protected):
        if not _quantity_is_plausible(unit_match, text):
            continue
        try:
            replacement = _quantity_text(unit_match, text, language)
        except (TypeError, ValueError):
            replacement = None
        add(
            unit_match.start,
            unit_match.end,
            replacement,
            "en.currency" if unit_match.category == "currency" else "en.quantity",
        )

    return tuple(candidates)


__all__ = ["NUMBER_POLICY", "QUANTITY_GRAMMAR", "QuantityGrammar", "iter_replacements"]
