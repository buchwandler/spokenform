"""Bounded, documented renderer alternatives for diagnostic use only."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from num2words import num2words

from .text_metrics import speech_key, speech_key_equivalent, word_error_rate

_TIME_RE = re.compile(r"(?<!\w)(?P<hour>\d{1,2}):(?P<minute>\d{2})(?!\w)")


@dataclass(frozen=True, slots=True)
class RenderAlternative:
    """One allowed family-specific rendering mode."""

    mode: str
    text: str


@dataclass(frozen=True, slots=True)
class RenderingOracleAnalysis:
    """Per-row bounded renderer evidence."""

    enabled: bool
    scorable: bool
    family: str | None
    baseline_mode: str | None
    best_mode: str | None
    renderer_regret: float
    speech_equivalent: bool
    reason: str | None = None


def _cardinal(value: int) -> str:
    return str(num2words(value, lang="en")).replace("-", " ").replace(" and ", " ")


def time_render_alternatives(hour: int, minute: int) -> tuple[RenderAlternative, ...]:
    """Return the documented bounded alternatives for one clock time."""
    minute_digits = f"{minute:02d}"
    digits = f"{_cardinal(hour)} " + " ".join(_cardinal(int(digit)) for digit in minute_digits)
    oh_digits = f"{_cardinal(hour)} " + " ".join(
        "oh" if digit == "0" else _cardinal(int(digit)) for digit in minute_digits
    )
    hundred = _cardinal(hour * 100 + minute)
    return (
        RenderAlternative("digits", digits),
        RenderAlternative("oh-digits", oh_digits),
        RenderAlternative("military/hundred", hundred),
        RenderAlternative("military/hundred-hours", f"{hundred} hours"),
    )


def documented_render_alternatives(
    source: str, *, family: str, language: str = "en"
) -> tuple[RenderAlternative, ...]:
    """Build alternatives only from parsed source semantics and fixed modes."""
    if language.casefold().split("-", 1)[0] == "en" and family == "time":
        match = _TIME_RE.search(source)
        if match is not None:
            return time_render_alternatives(int(match["hour"]), int(match["minute"]))
    return ()


def analyze_renderer_oracle(
    baseline_text: str,
    expected: str,
    *,
    language: str,
    family: str | None,
    baseline_mode: str | None,
    alternatives: tuple[RenderAlternative, ...],
) -> RenderingOracleAnalysis:
    """Score only caller-supplied documented alternatives."""
    if not alternatives:
        return RenderingOracleAnalysis(
            enabled=True,
            scorable=False,
            family=family,
            baseline_mode=baseline_mode,
            best_mode=None,
            renderer_regret=0.0,
            speech_equivalent=False,
            reason="no-supported-family",
        )
    baseline_wer = word_error_rate(speech_key(expected), speech_key(baseline_text))
    scored = [
        (
            speech_key_equivalent(alternative.text, language=language)
            == speech_key_equivalent(expected, language=language),
            word_error_rate(speech_key(expected), speech_key(alternative.text)),
            alternative.mode,
        )
        for alternative in alternatives
    ]
    best_equivalent, best_wer, best_mode = min(
        scored,
        key=lambda item: (not item[0], item[1], item[2] != baseline_mode, item[2]),
    )
    return RenderingOracleAnalysis(
        enabled=True,
        scorable=True,
        family=family,
        baseline_mode=baseline_mode,
        best_mode=best_mode,
        renderer_regret=max(0.0, baseline_wer - best_wer),
        speech_equivalent=best_equivalent,
    )


def analysis_fields(analysis: RenderingOracleAnalysis) -> dict[str, Any]:
    return {
        "renderer_oracle_enabled": analysis.enabled,
        "renderer_oracle_scorable": analysis.scorable,
        "renderer_family": analysis.family,
        "baseline_render_mode": analysis.baseline_mode,
        "best_render_mode": analysis.best_mode,
        "renderer_regret": analysis.renderer_regret,
        "renderer_oracle_speech_equivalent": analysis.speech_equivalent,
        "renderer_oracle_reason": analysis.reason,
    }


def oracle_aggregates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    enabled = [row for row in rows if row.get("renderer_oracle_enabled")]
    scorable = [row for row in enabled if row.get("renderer_oracle_scorable")]
    return {
        "schema_version": 1,
        "enabled": bool(enabled),
        "cases": len(enabled),
        "scorable_cases": len(scorable),
        "family_counts": dict(
            sorted(Counter(str(row.get("renderer_family")) for row in scorable).items())
        ),
        "best_mode_counts": dict(
            sorted(Counter(str(row.get("best_render_mode")) for row in scorable).items())
        ),
        "renderer_regret_sum": sum(float(row.get("renderer_regret", 0.0)) for row in scorable),
    }


__all__ = [
    "RenderAlternative",
    "RenderingOracleAnalysis",
    "analysis_fields",
    "analyze_renderer_oracle",
    "documented_render_alternatives",
    "oracle_aggregates",
    "source_render_fields",
    "time_render_alternatives",
]


def source_render_fields(
    source: str,
    baseline_text: str,
    expected: str,
    *,
    language: str,
    family: str | None,
    baseline_mode: str | None,
    replacements: tuple[Any, ...] = (),
) -> dict[str, Any]:
    """Build full-text alternatives from source-aligned semantic replacements."""
    alternatives = documented_render_alternatives(source, family=family or "", language=language)
    if not alternatives:
        return analysis_fields(
            analyze_renderer_oracle(
                baseline_text,
                expected,
                language=language,
                family=family,
                baseline_mode=baseline_mode,
                alternatives=(),
            )
        )
    output_span = next(
        (
            (int(item.output_start), int(item.output_end))
            for item in replacements
            if ".time" in str(getattr(item, "rule", ""))
        ),
        None,
    )
    if output_span is None:
        return analysis_fields(
            analyze_renderer_oracle(
                baseline_text,
                expected,
                language=language,
                family=family,
                baseline_mode=baseline_mode,
                alternatives=(),
            )
        )
    start, end = output_span
    full_alternatives = tuple(
        RenderAlternative(
            alternative.mode,
            baseline_text[:start] + alternative.text + baseline_text[end:],
        )
        for alternative in alternatives
    )
    return analysis_fields(
        analyze_renderer_oracle(
            baseline_text,
            expected,
            language=language,
            family=family,
            baseline_mode=baseline_mode,
            alternatives=full_alternatives,
        )
    )
