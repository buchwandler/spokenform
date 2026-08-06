"""Optional SSMD parsing and rendering adapters."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape

from .models import LanguageSpan, SemanticSpan
from .protection import ProtectedSpan


class SSMDParseError(ValueError):
    """Raised when requested SSMD cannot be parsed safely."""


@dataclass(frozen=True, slots=True)
class ParsedMarkup:
    source_text: str
    clean_text: str
    semantic_spans: tuple[SemanticSpan, ...] = ()
    language_spans: tuple[LanguageSpan, ...] = ()
    protected_spans: tuple[ProtectedSpan, ...] = ()
    warnings: tuple[str, ...] = ()


_AUTO_MARKUP_RE = re.compile(r"\[[^\]\n]+\]\{[^}\n]+\}")


def parse_markup(
    text: str,
    *,
    mode: str,
    language: str | None = None,
    strict: bool = False,
) -> ParsedMarkup:
    """Parse SSMD into clean text and provider-neutral spans."""
    if mode == "plain" or (mode == "auto" and not _AUTO_MARKUP_RE.search(text)):
        return ParsedMarkup(text, text)
    if mode not in {"ssmd", "auto"}:
        raise ValueError(f"Unsupported markup mode {mode!r}")
    try:
        import ssmd
    except ImportError as exc:
        raise RuntimeError(
            "SSMD support requires the 'ssmd' extra: python -m pip install 'spokenform[ssmd]'"
        ) from exc

    try:
        parsed = ssmd.parse_spans(
            text,
            normalize=False,
            default_lang=None,
            parse_yaml_header=True,
        )
    except Exception as exc:
        if strict:
            raise SSMDParseError(f"[SSMD] malformed markup: {exc}") from exc
        return ParsedMarkup(text, text, warnings=(f"[SSMD] malformed markup: {exc}",))

    warnings = tuple(f"[SSMD] {warning}" for warning in parsed.warnings)
    if warnings and strict:
        raise SSMDParseError("; ".join(warnings))

    semantic: list[SemanticSpan] = []
    languages: list[LanguageSpan] = []
    protected: list[ProtectedSpan] = []
    for annotation in parsed.annotations:
        attrs = {str(key): str(value) for key, value in annotation.attrs.items()}
        start = int(annotation.char_start)
        end = int(annotation.char_end)
        kind = str(attrs.get("tag") or annotation.kind)
        is_protected = any(key in attrs for key in ("ph", "literal", "say-as", "sub"))
        semantic.append(
            SemanticSpan(
                start=start,
                end=end,
                kind=kind,
                attributes=attrs,
                source="ssmd",
                protected=is_protected,
            )
        )
        if "lang" in attrs:
            languages.append(LanguageSpan(start, end, attrs["lang"], source="ssmd"))
        if is_protected:
            protected.append(ProtectedSpan(start, end, kind=kind, source="ssmd"))

    if language and parsed.clean_text and not languages:
        languages.append(LanguageSpan(0, len(parsed.clean_text), language, source="fallback"))

    return ParsedMarkup(
        source_text=text,
        clean_text=str(parsed.clean_text),
        semantic_spans=tuple(semantic),
        language_spans=tuple(languages),
        protected_spans=tuple(protected),
        warnings=warnings,
    )


def render_language_marks(
    text: str,
    spans: tuple[LanguageSpan, ...],
    *,
    include_detected: bool = True,
    include_configured: bool = False,
) -> str:
    """Render selected language spans using the compact SSMD inline syntax."""
    selected = [
        span
        for span in spans
        if (span.source == "detected" and include_detected)
        or (span.source == "configured" and include_configured)
        or span.source in {"ssmd", "caller"}
    ]
    if not selected:
        return text
    merged: list[LanguageSpan] = []
    for span in sorted(selected, key=lambda item: (item.start, item.end)):
        if (
            merged
            and merged[-1].end == span.start
            and merged[-1].language == span.language
            and merged[-1].source == span.source
        ):
            previous = merged[-1]
            merged[-1] = LanguageSpan(
                previous.start,
                span.end,
                span.language,
                source=span.source,
                confidence=span.confidence,
            )
        else:
            merged.append(span)

    output: list[str] = []
    cursor = 0
    for span in merged:
        if span.start < cursor or span.end > len(text):
            continue
        output.append(text[cursor : span.start])
        value = text[span.start : span.end]
        output.append(f'[{value}]{{lang="{escape(span.language, quote=True)}"}}')
        cursor = span.end
    output.append(text[cursor:])
    return "".join(output)


__all__ = ["ParsedMarkup", "SSMDParseError", "parse_markup", "render_language_marks"]
