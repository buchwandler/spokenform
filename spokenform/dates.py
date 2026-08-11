"""Small parsed date models shared by locale grammars."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass(frozen=True, slots=True)
class ParsedDate:
    """A validated calendar date retaining the source year width."""

    day: int
    month: int
    year: int | None = None
    year_digits: int | None = None

    @property
    def source_year_digits(self) -> int | None:
        """Number of year digits present in the source lexeme."""
        return self.year_digits

    @property
    def normalized_year_value(self) -> int | None:
        """Expanded year value used only when the selected policy needs it."""
        return self.year

    def valid(self) -> bool:
        if self.year is None:
            return 1 <= self.day <= 31 and 1 <= self.month <= 12
        try:
            date(self.year, self.month, self.day)
        except ValueError:
            return False
        return True


@dataclass(frozen=True, slots=True)
class ParsedDateRange:
    """Two dates represented by one source expression."""

    start: ParsedDate
    end: ParsedDate


@dataclass(frozen=True, slots=True)
class DateCandidate:
    """Source-aware date shape retained until a locale renders the value."""

    day: int
    month: int
    year: int | None
    year_digits: int | None
    month_style: Literal["numeric", "name", "abbrev"]
    source_order: Literal["mdy", "dmy", "ymd"]
    separator: str | None
    year_was_apostrophe: bool = False

    @property
    def source_year_digits(self) -> int | None:
        return self.year_digits

    @property
    def normalized_year_value(self) -> int | None:
        return self.year


def expand_year(raw: str, *, pivot: int = 68) -> tuple[int, int]:
    """Expand a short year and return ``(year, source_digit_count)``."""
    digits = len(raw)
    value = int(raw)
    if digits == 2:
        value += 2000 if value <= pivot else 1900
    return value, digits


def parsed_date(day: str, month: str, year: str | None = None) -> ParsedDate:
    """Build a parsed date model without accepting invalid calendar values."""
    expanded_year, digits = expand_year(year) if year else (None, None)
    result = ParsedDate(int(day), int(month), expanded_year, digits)
    if not result.valid():
        raise ValueError(f"Invalid date: {result!r}")
    return result


__all__ = [
    "DateCandidate",
    "ParsedDate",
    "ParsedDateRange",
    "expand_year",
    "parsed_date",
]
