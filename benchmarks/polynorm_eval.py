"""Comparison, metrics, and local report generation for PolyNorm."""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from statistics import mean, median
from typing import Any, Literal

from spokenform import PreparedText, prepare
from spokenform.numeric_lexeme import numeric_speech_policy

from .compare_common import with_configuration_hash
from .failure_reporting import (
    diagnostic_aggregates,
    failure_family,
    failure_family_counts,
    outcome_for_row,
)
from .polynorm_data import (
    POLYNORM_COMMIT,
    POLYNORM_DATASET_COMMIT,
    POLYNORM_REPOSITORY,
    POLYNORM_TO_SPOKENFORM,
    PolyNormCase,
)
from .text_metrics import literal_key, speech_key, speech_key_equivalent, word_error_rate

SEMANTIC_SYMBOLS = frozenset("$€£%@/°+=#&")
BENCHMARK_PROFILES = ("default", "extended")
LiteralProfile = Literal["default", "extended"]

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
    "es-MX:86": {
        "reason": "Expected decimal spelling is inconsistent.",
        "classification": "questionable",
        "reason_code": "questionable-target",
    },
    "es-MX:249": {
        "reason": "Expected text is unrelated to the source e-mail.",
        "classification": "malformed_ground_truth",
        "reason_code": "malformed-ground-truth",
    },
    "es-MX:274": {
        "reason": "Expected hashtag marker contains a likely spelling error.",
        "classification": "questionable",
        "reason_code": "questionable-target",
    },
    "fr-FR:208": {
        "reason": "Source contains alternatives/commentary rather than one normalization pair.",
        "classification": "malformed_ground_truth",
        "reason_code": "malformed-ground-truth",
    },
    "fr-FR:310": {
        "reason": "Expected text is an instruction rather than normalized source text.",
        "classification": "malformed_ground_truth",
        "reason_code": "malformed-ground-truth",
    },
    "fr-FR:316": {
        "reason": "Expected text is an instruction rather than normalized source text.",
        "classification": "malformed_ground_truth",
        "reason_code": "malformed-ground-truth",
    },
    "de-DE:161": {
        "reason": "Expected text uses an inconsistent English punctuation word.",
        "classification": "questionable",
        "reason_code": "questionable-target",
    },
    "de-DE:412": {
        "reason": "Expected coordinate appears to omit the hundred component.",
        "classification": "questionable",
        "reason_code": "questionable-target",
    },
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
        "unicode_fraction": len(re.findall(r"[¼½¾⅓⅔⅛⅜⅝⅞⅕⅖⅗⅘⅙⅚]", text)),
        "superscript_subscript": len(re.findall(r"[⁰¹²³⁴⁵⁶⁷⁸⁹₀₁₂₃₄₅₆₇₈₉]", text)),
        "url_or_email": len(re.findall(r"https?://\S+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text)),
    }


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not-installed"


def source_commit() -> str | None:
    """Return the checked-out source commit when this run comes from Git."""
    repository = Path(__file__).resolve().parent.parent
    try:
        result = subprocess.run(
            ("git", "-C", str(repository), "rev-parse", "HEAD"),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    commit = result.stdout.strip()
    return commit or None


def environment_fingerprint(
    locales: Iterable[str], *, profile: LiteralProfile = "default"
) -> dict[str, object]:
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
    return with_configuration_hash(
        {
            "dataset_repository": POLYNORM_REPOSITORY,
            "dataset_commit": POLYNORM_DATASET_COMMIT,
            "spokenform_version": _package_version("spokenform"),
            "spokenform_source_commit": source_commit(),
            "abbr2words_version": _package_version("abbr2words"),
            "num2words_version": _package_version("num2words"),
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "locale_mapping": resolution,
            "configuration": {
                "prepare": {"use_spacy": False, "normalize_literals": profile == "extended"},
                "profile": profile,
                "acronym_policy": {
                    "generic_mode": "conservative_unknown"
                    if profile == "extended"
                    else "known_only",
                    "generic_case": "upper",
                    "registered_mode": "spell" if profile == "extended" else "expand",
                },
                "semantic_symbols": "".join(sorted(SEMANTIC_SYMBOLS)),
            },
        }
    )


def _metric_counts(results: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(results)
    literal_exact_count = sum(bool(item["literal_exact"]) for item in results)
    speech_exact_count = sum(bool(item["speech_exact"]) for item in results)
    equivalent_count = sum(
        bool(item.get("speech_exact_equivalent", item["speech_exact"])) for item in results
    )
    presentation_only_count = sum(bool(item.get("presentation_only")) for item in results)
    semantic_failure_count = sum(bool(item.get("semantic_failure")) for item in results)
    unchanged_count = sum(bool(item["unchanged"]) for item in results)
    error_count = sum(bool(item["error"]) for item in results)
    wers = [float(item["speech_wer"]) for item in results if not item["error"]]
    return {
        "cases": count,
        "literal_exact_count": literal_exact_count,
        "literal_exact_rate": literal_exact_count / count if count else 0.0,
        "speech_exact_count": speech_exact_count,
        "speech_exact_rate": speech_exact_count / count if count else 0.0,
        "speech_exact_equivalent_count": equivalent_count,
        "speech_exact_equivalent_rate": equivalent_count / count if count else 0.0,
        "presentation_only_count": presentation_only_count,
        "semantic_failure_count": semantic_failure_count,
        "mean_speech_wer": mean(wers) if wers else 0.0,
        "median_speech_wer": median(wers) if wers else 0.0,
        "unchanged_count": unchanged_count,
        "error_count": error_count,
        "failure_family_count": len(failure_family_counts(results)),
    }


def _residual_symbol_counts(results: Iterable[dict[str, Any]]) -> dict[str, int]:
    """Aggregate source-like symbols left in generated speech."""
    totals: defaultdict[str, int] = defaultdict(int)
    for row in results:
        for symbol, count in row.get("residual_symbols", {}).items():
            totals[symbol] += int(count)
    return dict(sorted(totals.items()))


def _provenance_diagnostics(result: Any, *, ownership: str, language: str) -> dict[str, Any]:
    """Extract stable claim/provenance fields for benchmark triage."""
    mapped_edits = tuple(getattr(result, "mapped_edits", ()) or ())
    source_replacements = tuple(getattr(result, "source_replacements", ()) or ())
    candidates = [
        edit for edit in (*source_replacements, *mapped_edits) if getattr(edit, "rule", None)
    ]
    candidates.sort(
        key=lambda edit: (
            -int(getattr(edit, "source_end", 0)) + int(getattr(edit, "source_start", 0)),
            int(getattr(edit, "source_start", 0)),
        )
    )
    winner = candidates[0] if candidates else None
    primary_rule = getattr(winner, "rule", None) if winner is not None else None
    if winner is None:
        winning_span = None
    else:
        winning_span = {
            "start": int(getattr(winner, "source_start", 0)),
            "end": int(getattr(winner, "source_end", 0)),
            "source": str(getattr(winner, "source", "")),
            "rule": primary_rule,
        }

    protected_spans = tuple(getattr(result, "protected_spans", ()) or ())
    protected_mutation = any(
        int(getattr(edit, "source_start", 0)) < int(getattr(span, "end", 0))
        and int(getattr(span, "start", 0)) < int(getattr(edit, "source_end", 0))
        for edit in source_replacements
        for span in protected_spans
    )
    protected_reasons = tuple(
        dict.fromkeys(
            str(getattr(span, "kind", "literal"))
            for span in protected_spans
            if getattr(span, "kind", None)
        )
    )
    if protected_reasons:
        protected_reason = ", ".join(protected_reasons)
    elif ownership == "protected":
        protected_reason = "benchmark protected ownership"
    else:
        protected_reason = None

    rules = [str(getattr(edit, "rule", "")) for edit in mapped_edits if getattr(edit, "rule", None)]
    if ownership == "protected" and protected_spans:
        failure_phase = "protected"
    elif primary_rule is None:
        failure_phase = "unrecognized"
    elif any(getattr(edit, "stage", None) == "numbers" for edit in mapped_edits):
        failure_phase = "locale_rendering"
    elif any(getattr(edit, "stage", None) == "structured" for edit in mapped_edits):
        failure_phase = "structured_rendering"
    else:
        failure_phase = "downstream_rendering"

    diagnostics = {
        "primary_rule": primary_rule,
        "claim_owner": ownership
        if primary_rule
        else ("protection" if protected_spans else "unclaimed"),
        "failure_phase": failure_phase,
        "winning_span": winning_span,
        "protected_reason": protected_reason,
        "protected_mutation": protected_mutation,
        "numeric_policy": asdict(numeric_speech_policy(language)),
        "render_mode": _render_mode_for_rule(primary_rule, rules),
    }
    if primary_rule == "sequence.version":
        diagnostics.update({"separator": ".", "separator_role": "version"})
    return diagnostics


def _render_mode_for_rule(primary_rule: str | None, rules: Iterable[str]) -> str:
    """Map implementation provenance to a compact benchmark render mode."""
    haystack = " ".join(rule.casefold() for rule in rules)
    for marker, mode in (
        ("isbn", "digit_sequence"),
        ("phone", "digit_sequence"),
        ("mac", "digit_sequence"),
        ("ipv4", "digit_sequence"),
        ("serial", "digit_sequence"),
        ("plate", "digit_sequence"),
        ("vin", "digit_sequence"),
        ("product", "typed_code"),
        ("address", "address"),
        ("coordinate", "coordinate"),
        ("legal", "legal_reference"),
        ("sports", "sports_score"),
        ("hashtag", "literal_payload"),
        ("mention", "literal_payload"),
        ("roman", "roman"),
        ("math", "mathematical_expression"),
        ("music", "musical_notation"),
    ):
        if marker in haystack:
            return mode
    if primary_rule and ".quantity" in primary_rule:
        return "quantity"
    if primary_rule and "currency" in primary_rule:
        return "currency"
    if primary_rule and "date" in primary_rule:
        return "date"
    if primary_rule and "time" in primary_rule:
        return "time"
    if primary_rule and "ordinal" in primary_rule:
        return "ordinal"
    if primary_rule:
        return "cardinal"
    return "unchanged"


def _gate_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Return separate safety, ownership, and locale benchmark views."""
    grouped_ownership: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_locale: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped_ownership[row["ownership"]].append(row)
        grouped_locale[row["polynorm_locale"]].append(row)
    protected = grouped_ownership.get("protected", [])
    safety = {
        "protected_cases": len(protected),
        "protected_mutation_count": sum(bool(row.get("protected_mutation")) for row in protected),
        "protected_unchanged_rate": (
            1.0 - sum(bool(row.get("protected_mutation")) for row in protected) / len(protected)
            if protected
            else 0.0
        ),
        "error_count": sum(bool(row["error"]) for row in rows),
    }
    return {
        "safety": safety,
        "owned": _metric_counts(grouped_ownership.get("owned", [])),
        "extended": _metric_counts(grouped_ownership.get("extended-candidate", [])),
        "protected": _metric_counts(protected),
        "downstream": _metric_counts(grouped_ownership.get("downstream", [])),
        "unsupported": _metric_counts(grouped_ownership.get("unsupported", [])),
        "quarantine": _metric_counts([row for row in rows if row.get("quarantine") is not None]),
        "locale": {
            locale: _metric_counts(locale_rows)
            for locale, locale_rows in sorted(grouped_locale.items())
        },
    }


def evaluate_cases(
    cases: Iterable[PolyNormCase],
    *,
    prepare_fn: Callable[..., PreparedText] = prepare,
    profile: LiteralProfile = "default",
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
        result: PreparedText | Any = None
        try:
            kwargs: dict[str, object] = {"language": language, "use_spacy": False}
            if profile == "extended":
                kwargs.update(
                    {
                        "normalize_literals": True,
                        "generic_acronym_mode": "conservative_unknown",
                        "generic_acronym_case": "upper",
                        "registered_acronym_mode": "spell",
                    }
                )
            result = prepare_fn(case.original_text, **kwargs)
            actual = result.spoken_text
            warnings = list(result.warnings)
            changed_stages = tuple(stage.name for stage in result.stages if stage.changed)
            source_rules = tuple(sorted({edit.rule for edit in result.mapped_edits if edit.rule}))
            structured_claimed = any(edit.stage == "structured" for edit in result.mapped_edits)
        except Exception as exc:  # benchmark discovery must continue per case
            error = f"{type(exc).__name__}: {exc}"
        literal_exact = not error and literal_key(actual) == literal_key(case.normalized_text)
        speech_exact = not error and speech_key(actual) == speech_key(case.normalized_text)
        equivalent_actual = speech_key_equivalent(actual, language=language)
        equivalent_expected = speech_key_equivalent(case.normalized_text, language=language)
        speech_exact_equivalent = not error and equivalent_actual == equivalent_expected
        presentation_only = bool(not error and not speech_exact and speech_exact_equivalent)
        semantic_failure = bool(not error and not speech_exact_equivalent)
        speech_wer = (
            word_error_rate(speech_key(case.normalized_text), speech_key(actual))
            if not error
            else 0.0
        )
        provenance = _provenance_diagnostics(result, ownership=ownership, language=language)
        if error:
            provenance["failure_phase"] = "parse_error"
        row = {
            "id": case.case_id,
            "polynorm_locale": case.polynorm_locale,
            "spokenform_language": language,
            "index": case.index,
            "category": case.category,
            "canonical_category": canonical,
            "ownership": ownership,
            "quarantine": quarantine,
            "profile": profile,
            "original_text": case.original_text,
            "expected": case.normalized_text,
            "actual": actual,
            "literal_exact": literal_exact,
            "speech_exact": speech_exact,
            "speech_exact_raw": speech_exact,
            "speech_exact_equivalent": speech_exact_equivalent,
            "presentation_only": presentation_only,
            "semantic_failure": semantic_failure,
            "speech_wer": speech_wer,
            "unchanged": actual == case.original_text if not error else False,
            "error": error,
            "residual_symbols": residual_symbols(actual),
            "changed_stages": changed_stages,
            "source_rules": source_rules,
            "structured_claimed": structured_claimed,
            **provenance,
        }
        row["quarantine_reason_code"] = quarantine.get("reason_code") if quarantine else None
        row["outcome"] = outcome_for_row(row)
        row["failure_family"] = failure_family(row)
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
        "quarantine_reason_codes": {
            code: sum(row.get("quarantine_reason_code") == code for row in rows)
            for code in sorted(
                {row["quarantine_reason_code"] for row in rows if row["quarantine_reason_code"]}
            )
        },
        "failure_families": failure_family_counts(rows),
        "diagnostic_aggregates": diagnostic_aggregates(rows),
        "gate_metrics": _gate_metrics(rows),
        "profile": profile,
        "normalize_literals": profile == "extended",
    }
    summary["_rows"] = tuple(rows)
    return summary, tuple(failures)


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


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


def _filter_failures_by_speech_wer(
    failures: Iterable[dict[str, Any]], threshold: float | None
) -> tuple[dict[str, Any], ...]:
    """Select persisted failures without changing complete-run evaluation metrics."""
    values = tuple(failures)
    if threshold is None:
        return values
    return tuple(failure for failure in values if float(failure["speech_wer"]) > threshold)


def evaluate_and_write(
    cases: Iterable[PolyNormCase],
    *,
    output_root: Path | str = "benchmark-results/polynorm",
    speech_wer_threshold: float | None = None,
    profile: LiteralProfile = "default",
) -> tuple[Path, dict[str, Any]]:
    """Evaluate cases and write metrics plus local text-bearing failure reports."""
    case_list = tuple(cases)
    summary, failures = (
        evaluate_cases(case_list, profile=profile)
        if profile == "extended"
        else evaluate_cases(case_list)
    )
    all_rows = summary.pop("_rows", ())
    stored_failures = _filter_failures_by_speech_wer(failures, speech_wer_threshold)
    output_dir = Path(output_root) / _run_id()
    output_dir.mkdir(parents=True, exist_ok=False)
    environment = environment_fingerprint(
        (case.polynorm_locale for case in case_list), profile=profile
    )
    summary_payload = {
        "benchmark": "PolyNorm-Bench",
        "repository": POLYNORM_REPOSITORY,
        "dataset_commit": POLYNORM_DATASET_COMMIT,
        "commit": POLYNORM_COMMIT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "locales": sorted({case.polynorm_locale for case in case_list}),
        "spokenform_languages": sorted(
            {POLYNORM_TO_SPOKENFORM[case.polynorm_locale] for case in case_list}
        ),
        "environment": environment,
        "identity": {
            "benchmark": "PolyNorm-Bench",
            "dataset_commit": POLYNORM_DATASET_COMMIT,
            "spokenform_source_commit": environment["spokenform_source_commit"],
            "abbr2words_version": environment["abbr2words_version"],
            "num2words_version": environment["num2words_version"],
            "profile": profile,
            "config_hash": environment["config_hash"],
            "locale_mapping": environment["locale_mapping"],
        },
        "profile": profile,
        "normalize_literals": profile == "extended",
        "speech_wer_threshold": speech_wer_threshold,
        "stored_failure_count": len(stored_failures),
        **summary,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (output_dir / "failures.jsonl").open("w", encoding="utf-8") as handle:
        for failure in stored_failures:
            handle.write(json.dumps(failure, ensure_ascii=False, sort_keys=True) + "\n")
    with (output_dir / "rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in all_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    _write_failures_markdown(stored_failures, output_dir / "failures.md")
    return output_dir, summary_payload


__all__ = [
    "SEMANTIC_SYMBOLS",
    "BENCHMARK_PROFILES",
    "evaluate_and_write",
    "evaluate_cases",
    "literal_key",
    "speech_key",
    "speech_key_equivalent",
    "word_error_rate",
]
