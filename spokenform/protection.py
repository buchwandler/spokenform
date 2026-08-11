"""Protected ranges that generic normalization must leave unchanged."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


class ProtectionError(ValueError):
    """Raised when a protected range cannot be applied safely."""


@dataclass(frozen=True, slots=True)
class ProtectedSpan:
    """A source-aligned range protected from generic verbalization."""

    start: int
    end: int
    kind: str = "literal"
    source: str = "caller"

    def validate(self, text_length: int) -> None:
        if self.start < 0 or self.end < self.start or self.end > text_length:
            raise ProtectionError(
                f"Invalid protected range ({self.start}, {self.end}) for text of length {text_length}"
            )


_LITERAL_PATTERNS = (
    ("url", re.compile(r"https?://\S+|www\.\S+")),
    ("email", re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")),
    ("version", re.compile(r"(?<!\w)v\d+(?:\.\d+){2,}(?!\w)", re.IGNORECASE)),
    (
        "version",
        re.compile(r"(?<!\w)(?!\d{1,2}\.\d{1,2}\.\d{4}(?!\d))\d+\.\d+\.\d+(?!\w)"),
    ),
)


def discover_protected_spans(
    text: str, *, language: str | None = None
) -> tuple[ProtectedSpan, ...]:
    """Find auto-literals that generic stages must not partially rewrite."""
    base = language.replace("-", "_").split("_", 1)[0].casefold() if language else None
    found: list[ProtectedSpan] = []
    occupied: list[tuple[int, int]] = []
    for kind, pattern in _LITERAL_PATTERNS:
        for match in pattern.finditer(text):
            span = (match.start(), match.end())
            if kind == "version" and (_is_strong_sequence(text) or _is_contextual_version(text, match.start())):
                continue
            if kind == "version" and base == "de" and _is_german_number_or_date(match.group(0)):
                continue
            if any(start < span[1] and span[0] < end for start, end in occupied):
                continue
            occupied.append(span)
            found.append(ProtectedSpan(*span, kind=kind, source="discovered"))
    return tuple(sorted(found, key=lambda item: (item.start, item.end)))


def _is_german_number_or_date(value: str) -> bool:
    return bool(
        re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value)
        or re.fullmatch(r"\d{1,2}\.\d{1,2}\.\d{2,4}", value)
    )


def _is_strong_sequence(text: str) -> bool:
    """Keep canonical identifiers available to semantic recognizers."""
    return bool(
        re.search(r"(?<!\w)\d{1,3}(?:\.\d{1,3}){3}(?!\w)", text)
        or re.search(r"(?<![\w-])[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}(?![\w-])", text)
        or re.search(r"(?<![\w:])(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}(?![\w:])", text)
    )


def _is_contextual_version(text: str, start: int) -> bool:
    prefix = text[max(0, start - 24) : start]
    return bool(re.search(r"(?:version|release|ver\.?|build)\s*[=:]?\s*$", prefix, re.IGNORECASE))


def coerce_protected_spans(
    spans: Any,
    *,
    text_length: int,
    strict: bool,
) -> tuple[tuple[ProtectedSpan, ...], tuple[str, ...]]:
    """Validate caller ranges while retaining recoverable warnings."""
    if spans is None:
        return (), ()
    result: list[ProtectedSpan] = []
    warnings: list[str] = []
    for item in spans:
        if isinstance(item, ProtectedSpan):
            candidate = item
        elif hasattr(item, "start") and hasattr(item, "end"):
            candidate = ProtectedSpan(
                int(item.start),
                int(item.end),
                kind=str(getattr(item, "kind", "literal")),
                source=str(getattr(item, "source", "caller")),
            )
        else:
            try:
                start, end = item
            except (TypeError, ValueError) as exc:
                raise ProtectionError(f"Invalid protected span {item!r}") from exc
            candidate = ProtectedSpan(int(start), int(end))
        try:
            candidate.validate(text_length)
        except ProtectionError as exc:
            if strict:
                raise
            warnings.append(f"[PROTECT] {exc}")
            continue
        if any(
            existing.start < candidate.end and candidate.start < existing.end for existing in result
        ):
            message = f"[PROTECT] overlapping protected span ({candidate.start}, {candidate.end})"
            if strict:
                raise ProtectionError(message)
            warnings.append(message)
            continue
        result.append(candidate)
    return tuple(sorted(result, key=lambda item: (item.start, item.end))), tuple(warnings)


@dataclass(frozen=True, slots=True)
class ProtectedText:
    text: str
    spans: tuple[ProtectedSpan, ...]
    values: tuple[str, ...]
    placeholders: tuple[str, ...] = ()

    def restore(self, text: str | None = None) -> str:
        result = self.text if text is None else text
        for index, value in enumerate(self.values):
            placeholder = (
                self.placeholders[index] if index < len(self.placeholders) else _placeholder(index)
            )
            result = result.replace(placeholder, value)
        return result


def _placeholder(index: int) -> str:
    if index >= 0x1900:
        raise ProtectionError("Too many protected spans")
    return chr(0xE000 + index)


def protect_text(text: str, spans: tuple[ProtectedSpan, ...]) -> ProtectedText:
    """Replace protected source ranges with input-safe private-use sentinels."""
    if not spans:
        return ProtectedText(text, (), ())
    placeholders = _allocate_placeholders(text, len(spans))
    parts: list[str] = []
    values: list[str] = []
    cursor = 0
    for index, span in enumerate(spans):
        parts.append(text[cursor : span.start])
        values.append(text[span.start : span.end])
        parts.append(placeholders[index])
        cursor = span.end
    parts.append(text[cursor:])
    return ProtectedText("".join(parts), spans, tuple(values), placeholders)


def _allocate_placeholders(text: str, count: int) -> tuple[str, ...]:
    """Allocate private-use characters absent from *text* and each other."""
    if count <= 0:
        return ()
    used = set(text)
    candidates = (
        range(0xE000, 0xF900),
        range(0xF0000, 0x100000),
        range(0x100000, 0x110000),
    )
    placeholders: list[str] = []
    for codepoints in candidates:
        for codepoint in codepoints:
            placeholder = chr(codepoint)
            if placeholder in used:
                continue
            placeholders.append(placeholder)
            used.add(placeholder)
            if len(placeholders) == count:
                return tuple(placeholders)
    raise ProtectionError("Too many protected spans for available private-use sentinels")


__all__ = [
    "ProtectedSpan",
    "ProtectedText",
    "ProtectionError",
    "coerce_protected_spans",
    "discover_protected_spans",
    "protect_text",
]
