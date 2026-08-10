"""Comparison, metrics, and local report generation for PolyNorm."""

from __future__ import annotations

import json
import string
import unicodedata
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, median
from typing import Any

from spokenform import PreparedText, prepare

from .polynorm_data import (
    POLYNORM_COMMIT,
    POLYNORM_REPOSITORY,
    POLYNORM_TO_SPOKENFORM,
    PolyNormCase,
)

SEMANTIC_SYMBOLS = frozenset("$€£%@/°+=#&")


def literal_key(text: str) -> str:
    """Normalize only Unicode and whitespace for literal comparison."""
    normalized = unicodedata.normalize("NFC", text).strip()
    return " ".join(normalized.split())


def speech_key(text: str) -> tuple[str, ...]:
    """Tokenize speech while retaining semantically meaningful symbols."""
    characters: list[str] = []
    for character in unicodedata.normalize("NFC", text).casefold():
        if character in SEMANTIC_SYMBOLS:
            characters.append(character)
        elif unicodedata.category(character).startswith("P") or character in string.punctuation:
            characters.append(" ")
        else:
            characters.append(character)
    return tuple(" ".join("".join(characters).split()).split())


def word_error_rate(reference: Iterable[str], hypothesis: Iterable[str]) -> float:
    """Return word-level Levenshtein error rate without a benchmark dependency."""
    reference_words = tuple(reference)
    hypothesis_words = tuple(hypothesis)
    if not reference_words:
        return 0.0 if not hypothesis_words else 1.0
    previous = list(range(len(hypothesis_words) + 1))
    for row, reference_word in enumerate(reference_words, 1):
        current = [row]
        for column, hypothesis_word in enumerate(hypothesis_words, 1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (reference_word != hypothesis_word),
                )
            )
        previous = current
    return previous[-1] / len(reference_words)


def _metric_counts(results: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(results)
    literal_exact_count = sum(bool(item["literal_exact"]) for item in results)
    speech_exact_count = sum(bool(item["speech_exact"]) for item in results)
    unchanged_count = sum(bool(item["unchanged"]) for item in results)
    error_count = sum(bool(item["error"]) for item in results)
    wers = [float(item["speech_wer"]) for item in results if not item["error"]]
    return {
        "cases": count,
        "literal_exact_count": literal_exact_count,
        "literal_exact_rate": literal_exact_count / count if count else 0.0,
        "speech_exact_count": speech_exact_count,
        "speech_exact_rate": speech_exact_count / count if count else 0.0,
        "mean_speech_wer": mean(wers) if wers else 0.0,
        "median_speech_wer": median(wers) if wers else 0.0,
        "unchanged_count": unchanged_count,
        "error_count": error_count,
    }


def evaluate_cases(
    cases: Iterable[PolyNormCase],
    *,
    prepare_fn: Callable[..., PreparedText] = prepare,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Evaluate cases and return metrics plus all inspectable failures."""
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for case in cases:
        language = POLYNORM_TO_SPOKENFORM[case.polynorm_locale]
        error: str | None = None
        actual = ""
        warnings: list[str] = []
        try:
            result = prepare_fn(case.original_text, language=language, use_spacy=False)
            actual = result.spoken_text
            warnings = list(result.warnings)
        except Exception as exc:  # benchmark discovery must continue per case
            error = f"{type(exc).__name__}: {exc}"
        literal_exact = not error and literal_key(actual) == literal_key(case.normalized_text)
        speech_exact = not error and speech_key(actual) == speech_key(case.normalized_text)
        speech_wer = (
            word_error_rate(speech_key(case.normalized_text), speech_key(actual)) if not error else 0.0
        )
        row = {
            "id": case.case_id,
            "polynorm_locale": case.polynorm_locale,
            "spokenform_language": language,
            "index": case.index,
            "category": case.category,
            "literal_exact": literal_exact,
            "speech_exact": speech_exact,
            "speech_wer": speech_wer,
            "unchanged": actual == case.original_text if not error else False,
            "error": error,
        }
        rows.append(row)
        if error or not literal_exact or not speech_exact:
            failures.append(
                {
                    **row,
                    "original_text": case.original_text,
                    "expected": case.normalized_text,
                    "actual": actual,
                    "warnings": warnings,
                }
            )

    grouped_locale: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_category: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_locale[row["polynorm_locale"]].append(row)
        grouped_category[row["category"]].append(row)
    summary = {
        **_metric_counts(rows),
        "by_locale": {key: _metric_counts(value) for key, value in sorted(grouped_locale.items())},
        "by_category": {
            key: _metric_counts(value) for key, value in sorted(grouped_category.items())
        },
    }
    return summary, tuple(failures)


def _run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _write_failures_markdown(failures: tuple[dict[str, Any], ...], path: Path) -> None:
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for failure in failures:
        grouped[failure["polynorm_locale"]][failure["category"]].append(failure)
    lines = ["# PolyNorm failures", ""]
    for locale, categories in sorted(grouped.items()):
        lines.extend([f"## {locale}", ""])
        for category, category_failures in sorted(categories.items()):
            lines.extend([f"### {category}", ""])
            for failure in category_failures:
                lines.extend(
                    [
                        f"#### {failure['id']}",
                        f"- Original: `{failure['original_text']}`",
                        f"- Expected: `{failure['expected']}`",
                        f"- Actual: `{failure['actual']}`",
                        f"- Speech WER: `{failure['speech_wer']:.4f}`",
                        f"- Error: `{failure['error']}`" if failure["error"] else "- Error: none",
                        "",
                    ]
                )
    path.write_text("\n".join(lines), encoding="utf-8")


def evaluate_and_write(
    cases: Iterable[PolyNormCase],
    *,
    output_root: Path | str = "benchmark-results/polynorm",
) -> tuple[Path, dict[str, Any]]:
    """Evaluate cases and write metrics plus local text-bearing failure reports."""
    case_list = tuple(cases)
    summary, failures = evaluate_cases(case_list)
    output_dir = Path(output_root) / _run_id()
    output_dir.mkdir(parents=True, exist_ok=False)
    summary_payload = {
        "benchmark": "PolyNorm-Bench",
        "repository": POLYNORM_REPOSITORY,
        "commit": POLYNORM_COMMIT,
        "generated_at": datetime.now(UTC).isoformat(),
        "locales": sorted({case.polynorm_locale for case in case_list}),
        "spokenform_languages": sorted(
            {POLYNORM_TO_SPOKENFORM[case.polynorm_locale] for case in case_list}
        ),
        **summary,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output_dir / "failures.jsonl").open("w", encoding="utf-8") as handle:
        for failure in failures:
            handle.write(json.dumps(failure, ensure_ascii=False, sort_keys=True) + "\n")
    _write_failures_markdown(failures, output_dir / "failures.md")
    return output_dir, summary_payload


__all__ = [
    "SEMANTIC_SYMBOLS",
    "evaluate_and_write",
    "evaluate_cases",
    "literal_key",
    "speech_key",
    "word_error_rate",
]
