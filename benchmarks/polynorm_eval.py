"""Comparison, metrics, and local report generation for PolyNorm."""

from __future__ import annotations

import json
import platform
import re
import string
import sys
import unicodedata
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from statistics import mean, median
from typing import Any

from spokenform import PreparedText, prepare

from .polynorm_data import (
    POLYNORM_COMMIT,
    POLYNORM_DATASET_COMMIT,
    POLYNORM_REPOSITORY,
    POLYNORM_TO_SPOKENFORM,
    PolyNormCase,
)

SEMANTIC_SYMBOLS = frozenset("$€£%@/°+=#&")

# Reporting aliases intentionally do not alter the upstream category stored on
# each case.  PolyNorm has changed capitalization and pluralization between
# category files, which otherwise makes aggregate reports misleading.
_CATEGORY_ALIASES = {
    "currency": "Currency",
    "currencies": "Currency",
    "phone number": "Phone Number",
    "phone numbers": "Phone Number",
    "mathematical expression": "Mathematical Expression",
    "mathematical expressions": "Mathematical Expression",
    "unit": "Unit",
    "units": "Unit",
    "sports score": "Sports Score",
    "sports scores": "Sports Score",
}

# These are local annotations about benchmark quality/ownership.  They are
# deliberately separate from the upstream corpus and never rewrite its text.
POLYNORM_QUARANTINE: dict[str, dict[str, str]] = {
    "es-MX:86": {"reason": "Expected decimal spelling is inconsistent.", "classification": "questionable"},
    "es-MX:249": {"reason": "Expected text is unrelated to the source e-mail.", "classification": "malformed_ground_truth"},
    "es-MX:274": {"reason": "Expected hashtag marker contains a likely spelling error.", "classification": "questionable"},
    "fr-FR:208": {"reason": "Source contains alternatives/commentary rather than one normalization pair.", "classification": "malformed_ground_truth"},
    "fr-FR:310": {"reason": "Expected text is an instruction rather than normalized source text.", "classification": "malformed_ground_truth"},
    "fr-FR:316": {"reason": "Expected text is an instruction rather than normalized source text.", "classification": "malformed_ground_truth"},
    "de-DE:161": {"reason": "Expected text uses an inconsistent English punctuation word.", "classification": "questionable"},
    "de-DE:412": {"reason": "Expected coordinate appears to omit the hundred component.", "classification": "questionable"},
}

_OWNERSHIP: dict[str, str] = {
    "URL or Email": "protected",
    "Version Numbers": "protected",
    "Roman Numeral": "downstream",
    "Stock Ticker": "downstream",
    "Chemical Formula": "extended-candidate",
    "Hashtag or Mention": "extended-candidate",
    "Phone Number": "extended-candidate",
    "License Plate or Serial Numbers": "extended-candidate",
    "Vehicle or Product Code": "extended-candidate",
    "ISBN": "extended-candidate",
    "Geographic Coordinates": "extended-candidate",
    "Cardinal": "owned",
    "Decimal": "owned",
    "Date": "owned",
    "Time": "owned",
    "Ordinal": "owned",
    "Currency": "owned",
    "Unit": "owned",
    "Address": "extended-candidate",
    "Sports Score": "extended-candidate",
    "Legal Reference": "extended-candidate",
}


def literal_key(text: str) -> str:
    """Normalize only Unicode and whitespace for literal comparison."""
    normalized = unicodedata.normalize("NFC", text).strip()
    return " ".join(normalized.split())


def canonical_category(category: str) -> str:
    """Return a stable reporting label while preserving source categories."""
    return _CATEGORY_ALIASES.get(category.strip().casefold(), category.strip())


def ownership_state(category: str) -> str:
    """Classify a category for diagnostic reporting, not release gating."""
    return _OWNERSHIP.get(canonical_category(category), "unsupported")


def residual_symbols(text: str) -> dict[str, int]:
    """Count source-like symbols left in generated speech for diagnosis."""
    return {
        "digits": sum(character.isdigit() for character in text),
        "hash": text.count("#"),
        "at": text.count("@"),
        "degree": text.count("°"),
        "slash": text.count("/"),
        "multi_dot": len(re.findall(r"\.{2,}", text)),
        "unicode_fraction": len(re.findall(r"[¼½¾⅓⅔⅛⅜⅝⅞]", text)),
        "superscript_subscript": len(re.findall(r"[⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉]", text)),
        "url_or_email": len(re.findall(r"https?://\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)),
    }


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not-installed"


def environment_fingerprint(locales: Iterable[str]) -> dict[str, object]:
    """Return reproducibility metadata for one benchmark configuration."""
    from spokenform.language import resolve_abbr2words_language, resolve_num2words_language

    resolution = {
        locale: {
            "spokenform": POLYNORM_TO_SPOKENFORM[locale],
            "num2words": resolve_num2words_language(POLYNORM_TO_SPOKENFORM[locale]),
            "abbr2words": resolve_abbr2words_language(POLYNORM_TO_SPOKENFORM[locale]),
        }
        for locale in sorted(set(locales))
    }
    return {
        "dataset_repository": POLYNORM_REPOSITORY,
        "dataset_commit": POLYNORM_DATASET_COMMIT,
        "spokenform_version": _package_version("spokenform"),
        "spokenform_source_commit": None,
        "abbr2words_version": _package_version("abbr2words"),
        "num2words_version": _package_version("num2words"),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "locale_mapping": resolution,
        "configuration": {
            "prepare": {"use_spacy": False},
            "semantic_symbols": "".join(sorted(SEMANTIC_SYMBOLS)),
        },
    }


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


def _residual_symbol_counts(results: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Aggregate source-like symbols left in generated speech."""
    totals: defaultdict[str, int] = defaultdict(int)
    for row in results:
        for symbol, count in row.get("residual_symbols", {}).items():
            totals[symbol] += int(count)
    return dict(sorted(totals.items()))


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
        quarantine = POLYNORM_QUARANTINE.get(case.case_id)
        canonical = canonical_category(case.category)
        ownership = ownership_state(case.category)
        error: str | None = None
        actual = ""
        warnings: list[str] = []
        changed_stages: tuple[str, ...] = ()
        source_rules: tuple[str, ...] = ()
        structured_claimed = False
        try:
            result = prepare_fn(case.original_text, language=language, use_spacy=False)
            actual = result.spoken_text
            warnings = list(result.warnings)
            changed_stages = tuple(stage.name for stage in result.stages if stage.changed)
            source_rules = tuple(
                sorted({edit.rule for edit in result.mapped_edits if edit.rule})
            )
            structured_claimed = any(edit.stage == "structured" for edit in result.mapped_edits)
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
            "canonical_category": canonical,
            "ownership": ownership,
            "quarantine": quarantine,
            "literal_exact": literal_exact,
            "speech_exact": speech_exact,
            "speech_wer": speech_wer,
            "unchanged": actual == case.original_text if not error else False,
            "error": error,
            "residual_symbols": residual_symbols(actual),
            "changed_stages": changed_stages,
            "source_rules": source_rules,
            "structured_claimed": structured_claimed,
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
    grouped_ownership: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_locale_category: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        grouped_locale[row["polynorm_locale"]].append(row)
        grouped_category[row["canonical_category"]].append(row)
        grouped_ownership[row["ownership"]].append(row)
        grouped_locale_category[row["polynorm_locale"]][row["canonical_category"]].append(row)
    reviewed_rows = [row for row in rows if row["quarantine"] is None]
    summary = {
        **_metric_counts(rows),
        "by_locale": {key: _metric_counts(value) for key, value in sorted(grouped_locale.items())},
        "by_category": {
            key: _metric_counts(value) for key, value in sorted(grouped_category.items())
        },
        "by_canonical_category": {
            key: _metric_counts(value) for key, value in sorted(grouped_category.items())
        },
        "by_ownership": {
            key: _metric_counts(value) for key, value in sorted(grouped_ownership.items())
        },
        "by_locale_category": {
            locale: {
                category: _metric_counts(category_rows)
                for category, category_rows in sorted(categories.items())
            }
            for locale, categories in sorted(grouped_locale_category.items())
        },
        "residual_symbols": _residual_symbol_counts(rows),
        "residual_symbols_by_category": {
            category: _residual_symbol_counts(category_rows)
            for category, category_rows in sorted(grouped_category.items())
        },
        "reviewed": _metric_counts(reviewed_rows),
        "quarantine_count": len(rows) - len(reviewed_rows),
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
        "dataset_commit": POLYNORM_DATASET_COMMIT,
        "commit": POLYNORM_COMMIT,
        "generated_at": datetime.now(UTC).isoformat(),
        "locales": sorted({case.polynorm_locale for case in case_list}),
        "spokenform_languages": sorted(
            {POLYNORM_TO_SPOKENFORM[case.polynorm_locale] for case in case_list}
        ),
        "environment": environment_fingerprint(case.polynorm_locale for case in case_list),
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
