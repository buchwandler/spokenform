"""Number and structured-value verbalization."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
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
        "ledna", "února", "března", "dubna", "května", "června",
        "července", "srpna", "září", "října", "listopadu", "prosince",
    ),
    "de": (
        "Januar", "Februar", "März", "April", "Mai", "Juni",
        "Juli", "August", "September", "Oktober", "November", "Dezember",
    ),
    "en": (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ),
    "es": (
        "enero", "febrero", "marzo", "abril", "mayo", "junio",
        "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    ),
    "fr": (
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ),
    "it": (
        "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
        "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre",
    ),
    "pt": (
        "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
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

_URL_OR_EMAIL_RE = re.compile(r"https?://\S+|www\.\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_VERSION_RE = re.compile(r"(?<!\w)v\d+(?:\.\d+){2,}(?!\w)", re.IGNORECASE)
_DATE_DMY_RE = re.compile(r"(?<!\d)(?P<day>0?[1-9]|[12]\d|3[01])[./](?P<month>0?[1-9]|1[0-2])[./](?P<year>\d{4})(?!\d)")
_DATE_ISO_RE = re.compile(r"(?<!\d)(?P<year>\d{4})-(?P<month>0?[1-9]|1[0-2])-(?P<day>0?[1-9]|[12]\d|3[01])(?!\d)")
_TIME_RE = re.compile(r"(?<!\d)(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)(?!\d)(?:\s+Uhr)?")
_CURRENCY_PREFIX_RE = re.compile(
    r"(?<!\w)(?P<currency>[€$£])\s*(?P<number>[+\-−]?\d+(?:[.,]\d{1,2})?)(?!\w)"
)
_CURRENCY_SUFFIX_RE = re.compile(
    r"(?<!\w)(?P<number>[+\-−]?\d+(?:[.,]\d{1,2})?)\s*(?P<currency>EUR|USD|GBP|€|\$|£)(?!\w)",
    re.IGNORECASE,
)
_ORDINAL_RE = re.compile(r"(?<![\w.])(?P<number>\d+)\.(?=\s+[A-Za-zÀ-ž])")
_NUMBER_RE = re.compile(r"(?<![\w.])[+\-−]?\d+(?:[.,]\d+)?(?![\w.])")


@dataclass(frozen=True, slots=True)
class _ProtectedText:
    text: str
    values: tuple[str, ...]

    def restore(self) -> str:
        result = self.text
        for index, value in enumerate(self.values):
            result = result.replace(_placeholder(index), value)
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
    year_text = _spell(year, language)
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
            return f"{_spell(value, language)} {currency}"

    return _CURRENCY_SUFFIX_RE.sub(replace, _CURRENCY_PREFIX_RE.sub(replace, text))


def _replace_ordinals(text: str, language: str) -> str:
    if language not in {"cs", "de", "en"}:
        return text

    def replace(match: re.Match[str]) -> str:
        return _spell(int(match.group("number")), language, ordinal=True)

    return _ORDINAL_RE.sub(replace, text)


def _replace_numbers(text: str, language: str) -> str:
    def replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        value = _decimal_value(raw, language)
        if value == value.to_integral_value():
            return _spell(int(value), language)
        return _spell(value, language)

    return _NUMBER_RE.sub(replace, text)


def normalize_numbers(text: str, *, language: str) -> str:
    """Verbalize common dates, times, currencies, ordinals, and numbers.

    URLs, email addresses, and semantic-version-like values are protected. The
    implementation is intentionally conservative and is an MVP, not a complete
    locale grammar.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    base = _base_language(language)
    protected = _protect(text)
    result = protected.text
    transformations: tuple[Callable[[str, str], str], ...] = (
        _replace_dates,
        _replace_times,
        _replace_currencies,
        _replace_ordinals,
        _replace_numbers,
    )
    for transformation in transformations:
        result = transformation(result, base)
    return _ProtectedText(result, protected.values).restore()
