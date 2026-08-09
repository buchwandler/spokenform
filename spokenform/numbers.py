"""Number and structured-value verbalization."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Final

from num2words import num2words

_SUPPORTED: Final[tuple[str, ...]] = ("cs", "de", "en", "es", "fr", "it", "pt")
_NUM2WORDS_LANG: Final[dict[str, str]] = {
    "cs": "cs",
    "de": "de",
    "en": "en",
    "es": "es",
    "fr": "fr",
    "it": "it",
    "pt": "pt",
}
_COMMA_DECIMAL: Final[frozenset[str]] = frozenset({"cs", "de", "es", "fr", "it", "pt"})
_MONTHS: Final[dict[str, tuple[str, ...]]] = {
    "cs": (
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
    ),
    "de": (
        "Januar",
        "Februar",
        "März",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ),
    "en": (
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
    ),
    "es": (
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
    ),
    "fr": (
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
    ),
    "it": (
        "gennaio",
        "febbraio",
        "marzo",
        "aprile",
        "maggio",
        "giugno",
        "luglio",
        "agosto",
        "settembre",
        "ottobre",
        "novembre",
        "dicembre",
    ),
    "pt": (
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
    ),
}
_TIME_JOINERS: Final[dict[str, str]] = {
    "cs": " hodin ",
    "de": " Uhr ",
    "en": " ",
    "es": " horas ",
    "fr": " heures ",
    "it": " e ",
    "pt": " e ",
}
_GERMAN_YEAR_POLICY: Final[str] = "century_for_1100_1999"

_URL_OR_EMAIL_RE = re.compile(r"https?://\S+|www\.\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_VERSION_RE = re.compile(r"(?<!\w)v\d+(?:\.\d+){2,}(?!\w)", re.IGNORECASE)
_BARE_VERSION_RE = re.compile(r"(?<![\w.])\d+(?:\.\d+){2,}(?![\w.])")
_DATE_DMY_RE = re.compile(
    r"(?<!\d)(?P<day>0?[1-9]|[12]\d|3[01])[./](?P<month>0?[1-9]|1[0-2])[./](?P<year>\d{4})(?!\d)"
)
_DATE_ISO_RE = re.compile(
    r"(?<!\d)(?P<year>\d{4})-(?P<month>0?[1-9]|1[0-2])-(?P<day>0?[1-9]|[12]\d|3[01])(?!\d)"
)
_TIME_RE = re.compile(r"(?<!\d)(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)(?!\d)(?:\s+Uhr)?")
_CURRENCY_PREFIX_RE = re.compile(
    r"(?<!\w)(?P<currency>EUR|USD|GBP|CHF|€|\$|£)\s*(?P<number>[+\-−]?(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{1,2})?)(?!\w)",
    re.IGNORECASE,
)
_CURRENCY_SUFFIX_RE = re.compile(
    r"(?<!\w)(?P<number>[+\-−]?(?:\d{1,3}(?:[.,]\d{3})+|\d+)(?:[.,]\d{1,2})?)\s*(?P<currency>EUR|USD|GBP|CHF|€|\$|£)(?!\w)",
    re.IGNORECASE,
)
_ORDINAL_RE = re.compile(r"(?<![\w.])(?P<number>\d+)\.(?=\s+[A-Za-zÀ-ž])")
_NUMBER_RE = re.compile(r"(?<![\w.])[+\-−]?(?:\d+(?:[.,]\d+)?|[.,]\d+)(?![\w.])")
_GERMAN_NUMBER_RE = re.compile(
    r"(?<![\w.])[+\-−]?(?:(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?|[.,]\d+)(?![\w.])"
)
_DATE_CANDIDATE_RE = re.compile(
    r"(?<!\d)(?P<day>\d{1,2})[./](?P<month>\d{1,2})[./](?P<year>\d{4})(?!\d)"
)
_ISO_DATE_CANDIDATE_RE = re.compile(
    r"(?<!\d)(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})(?!\d)"
)
_TIME_CANDIDATE_RE = re.compile(r"(?<!\d)(?P<hour>\d{1,2}):(?P<minute>\d{2})(?!\d)")
_SPANISH_PLAIN_NUMBER_RE = re.compile(
    r"(?<![\w.])[+\-−]?(?:(?:\d{1,3}(?:\.\d{3})+|\d+)(?:,\d+)?|,\d+)(?![\w.])"
)
_CZECH_PLAIN_NUMBER_RE = re.compile(
    r"(?<![\w.])[+\-−]?(?:(?:\d{1,3}(?:[.\s\u00a0\u202f]\d{3})+|\d+)(?:,\d+)?|,\d+)(?![\w.])"
)
_ENGLISH_PLAIN_NUMBER_RE = re.compile(
    r"(?<![\w.])[+\-−]?(?:(?:\d{1,3}(?:,\d{3})+|\d{1,3})(?:\.\d+)?|\.\d+)(?![\w.])"
)


@dataclass(frozen=True, slots=True)
class _ProtectedText:
    text: str
    values: tuple[str, ...]
    placeholder_start: int = 0xE000

    def restore(self) -> str:
        result = self.text
        for index, value in enumerate(self.values):
            result = result.replace(chr(self.placeholder_start + index), value)
        return result


def _placeholder(index: int) -> str:
    if index >= 0x1900:
        raise ValueError("Too many protected spans")
    return chr(0xE000 + index)


def _protect(text: str) -> _ProtectedText:
    values: list[str] = []

    def replace(match: re.Match[str]) -> str:
        index = len(values)
        values.append(match.group(0))
        return _placeholder(index)

    protected = _URL_OR_EMAIL_RE.sub(replace, text)
    protected = _VERSION_RE.sub(replace, protected)
    protected = _BARE_VERSION_RE.sub(replace, protected)

    def invalid_date(match: re.Match[str]) -> str:
        try:
            date(int(match["year"]), int(match["month"]), int(match["day"]))
        except ValueError:
            return replace(match)
        return match.group(0)

    protected = _DATE_CANDIDATE_RE.sub(invalid_date, protected)

    def invalid_time(match: re.Match[str]) -> str:
        if int(match["hour"]) > 23 or int(match["minute"]) > 59:
            return replace(match)
        return match.group(0)

    protected = _TIME_CANDIDATE_RE.sub(invalid_time, protected)
    return _ProtectedText(protected, tuple(values))


def _base_language(language: str) -> str:
    base = language.strip().lower().replace("_", "-").split("-", 1)[0]
    if base not in _SUPPORTED:
        supported = ", ".join(_SUPPORTED)
        raise ValueError(f"Unsupported language {language!r}. Supported languages: {supported}")
    return base


def _spell(value: int | Decimal, language: str, *, ordinal: bool = False) -> str:
    target = "ordinal" if ordinal else "cardinal"
    return str(num2words(value, lang=_NUM2WORDS_LANG[language], to=target))


def _year_text(year: int, language: str) -> str:
    if language == "de" and _GERMAN_YEAR_POLICY == "century_for_1100_1999" and 1100 <= year < 2000:
        century, remainder = divmod(year, 100)
        prefix = f"{_spell(century, language)}hundert"
        return prefix if remainder == 0 else f"{prefix}{_spell(remainder, language)}"
    return _spell(year, language)


def _decimal_value(raw: str, language: str) -> Decimal:
    normalized = raw.replace("−", "-")
    if language in _COMMA_DECIMAL:
        if "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        elif re.fullmatch(r"[+\-]?\d{1,3}(?:\.\d{3})+", normalized):
            normalized = normalized.replace(".", "")
    else:
        if "." in normalized:
            normalized = normalized.replace(",", "")
        elif re.fullmatch(r"[+\-]?\d{1,3}(?:,\d{3})+", normalized):
            normalized = normalized.replace(",", "")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise ValueError(f"Cannot parse numeric value {raw!r}") from exc


def _date_text(
    day: int,
    month: int,
    year: int,
    language: str,
    *,
    german_dative: bool = False,
) -> str:
    month_name = _MONTHS[language][month - 1]
    day_text = _spell(day, language, ordinal=language in {"de", "en"})
    year_text = _year_text(year, language)
    if language == "de":
        if german_dative:
            day_text = day_text if day_text.endswith("n") else f"{day_text}n"
        else:
            day_text = day_text if day_text.endswith("r") else f"{day_text}r"
        return f"{day_text} {month_name} {year_text}"
    if language == "en":
        return f"{month_name} {day_text}, {year_text}"
    if language in {"es", "pt"}:
        return f"{_spell(day, language)} de {month_name} de {year_text}"
    if language == "fr":
        return f"{_spell(day, language)} {month_name} {year_text}"
    return f"{day_text} {month_name} {year_text}"


def _replace_dates(text: str, language: str) -> str:
    def replacement(match: re.Match[str]) -> str:
        try:
            date(int(match.group("year")), int(match.group("month")), int(match.group("day")))
        except ValueError:
            return match.group(0)
        prefix = match.string[max(0, match.start() - 12) : match.start()]
        german_dative = language == "de" and bool(
            re.search(r"\b(?:am|zum|vom)\s*$", prefix, re.IGNORECASE)
        )
        return _date_text(
            int(match.group("day")),
            int(match.group("month")),
            int(match.group("year")),
            language,
            german_dative=german_dative,
        )

    return _DATE_ISO_RE.sub(replacement, _DATE_DMY_RE.sub(replacement, text))


def _replace_times(text: str, language: str) -> str:
    def replace(match: re.Match[str]) -> str:
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        hour_text = _spell(hour, language)
        if minute == 0:
            if language == "de":
                return f"{hour_text} Uhr"
            return hour_text
        return f"{hour_text}{_TIME_JOINERS[language]}{_spell(minute, language)}"

    return _TIME_RE.sub(replace, text)


def _currency_code(symbol: str) -> str:
    return {"€": "EUR", "$": "USD", "£": "GBP"}.get(symbol.upper(), symbol.upper())


def _replace_currencies(text: str, language: str) -> str:
    def replace(match: re.Match[str]) -> str:
        value = _decimal_value(match.group("number"), language)
        currency = _currency_code(match.group("currency"))
        try:
            return str(
                num2words(
                    value,
                    lang=_NUM2WORDS_LANG[language],
                    to="currency",
                    currency=currency,
                )
            )
        except (NotImplementedError, TypeError, ValueError):
            if language == "de" and value >= 0:
                major = int(value)
                cents = int((value - major) * 100)
                labels = {
                    "CHF": "Schweizer Franken",
                    "EUR": "Euro",
                    "USD": "Dollar",
                    "GBP": "Pfund",
                }
                result = f"{_spell(major, language)} {labels.get(currency, currency)}"
                if cents:
                    result += f" {_spell(cents, language)} Cent"
                return result
            return f"{_spell(value, language)} {currency}"

    return _CURRENCY_SUFFIX_RE.sub(replace, _CURRENCY_PREFIX_RE.sub(replace, text))


def _replace_years(text: str, language: str) -> str:
    if language not in _SUPPORTED:
        return text
    pattern = re.compile(r"(?<![\w.])(?P<year>\d{4})(?![\w.])")

    def replace(match: re.Match[str]) -> str:
        year = int(match["year"])
        return _year_text(year, language)

    return pattern.sub(replace, text)


def _replace_ordinals(text: str, language: str) -> str:
    if language not in {"cs", "de", "en"}:
        return text

    def replace(match: re.Match[str]) -> str:
        return _spell(int(match.group("number")), language, ordinal=True)

    return _ORDINAL_RE.sub(replace, text)


def _replace_numbers(text: str, language: str) -> str:
    pattern = _GERMAN_NUMBER_RE if language == "de" else _NUMBER_RE

    def replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        if language == "de":
            unsigned = raw.lstrip("+−-")
            negative = raw.startswith(("-", "−"))
            if unsigned.startswith((".", ",")):
                integer, fraction = "0", unsigned[1:]
            elif "," in unsigned:
                integer, fraction = unsigned.split(",", 1)
            else:
                integer, fraction = unsigned, None
            integer_value = int(re.sub(r"[.\s]", "", integer) or "0")
            if fraction is None:
                spoken = _spell(integer_value, language)
            else:
                spoken = f"{_spell(integer_value, language)} Komma " + " ".join(
                    _spell(int(digit), language) for digit in fraction
                )
            return f"minus {spoken}" if negative else spoken
        value = _decimal_value(raw, language)
        if value == value.to_integral_value():
            return _spell(int(value), language)
        return _spell(value, language)

    return pattern.sub(replace, text)


def normalize_numbers(text: str, *, language: str) -> str:
    """Verbalize common dates, times, currencies, ordinals, and numbers.

    URLs, email addresses, and semantic-version-like values are protected. The
    implementation is intentionally conservative and is an MVP, not a complete
    locale grammar.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    base = _base_language(language)
    if base == "cs":
        # Czech has a reviewed semantic grammar in the structured stage. Keep
        # this public convenience API on that same engine rather than allowing
        # its older generic date/currency morphology to drift independently.
        from .structured import normalize_structured

        structured = normalize_structured(text, language=language)
        return normalize_plain_numbers(structured.text, language=language)
    protected = _protect(text)
    result = protected.text
    transformations: tuple[Callable[[str, str], str], ...] = (
        _replace_dates,
        _replace_times,
        _replace_currencies,
        _replace_ordinals,
        _replace_years,
        _replace_numbers,
    )
    for transformation in transformations:
        result = transformation(result, base)
    return _ProtectedText(result, protected.values).restore()


def _protect_plain_numbers(text: str) -> _ProtectedText:
    """Protect literals and reviewed structured candidates for a plain pass."""
    values: list[str] = []
    existing_offsets = [
        ord(character) - 0xE000 for character in text if 0xE000 <= ord(character) < 0xE000 + 0x1900
    ]
    placeholder_start = 0xE000 + max(existing_offsets, default=-1) + 1

    def replace(match: re.Match[str]) -> str:
        index = len(values)
        values.append(match.group(0))
        return chr(placeholder_start + index)

    protected = _URL_OR_EMAIL_RE.sub(replace, text)
    protected = _VERSION_RE.sub(replace, protected)
    for pattern in (
        _DATE_CANDIDATE_RE,
        _ISO_DATE_CANDIDATE_RE,
        _TIME_CANDIDATE_RE,
    ):
        protected = pattern.sub(replace, protected)
    return _ProtectedText(protected, tuple(values), placeholder_start)


def _normalize_comma_decimal_plain_numbers(
    text: str,
    *,
    language: str,
    decimal_word: str,
    negative_word: str,
) -> str:
    """Verbalize ordinary comma-decimal numbers while preserving digit precision."""
    protected = _protect_plain_numbers(text)

    def replace(match: re.Match[str]) -> str:
        raw = match.group(0).replace("−", "-")
        negative = raw.startswith("-")
        unsigned = raw.lstrip("+-")
        if unsigned.startswith(","):
            integer, fraction = "0", unsigned[1:]
        elif "," in unsigned:
            integer, fraction = unsigned.split(",", 1)
        else:
            integer, fraction = re.sub(r"[.]", "", unsigned), None
        result = str(num2words(int(integer), lang=language))
        if fraction is not None:
            result += f" {decimal_word} " + " ".join(
                str(num2words(int(digit), lang=language)) for digit in fraction
            )
        return f"{negative_word} {result}" if negative else result

    return _ProtectedText(
        _SPANISH_PLAIN_NUMBER_RE.sub(replace, protected.text),
        protected.values,
        protected.placeholder_start,
    ).restore()


def _normalize_czech_plain_numbers(text: str) -> str:
    """Verbalize Czech ordinary numbers without consuming structured values."""
    from abbr2words import iter_unit_matches

    protected = _protect_plain_numbers(text)
    values = list(protected.values)
    result = protected.text
    occupied: list[tuple[int, int]] = []
    unit_matches = tuple(iter_unit_matches(result, "cs"))
    for match in reversed(unit_matches):
        if any(match.start < end and start < match.end for start, end in occupied):
            continue
        index = len(values)
        values.append(result[match.start : match.end])
        placeholder = chr(protected.placeholder_start + index)
        result = result[: match.start] + placeholder + result[match.end :]
        occupied.append((match.start, match.end))

    from .locales.cs import number_text

    def replace(match: re.Match[str]) -> str:
        return number_text(match.group(0))

    return _ProtectedText(
        _CZECH_PLAIN_NUMBER_RE.sub(replace, result),
        tuple(values),
        protected.placeholder_start,
    ).restore()


def _english_spell(value: int) -> str:
    """Spell a safe English cardinal without punctuation or hyphens."""
    return str(num2words(value, lang="en")).replace(",", "").replace("-", " ")


def _english_plain_number_text(raw: str) -> str:
    """Render one reviewed English ordinary number, preserving fraction digits."""
    normalized = raw.replace("−", "-")
    negative = normalized.startswith("-")
    positive = normalized.startswith("+")
    unsigned = normalized.lstrip("+-").replace(",", "")
    if unsigned.startswith("."):
        integer, fraction = "", unsigned[1:]
        result = "point " + " ".join(_english_spell(int(digit)) for digit in fraction)
    elif "." in unsigned:
        integer, fraction = unsigned.split(".", 1)
        result = f"{_english_spell(int(integer))} point " + " ".join(
            _english_spell(int(digit)) for digit in fraction
        )
    else:
        result = _english_spell(int(unsigned))
    if negative:
        return f"minus {result}"
    if positive:
        return f"plus {result}"
    return result


def _protect_english_units(protected: _ProtectedText) -> _ProtectedText:
    """Reserve every recognized unit so unknown/future IDs fail closed."""
    from abbr2words import iter_unit_matches

    values = list(protected.values)
    result = protected.text
    occupied: list[tuple[int, int]] = []
    for match in reversed(tuple(iter_unit_matches(result, "en"))):
        if any(match.start < end and start < match.end for start, end in occupied):
            continue
        index = len(values)
        values.append(result[match.start : match.end])
        placeholder = chr(protected.placeholder_start + index)
        result = result[: match.start] + placeholder + result[match.end :]
        occupied.append((match.start, match.end))
    return _ProtectedText(result, tuple(values), protected.placeholder_start)


def _normalize_english_plain_numbers(text: str) -> str:
    """Verbalize only low-risk English cardinals and decimals.

    Four-digit and longer ungrouped digit strings are deliberately excluded:
    they may be years, phone/ID values, or another downstream-owned sequence.
    Dates, times, versions, URLs, emails, and recognized units are protected
    atomically before this pass.
    """
    protected = _protect_english_units(_protect_plain_numbers(text))

    def replace(match: re.Match[str]) -> str:
        return _english_plain_number_text(match.group(0))

    return _ProtectedText(
        _ENGLISH_PLAIN_NUMBER_RE.sub(replace, protected.text),
        protected.values,
        protected.placeholder_start,
    ).restore()


def normalize_plain_numbers(text: str, *, language: str) -> str:
    """Verbalize only ordinary numbers, preserving all structured candidates."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    base = _base_language(language)
    if base == "cs":
        return _normalize_czech_plain_numbers(text)
    if base in {"es", "it", "pt"}:
        number_language = language
        if base == "pt":
            number_language = "pt_BR" if language in {"pt", "pt-br"} else "pt"
        return _normalize_comma_decimal_plain_numbers(
            text,
            language=number_language,
            decimal_word={"es": "coma", "it": "virgola", "pt": "vírgula"}[base],
            negative_word={"es": "menos", "it": "meno", "pt": "menos"}[base],
        )
    if base == "en":
        return _normalize_english_plain_numbers(text)
    return normalize_numbers(text, language=base)
