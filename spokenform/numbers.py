"""Number and structured-value verbalization."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Final

from num2words import num2words

from .casing import capitalize_generated_input_start, capitalize_generated_sentence_start
from .language import (
    SUPPORTED_BASE_LANGUAGES,
    base_language,
    normalize_language,
    resolve_abbr2words_language,
    resolve_num2words_language,
)
from .numeric_lexeme import (
    NumberRenderMode,
    NumericLexeme,
    fraction_digit_groups,
    numeric_speech_policy,
    parse_numeric_lexeme,
)

_COMMA_DECIMAL: Final[frozenset[str]] = frozenset({"cs", "de", "es", "fr", "it", "pt"})
_BARE_DOT_ORDINAL_COMPAT_LANGUAGES: Final[frozenset[str]] = frozenset({"de"})
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
_NUMBER_RE = re.compile(r"(?<![\w.])[+\-−]?(?:\d+(?:[.,]\d+)?|[.,]\d+)(?!\w|\.\d)")
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
    r"(?<![\w.])[+\-−]?(?:(?:\d{1,3}(?:,\d{3})+|\d{1,3})(?:\.\d+)?|\.\d+)(?!\w|\.\d)"
)
_UNIFIED_PLAIN_NUMBER_RE = re.compile(
    r"(?<![\w.])[+\-−]?(?:(?:\d{1,3}(?:[ \u00a0\u202f]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)+|[.,]\d+)|\d+)(?!\w)"
)
_LONG_NUMBER_POSITIVE_CONTEXT_RE = re.compile(
    r"\b(?:there\s+are|population|total|amount|number\s+of|count\s+of|items?|users?|people|"
    r"records?|entries|downloads?|views?|inhabitants?)\b",
    re.IGNORECASE,
)
_LONG_NUMBER_IDENTIFIER_CONTEXT_RE = re.compile(
    r"\b(?:pin|id|serial|number|code|account|isbn|phone|telephone|mobile|postal|zip|"
    r"suite|unit|plate|model|product|sku|vin|imei|iccid|iban|registration)\b",
    re.IGNORECASE,
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


def _protect(text: str, *, language: str | None = None) -> _ProtectedText:
    values: list[str] = []

    def replace(match: re.Match[str]) -> str:
        index = len(values)
        values.append(match.group(0))
        return _placeholder(index)

    protected = _URL_OR_EMAIL_RE.sub(replace, text)
    protected = _VERSION_RE.sub(replace, protected)
    base = base_language(language) if language else None

    def bare_version(match: re.Match[str]) -> str:
        value = match.group(0)
        if base == "de" and (
            re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value)
            or re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{2,4}", value)
        ):
            return value
        return replace(match)

    protected = _BARE_VERSION_RE.sub(bare_version, protected)

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
    base = base_language(language)
    if base not in SUPPORTED_BASE_LANGUAGES:
        supported = ", ".join(SUPPORTED_BASE_LANGUAGES)
        raise ValueError(f"Unsupported language {language!r}. Supported languages: {supported}")
    return base


def _spell(value: int | Decimal, language: str, *, ordinal: bool = False) -> str:
    target = "ordinal" if ordinal else "cardinal"
    return str(num2words(value, lang=resolve_num2words_language(language), to=target))


def _year_text(year: int, language: str) -> str:
    base = base_language(language)
    if base == "en" and 1900 <= year < 2000:
        century, remainder = divmod(year, 100)
        prefix = _spell(century, language)
        if remainder == 0:
            return prefix
        if remainder < 10:
            return f"{prefix} oh {_spell(remainder, language)}"
        return f"{prefix} {_spell(remainder, language)}"
    if base == "de" and _GERMAN_YEAR_POLICY == "century_for_1100_1999" and 1100 <= year < 2000:
        century, remainder = divmod(year, 100)
        prefix = f"{_spell(century, language)}hundert"
        return prefix if remainder == 0 else f"{prefix}{_spell(remainder, language)}"
    return _spell(year, language)


def _decimal_value(raw: str, language: str) -> Decimal:
    language = base_language(language)
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
    base = base_language(language)
    month_name = _MONTHS[base][month - 1]
    day_text = _spell(day, language, ordinal=base in {"de", "en"})
    year_text = _year_text(year, language)
    if base == "de":
        if german_dative:
            day_text = day_text if day_text.endswith("n") else f"{day_text}n"
        else:
            day_text = day_text if day_text.endswith("r") else f"{day_text}r"
        return f"{day_text} {month_name} {year_text}"
    if base == "en":
        return f"{month_name} {day_text}, {year_text}"
    if base in {"es", "pt"}:
        return f"{_spell(day, language)} de {month_name} de {year_text}"
    if base == "fr":
        return f"{_spell(day, language)} {month_name} {year_text}"
    return f"{day_text} {month_name} {year_text}"


def _replace_dates(text: str, language: str) -> str:
    base = base_language(language)

    def replacement(match: re.Match[str]) -> str:
        try:
            date(int(match.group("year")), int(match.group("month")), int(match.group("day")))
        except ValueError:
            return match.group(0)
        prefix = match.string[max(0, match.start() - 12) : match.start()]
        german_dative = base == "de" and bool(
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
    base = base_language(language)

    def replace(match: re.Match[str]) -> str:
        hour = int(match.group("hour"))
        minute = int(match.group("minute"))
        hour_text = _spell(hour, language)
        if minute == 0:
            if base == "de":
                return f"{hour_text} Uhr"
            return hour_text
        return f"{hour_text}{_TIME_JOINERS[base]}{_spell(minute, language)}"

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
                    lang=resolve_num2words_language(language),
                    to="currency",
                    currency=currency,
                )
            )
        except (NotImplementedError, TypeError, ValueError):
            if base_language(language) == "de" and value >= 0:
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
    if base_language(language) not in SUPPORTED_BASE_LANGUAGES:
        return text
    pattern = re.compile(r"(?<![\w.])(?P<year>\d{4})(?![\w.])")

    def replace(match: re.Match[str]) -> str:
        year = int(match["year"])
        return _year_text(year, language)

    return pattern.sub(replace, text)


def _replace_ordinals(text: str, language: str) -> str:
    if base_language(language) not in {"cs", "de", "en"}:
        return text

    def replace(match: re.Match[str]) -> str:
        return _spell(int(match.group("number")), language, ordinal=True)

    return _ORDINAL_RE.sub(replace, text)


def _replace_numbers(text: str, language: str) -> str:
    base = base_language(language)
    pattern = _GERMAN_NUMBER_RE if base == "de" else _NUMBER_RE

    def replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        if (
            raw.startswith(("-", "−"))
            and match.start() > 0
            and match.string[match.start() - 1] in "-−"
        ):
            raw = raw[1:]
        if base == "de":
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
        if base == "en" and "." in raw:
            return _english_plain_number_text(raw, language)
        if base in {"es", "it"} and "." in raw and re.search(r"\.\d{1,2}$", raw):
            integer, fraction = raw.replace("−", "-").lstrip("+-").split(".", 1)
            decimal_word = "coma" if base == "es" else "virgola"
            result = f"{_spell(int(integer or '0'), language)} {decimal_word} " + " ".join(
                _spell(int(digit), language) for digit in fraction
            )
            return f"minus {result}" if raw.startswith(("-", "−")) else result
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
    language = normalize_language(language)
    base = _base_language(language)
    if base == "cs":
        # Czech has a reviewed semantic grammar in the structured stage. Keep
        # this public convenience API on that same engine rather than allowing
        # its older generic date/currency morphology to drift independently.
        from .structured import normalize_structured

        structured = normalize_structured(text, language=language)
        return normalize_plain_numbers(structured.text, language=language)
    protected = _protect(text, language=language)
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
    restored = _ProtectedText(result, protected.values).restore()
    return capitalize_generated_input_start(source=text, replacement=restored, language=language)


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


def _protect_reserved_ranges(
    text: str,
    protected_ranges: tuple[tuple[int, int], ...],
) -> _ProtectedText:
    """Hide already-rendered structured output from the plain-number pass."""
    selected: list[tuple[int, int]] = []
    for start, end in sorted(protected_ranges):
        start = max(0, start)
        end = min(len(text), end)
        if start >= end or (selected and start < selected[-1][1]):
            continue
        selected.append((start, end))
    values = [text[start:end] for start, end in selected]
    result = text
    existing_offsets = [
        ord(character) - 0xE000 for character in text if 0xE000 <= ord(character) < 0xE000 + 0x1900
    ]
    placeholder_start = 0xE000 + max(existing_offsets, default=-1) + 1
    for index in reversed(range(len(selected))):
        start, end = selected[index]
        result = result[:start] + chr(placeholder_start + index) + result[end:]
    return _ProtectedText(result, tuple(values), placeholder_start)


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
        result = str(num2words(int(integer), lang=resolve_num2words_language(language)))
        if fraction is not None:
            result += f" {decimal_word} " + " ".join(
                str(num2words(int(digit), lang=resolve_num2words_language(language)))
                for digit in fraction
            )
        return f"{negative_word} {result}" if negative else result

    return _ProtectedText(
        _SPANISH_PLAIN_NUMBER_RE.sub(replace, protected.text),
        protected.values,
        protected.placeholder_start,
    ).restore()


def _normalize_czech_plain_numbers(text: str, language: str = "cs") -> str:
    """Verbalize Czech ordinary numbers without consuming structured values."""
    from abbr2words import iter_unit_matches

    protected = _protect_plain_numbers(text)
    values = list(protected.values)
    result = protected.text
    occupied: list[tuple[int, int]] = []
    unit_matches = tuple(iter_unit_matches(result, resolve_abbr2words_language(language)))
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
        return number_text(match.group(0), language=language)

    return _ProtectedText(
        _CZECH_PLAIN_NUMBER_RE.sub(replace, result),
        tuple(values),
        protected.placeholder_start,
    ).restore()


def _english_spell(value: int, language: str = "en") -> str:
    """Spell a safe English cardinal without punctuation or hyphens."""
    return (
        str(num2words(value, lang=resolve_num2words_language(language)))
        .replace(",", "")
        .replace("-", " ")
        .replace(" and ", " ")
    )


def _english_plain_number_text(raw: str, language: str = "en") -> str:
    """Render one reviewed English ordinary number, preserving fraction digits."""
    normalized = raw.replace("−", "-")
    negative = normalized.startswith("-")
    positive = normalized.startswith("+")
    unsigned = normalized.lstrip("+-").replace(",", "")
    if unsigned.startswith("."):
        integer, fraction = "", unsigned[1:]
        result = "point " + " ".join(_english_spell(int(digit), language) for digit in fraction)
    elif "." in unsigned:
        integer, fraction = unsigned.split(".", 1)
        result = f"{_english_spell(int(integer), language)} point " + " ".join(
            _english_spell(int(digit), language) for digit in fraction
        )
    else:
        result = _english_spell(int(unsigned), language)
    if negative:
        return f"minus {result}"
    if positive:
        return f"plus {result}"
    return result


def _protect_english_units(protected: _ProtectedText, language: str = "en") -> _ProtectedText:
    """Reserve every recognized unit so unknown/future IDs fail closed."""
    from abbr2words import iter_unit_matches

    values = list(protected.values)
    result = protected.text
    occupied: list[tuple[int, int]] = []
    for match in reversed(tuple(iter_unit_matches(result, resolve_abbr2words_language(language)))):
        if any(match.start < end and start < match.end for start, end in occupied):
            continue
        index = len(values)
        values.append(result[match.start : match.end])
        placeholder = chr(protected.placeholder_start + index)
        result = result[: match.start] + placeholder + result[match.end :]
        occupied.append((match.start, match.end))
    return _ProtectedText(result, tuple(values), protected.placeholder_start)


def _normalize_english_plain_numbers(text: str, language: str = "en") -> str:
    """Verbalize only low-risk English cardinals and decimals.

    Four-digit and longer ungrouped digit strings are deliberately excluded:
    they may be years, phone/ID values, or another downstream-owned sequence.
    Dates, times, versions, URLs, emails, and recognized units are protected
    atomically before this pass.
    """
    protected = _protect_english_units(_protect_plain_numbers(text), language)

    def replace(match: re.Match[str]) -> str:
        return _english_plain_number_text(match.group(0), language)

    return _ProtectedText(
        _ENGLISH_PLAIN_NUMBER_RE.sub(replace, protected.text),
        protected.values,
        protected.placeholder_start,
    ).restore()


def _negative_word(language: str) -> str:
    return {
        "de": "minus",
        "en": "minus",
        "es": "menos",
        "fr": "moins",
        "it": "meno",
        "pt": "menos",
    }.get(base_language(language), "minus")


def _render_numeric_lexeme(
    lexeme: NumericLexeme,
    language: str,
    *,
    mode: NumberRenderMode = NumberRenderMode.CARDINAL,
) -> str:
    """Render a parsed lexeme without reparsing its punctuation."""
    positive = lexeme.raw.startswith("+")
    if mode is NumberRenderMode.DIGIT_SEQUENCE:
        result = " ".join(
            str(num2words(int(digit), lang=resolve_num2words_language(language)))
            for digit in lexeme.integer_digits
        )
    elif mode is NumberRenderMode.YEAR:
        result = _year_text(int(lexeme.integer_digits), language)
    elif mode is NumberRenderMode.ORDINAL:
        result = _spell(int(lexeme.integer_digits), language, ordinal=True)
    elif lexeme.fraction_digits is not None or mode is NumberRenderMode.DECIMAL:
        policy = numeric_speech_policy(language)
        leading_decimal = lexeme.raw.lstrip("+−-").startswith((".", ","))
        integer = (
            ""
            if leading_decimal and base_language(language) == "en"
            else _english_spell(int(lexeme.integer_digits), language)
            if base_language(language) == "en"
            else _spell(int(lexeme.integer_digits), language)
        )
        groups = fraction_digit_groups(lexeme.fraction_digits or "", language)
        rendered_groups = []
        for group in groups:
            if len(group) == 1:
                rendered_groups.append(_spell(int(group), language))
            else:
                rendered_groups.append(
                    _english_spell(int(group), language)
                    if base_language(language) == "en"
                    else _spell(int(group), language)
                )
        result = f"{integer + ' ' if integer else ''}{policy.decimal_word} {' '.join(rendered_groups)}".rstrip()
    else:
        result = (
            _english_spell(int(lexeme.integer_digits), language)
            if base_language(language) == "en"
            else _spell(int(lexeme.integer_digits), language)
        )
    if lexeme.negative:
        return f"{_negative_word(language)} {result}"
    if positive:
        return f"plus {result}"
    return result


def _normalize_unified_plain_numbers(
    text: str, language: str, *, long_number_mode: str = "preserve"
) -> str:
    """Normalize plain numbers through the same lexeme parser as quantities."""
    protected = _protect_plain_numbers(text)

    def replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        if (
            raw.startswith(("-", "−"))
            and match.start() > 0
            and match.string[match.start() - 1] in "-−"
        ):
            raw = raw[1:]
        unsigned = raw.lstrip("+−-")
        if (
            base_language(language) in _BARE_DOT_ORDINAL_COMPAT_LANGUAGES
            and len(unsigned) == 1
            and match.string[match.end() : match.end() + 1] == "."
            and not re.match(r"\.\d", match.string[match.end() :])
        ):
            return raw
        if (
            base_language(language) == "en"
            and "." not in unsigned
            and "," not in unsigned
            and len(unsigned) > 3
            and long_number_mode == "preserve"
        ):
            return raw
        if (
            long_number_mode == "contextual"
            and "." not in unsigned
            and "," not in unsigned
            and len(unsigned) > 3
        ):
            if unsigned.startswith("0"):
                return raw
            left_context = match.string[max(0, match.start() - 64) : match.start()]
            right_context = match.string[match.end() : match.end() + 32]
            context = f"{left_context} {right_context}"
            if _LONG_NUMBER_IDENTIFIER_CONTEXT_RE.search(
                left_context
            ) or not _LONG_NUMBER_POSITIVE_CONTEXT_RE.search(context):
                return raw
        before = match.string[max(0, match.start() - 1) : match.start()]
        after = match.string[match.end() : match.end() + 1]
        fraction_tail = re.split(r"[.,]", unsigned)[-1]
        if len(fraction_tail) > 2 and ((before and before in "$€£") or (after and after in "$€£")):
            return raw
        lexeme = parse_numeric_lexeme(raw, language, context="plain")
        if lexeme is None:
            return raw
        return capitalize_generated_sentence_start(
            source=match.string,
            start=match.start(),
            replacement=_render_numeric_lexeme(lexeme, language),
            language=language,
        )

    result = _UNIFIED_PLAIN_NUMBER_RE.sub(replace, protected.text)
    return _ProtectedText(result, protected.values, protected.placeholder_start).restore()


def normalize_plain_numbers(
    text: str,
    *,
    language: str,
    protected_ranges: tuple[tuple[int, int], ...] = (),
    long_number_mode: str = "preserve",
) -> str:
    """Verbalize only ordinary numbers, preserving all structured candidates."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    language = normalize_language(language)
    if long_number_mode not in {"preserve", "contextual", "cardinal"}:
        raise ValueError("long_number_mode must be 'preserve', 'contextual', or 'cardinal'")
    base = _base_language(language)
    reserved = _protect_reserved_ranges(text, protected_ranges)
    working = reserved.text
    if base == "cs":
        result = _normalize_czech_plain_numbers(working, language)
    else:
        result = _normalize_unified_plain_numbers(
            working, language, long_number_mode=long_number_mode
        )
    for index, value in enumerate(reserved.values):
        result = result.replace(chr(reserved.placeholder_start + index), value)
    return result
