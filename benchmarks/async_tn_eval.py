"""Deterministic mapping and evaluation for the Async TN benchmark."""

from __future__ import annotations

import platform
import sys
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any

from spokenform import PreparedText, prepare
from spokenform.mapping import OffsetMap, Replacement, apply_replacements, replacements_from_diff

from .async_tn_data import AsyncTNCase, AsyncTNUnit
from .candidate_oracle import (
    MAX_COMPONENT_PATHS,
    MAX_GLOBAL_COMBINATIONS,
    analyze_candidate_oracle,
)
from .candidate_oracle import (
    analysis_fields as candidate_oracle_fields,
)
from .configuration_oracle import (
    analysis_fields as configuration_oracle_fields,
)
from .configuration_oracle import (
    analyze_configuration_oracle,
)
from .configuration_oracle import (
    oracle_aggregates as configuration_oracle_aggregates,
)
from .failure_reporting import (
    RISK_TIERS,
    diagnostic_aggregates,
    failure_family,
    failure_family_counts,
    oracle_aggregates,
    oracle_gap_type,
    ownership_for_rule,
    rank_provenance,
    risk_tier_for_row,
)
from .text_metrics import literal_key, speech_key, speech_key_equivalent, word_error_rate

BENCHMARK_PROFILES = ("default", "extended")


@dataclass(frozen=True, slots=True)
class ExpectedMapping:
    """A source-to-expected-text map and its diff evidence."""

    source_text: str
    expected_text: str
    offset_map: OffsetMap
    replacements: tuple[Replacement, ...]


@dataclass(frozen=True, slots=True)
class UnitProjection:
    """Text projected from one source unit into a target sentence."""

    text: str
    start: int
    end: int
    ambiguous: bool
    overlapping_replacements: tuple[Any, ...] = ()


def build_expected_mapping(source: str, expected: str) -> ExpectedMapping:
    """Build the deterministic source-to-expected map used for unit scoring."""
    replacements = replacements_from_diff(source, expected, stage="benchmark-target")
    actual, _, offset_map = apply_replacements(source, replacements, stage="benchmark-target")
    if actual != expected:
        raise ValueError("benchmark target mapping did not reproduce expected text")
    return ExpectedMapping(source, expected, offset_map, replacements)


def _overlapping_replacements(
    unit: AsyncTNUnit, replacements: tuple[Replacement, ...]
) -> tuple[Replacement, ...]:
    return tuple(
        replacement
        for replacement in replacements
        if replacement.start < unit.source_end and replacement.end > unit.source_start
    )


def project_unit(mapping: ExpectedMapping, unit: AsyncTNUnit) -> UnitProjection:
    """Project a source unit to expected text and flag cross-boundary edits."""
    start, end = mapping.offset_map.map_source_span(unit.source_start, unit.source_end)
    overlapping = _overlapping_replacements(unit, mapping.replacements)
    ambiguous = any(
        replacement.start < unit.source_start or replacement.end > unit.source_end
        for replacement in overlapping
    )
    return UnitProjection(mapping.expected_text[start:end], start, end, ambiguous, overlapping)


def project_expected_unit(
    case: AsyncTNCase, unit: AsyncTNUnit, mapping: ExpectedMapping | None = None
) -> UnitProjection:
    """Project one case unit through a cached or newly built expected map."""
    selected_mapping = mapping or build_expected_mapping(case.original_text, case.normalized_text)
    return project_unit(selected_mapping, unit)


def project_actual_unit(result: PreparedText, unit: AsyncTNUnit) -> UnitProjection:
    """Project one source unit through a Spokenform ``PreparedText`` result."""
    start, end = result.map_source_span(unit.source_start, unit.source_end)
    replacements = tuple(getattr(result, "source_replacements", ()) or ())
    overlapping = tuple(
        replacement
        for replacement in replacements
        if replacement.source_start < unit.source_end and replacement.source_end > unit.source_start
    )
    ambiguous = any(
        replacement.source_start < unit.source_start or replacement.source_end > unit.source_end
        for replacement in overlapping
    )
    return UnitProjection(result.spoken_text[start:end], start, end, ambiguous, overlapping)


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not-installed"


def _source_rules(edits: Iterable[Any], unit: AsyncTNUnit | None = None) -> tuple[str, ...]:
    rules = {
        str(edit.rule)
        for edit in edits
        if getattr(edit, "rule", None)
        and (
            unit is None
            or (
                int(getattr(edit, "source_start", 0)) < unit.source_end
                and int(getattr(edit, "source_end", 0)) > unit.source_start
            )
        )
    }
    return tuple(sorted(rules))


def _changed_stages(result: PreparedText | None) -> tuple[str, ...]:
    return tuple(stage.name for stage in result.stages if stage.changed) if result else ()


def _category_ownership(category: str, language: str) -> str:
    if language not in {"en", "de", "es", "fr", "it", "pt"}:
        return "external-language"
    if category in {
        "api_token",
        "file_path",
        "ip_address",
        "password_token",
        "promo_code",
        "social_handle",
        "url_or_email",
        "version",
    }:
        return "protected"
    if category in {"abbreviation", "acronym"}:
        return "dependency-abbr2words"
    if category in {
        "cardinal",
        "currency",
        "date",
        "decimal",
        "fraction",
        "measurement_unit",
        "ordinal",
        "quantity",
        "range",
        "score_percent",
        "time",
    }:
        return "owned"
    return "extended-candidate"


def _diagnostics(
    row: dict[str, Any], result: PreparedText | None, *, category: str, language: str
) -> dict[str, Any]:
    edits = tuple(getattr(result, "source_replacements", ()) or ()) if result else ()
    provenance = rank_provenance(
        edits,
        semantic_failure=bool(row.get("semantic_failure")),
        presentation_only=bool(row.get("presentation_only")),
        error=bool(row.get("error")),
        protected_spans=tuple(getattr(result, "protected_spans", ()) or ()) if result else (),
    )
    primary = provenance["primary_rule"]
    ownership = ownership_for_rule(primary)
    if ownership == "unrecognized":
        ownership = _category_ownership(category, language)
    row.update(
        provenance,
        primary_rule=primary,
        ownership=ownership,
        category=category,
        canonical_category=category,
    )
    row["failure_family"] = failure_family(row)
    row["risk_tier"] = risk_tier_for_row(row)
    return row


def _metric_values(actual: str, expected: str, language: str) -> dict[str, Any]:
    return {
        "literal_exact": literal_key(actual) == literal_key(expected),
        "speech_exact": speech_key(actual) == speech_key(expected),
        "speech_equivalent": speech_key_equivalent(actual, language=language)
        == speech_key_equivalent(expected, language=language),
        "speech_wer": word_error_rate(speech_key(expected), speech_key(actual)),
    }


def _candidate_oracle_kwargs(*, normalize_literals: bool) -> dict[str, Any]:
    return {
        "promote_literals": normalize_literals,
        "generic_acronym_mode": "known_only",
        "generic_acronym_case": "upper",
        "max_component_paths": MAX_COMPONENT_PATHS,
        "max_global_combinations": MAX_GLOBAL_COMBINATIONS,
    }


def _oracle_row_fields(
    row: dict[str, Any],
    result: PreparedText | None,
    case: AsyncTNCase,
    *,
    normalize_literals: bool,
) -> dict[str, Any]:
    if row["error"] or result is None:
        fields = {
            "candidate_count": 0,
            "ambiguous_component_count": 0,
            "alternative_path_count": 0,
            "combinations_evaluated": 0,
            "actual_speech_wer": float(row["speech_wer"]),
            "oracle_speech_wer": float(row["speech_wer"]),
            "selector_regret": 0.0,
            "actual_speech_equivalent": bool(row["speech_exact_equivalent"]),
            "oracle_speech_equivalent": bool(row["speech_exact_equivalent"]),
            "oracle_literal_exact": bool(row["literal_exact"]),
            "oracle_rules": [],
            "oracle_spans": [],
            "baseline_structured_rules": [],
            "oracle_changed_rules": [],
            "oracle_scorable": False,
            "oracle_truncated": False,
            "oracle_reason": "runtime-error",
            "oracle_internal_gap_type": "oracle-unscorable",
        }
    else:
        fields = candidate_oracle_fields(
            analyze_candidate_oracle(
                case.original_text,
                case.normalized_text,
                result,
                language=case.spokenform_language,
                **_candidate_oracle_kwargs(normalize_literals=normalize_literals),
            )
        )
    if not row["error"] and result is not None:
        fields.update(
            configuration_oracle_fields(
                analyze_configuration_oracle(
                    case.original_text,
                    case.normalized_text,
                    result,
                    language=case.spokenform_language,
                    base_kwargs={
                        "language": case.spokenform_language,
                        "normalize_literals": normalize_literals,
                    },
                )
            )
        )
    merged = {**row, **fields}
    gap_type = oracle_gap_type(merged)
    fields["oracle_gap_type"] = gap_type
    fields["eligible_for_selector"] = gap_type not in {
        "dependency",
        "policy",
        "presentation",
        "runtime-error",
    }
    fields["selection_gap"] = gap_type == "selection"
    fields["fully_recoverable_selection_gap"] = gap_type == "selection" and bool(
        fields["oracle_speech_equivalent"]
    )
    return fields


def _unit_outcome(
    unit: AsyncTNUnit, actual: str, expected: str, metrics: dict[str, Any], ambiguous: bool
) -> str:
    if ambiguous:
        return "mapping-ambiguous"
    if metrics["speech_equivalent"]:
        if unit.text == expected:
            return "identity-preserved"
        if metrics["literal_exact"]:
            return "correct-transform"
        return "presentation-only"
    if literal_key(actual) == literal_key(unit.text):
        return "transform-miss"
    return "wrong-transform"


def _unit_record(
    case: AsyncTNCase,
    unit: AsyncTNUnit,
    expected_projection: UnitProjection | None,
    actual_projection: UnitProjection | None,
    result: PreparedText | None,
    *,
    error: str | None = None,
) -> dict[str, Any]:
    expected = expected_projection.text if expected_projection else ""
    actual = (
        actual_projection.text
        if actual_projection
        else case.original_text[unit.source_start : unit.source_end]
    )
    ambiguous_expected = bool(expected_projection and expected_projection.ambiguous)
    ambiguous_actual = bool(actual_projection and actual_projection.ambiguous)
    ambiguous = ambiguous_expected or ambiguous_actual
    metrics = (
        _metric_values(actual, expected, case.source_language)
        if not error
        else {
            "literal_exact": False,
            "speech_exact": False,
            "speech_equivalent": False,
            "speech_wer": 1.0,
        }
    )
    outcome = (
        "runtime-error" if error else _unit_outcome(unit, actual, expected, metrics, ambiguous)
    )
    row: dict[str, Any] = {
        "record_type": "unit",
        "unit_id": case.unit_id(unit.index),
        "id": case.unit_id(unit.index),
        "case_id": case.case_id,
        "suite": case.suite,
        "source_language": case.source_language,
        "spokenform_language": case.spokenform_language,
        "category": unit.category,
        "source_category": unit.category,
        "source_text": unit.text,
        "source_start": unit.source_start,
        "source_end": unit.source_end,
        "expected": expected,
        "actual": actual,
        "expected_mapping_ambiguous": ambiguous_expected,
        "actual_mapping_ambiguous": ambiguous_actual,
        "mapping_ambiguous": ambiguous,
        **metrics,
        "outcome": outcome,
        "normalization_outcome": outcome,
        "source_rules": list(_source_rules(result.source_replacements, unit) if result else ()),
        "changed_stages": list(_changed_stages(result)),
        "error": error,
        "scorable": not ambiguous and error is None,
    }
    return _diagnostics(row, result, category=unit.category, language=case.source_language)


def _sentence_record(
    case: AsyncTNCase,
    result: PreparedText | None,
    unit_records: tuple[dict[str, Any], ...],
    *,
    error: str | None = None,
) -> dict[str, Any]:
    actual = result.spoken_text if result is not None and error is None else case.original_text
    metrics = (
        _metric_values(actual, case.normalized_text, case.source_language)
        if not error
        else {
            "literal_exact": False,
            "speech_exact": False,
            "speech_equivalent": False,
            "speech_wer": 1.0,
        }
    )
    outcome = (
        "runtime-error"
        if error
        else "correct"
        if metrics["speech_equivalent"]
        else "presentation-only"
        if metrics["speech_wer"] == 0.0
        else "semantic-failure"
    )
    record: dict[str, Any] = {
        "record_type": "sentence",
        "id": case.case_id,
        "case_id": case.case_id,
        "suite": case.suite,
        "source_language": case.source_language,
        "spokenform_language": case.spokenform_language,
        "original": case.original_text,
        "original_text": case.original_text,
        "expected": case.normalized_text,
        "actual": actual,
        "categories": list(case.categories),
        "units_total": len(unit_records),
        "units_scorable": sum(bool(item["scorable"]) for item in unit_records),
        "all_units_correct": bool(unit_records)
        and all(
            item["outcome"] in {"correct-transform", "identity-preserved", "presentation-only"}
            for item in unit_records
            if item["scorable"]
        )
        and not any(item["mapping_ambiguous"] for item in unit_records),
        **metrics,
        "speech_exact_equivalent": metrics["speech_equivalent"],
        "outcome": outcome,
        "normalization_outcome": outcome,
        "source_rules": sorted({rule for item in unit_records for rule in item["source_rules"]}),
        "changed_stages": list(_changed_stages(result)),
        "error": error,
        "semantic_failure": outcome == "semantic-failure",
        "presentation_only": outcome == "presentation-only",
        "normalization_sentences": case.original_text != case.normalized_text,
        "identity_sentence": case.original_text == case.normalized_text,
    }
    category = case.categories[0] if case.categories else "unknown"
    return _diagnostics(record, result, category=category, language=case.source_language)


def _profile_normalize_literals(profile: str, normalize_literals: bool | None) -> bool:
    if profile not in BENCHMARK_PROFILES:
        raise ValueError(f"unsupported Async TN profile {profile!r}")
    return profile == "extended" if normalize_literals is None else bool(normalize_literals)


def evaluate_cases(
    cases: Iterable[AsyncTNCase],
    *,
    profile: str = "default",
    normalize_literals: bool | None = None,
    candidate_oracle: bool = False,
) -> tuple[
    dict[str, Any],
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
]:
    """Evaluate cases and return summary, sentence rows, unit rows, and failures."""
    use_literals = _profile_normalize_literals(profile, normalize_literals)
    sentence_rows: list[dict[str, Any]] = []
    unit_rows: list[dict[str, Any]] = []
    for case in cases:
        expected_mapping = build_expected_mapping(case.original_text, case.normalized_text)
        result: PreparedText | None = None
        error: str | None = None
        try:
            result = prepare(
                case.original_text,
                language=case.spokenform_language,
                normalize_literals=use_literals,
            )
        except Exception as exc:  # isolate a bad sentence from the benchmark run
            error = f"{type(exc).__name__}: {exc}"
        units = tuple(
            _unit_record(
                case,
                unit,
                project_expected_unit(case, unit, expected_mapping),
                project_actual_unit(result, unit) if result is not None else None,
                result,
                error=error,
            )
            for unit in case.units
        )
        sentence = _sentence_record(case, result, units, error=error)
        if candidate_oracle:
            sentence.update(
                _oracle_row_fields(
                    sentence,
                    result,
                    case,
                    normalize_literals=use_literals,
                )
            )
            changed_spans = tuple(tuple(span) for span in sentence["oracle_spans"])
            units = tuple(
                {
                    **unit_record,
                    "oracle_changed_span": any(
                        unit_record["source_start"] < span_end
                        and span_start < unit_record["source_end"]
                        for span_start, span_end in changed_spans
                    ),
                    "oracle_gap_type": sentence["oracle_gap_type"],
                }
                for unit_record in units
            )
        sentence["profile"] = profile
        for unit_record in units:
            unit_record["profile"] = profile
        sentence_rows.append(sentence)
        unit_rows.extend(units)
    failures = tuple(
        row
        for row in sentence_rows
        if row["error"] or not row["speech_equivalent"] or row["presentation_only"]
    )
    summary = _aggregate(
        sentence_rows,
        unit_rows,
        profile=profile,
        normalize_literals=use_literals,
        candidate_oracle=candidate_oracle,
    )
    return summary, tuple(sentence_rows), tuple(unit_rows), failures


def evaluate(
    cases: Iterable[AsyncTNCase],
    *,
    profile: str = "default",
    normalize_literals: bool | None = None,
    candidate_oracle: bool = False,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    """Compatibility wrapper returning summary, rows, and sentence failures."""
    summary, rows, units, failures = evaluate_cases(
        cases,
        profile=profile,
        normalize_literals=normalize_literals,
        candidate_oracle=candidate_oracle,
    )
    summary["unit_records"] = units
    return summary, rows, failures


def _rate(correct: int, denominator: int) -> float:
    return correct / denominator if denominator else 0.0


def _metric_summary(rows: Iterable[dict[str, Any]], *, scorable: bool = True) -> dict[str, Any]:
    selected = [row for row in rows if not scorable or row.get("scorable", True)]
    return {
        "total": len(list(rows)) if not isinstance(rows, list) else len(rows),
        "scorable": len(selected),
        "literal_exact": sum(bool(row["literal_exact"]) for row in selected),
        "speech_exact": sum(bool(row["speech_exact"]) for row in selected),
        "speech_equivalent": sum(bool(row["speech_equivalent"]) for row in selected),
        "mean_speech_wer": sum(float(row["speech_wer"]) for row in selected) / len(selected)
        if selected
        else 0.0,
    }


def _aggregate(
    sentence_rows: list[dict[str, Any]],
    unit_rows: list[dict[str, Any]],
    *,
    profile: str,
    normalize_literals: bool,
    candidate_oracle: bool,
) -> dict[str, Any]:
    categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
    languages: dict[str, list[dict[str, Any]]] = defaultdict(list)
    language_categories: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in unit_rows:
        categories[row["category"]].append(row)
        languages[row["source_language"]].append(row)
        language_categories[row["source_language"]][row["category"]].append(row)

    def group_metrics(group: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(group)
        scorable = [row for row in group if row["scorable"]]
        correct = [row for row in scorable if row["speech_equivalent"]]
        return {
            "units_total": total,
            "units_scorable": len(scorable),
            "units_correct": len(correct),
            "units_incorrect": len(scorable) - len(correct),
            "units_quarantined": total - len(scorable),
            "accuracy": _rate(len(correct), len(scorable)),
            "mean_speech_wer": sum(row["speech_wer"] for row in scorable) / len(scorable)
            if scorable
            else 0.0,
        }

    unit_metrics = group_metrics(unit_rows)
    sentence_metrics = _metric_summary(sentence_rows, scorable=False)
    summary: dict[str, Any] = {
        "schema_version": 1,
        "benchmark": "async_tn",
        "profile": profile,
        "normalize_literals": normalize_literals,
        "counts": {
            "source_cases": len(sentence_rows),
            "selected_cases": len(sentence_rows),
            "evaluated_cases": len(sentence_rows),
            "runtime_error_cases": sum(bool(row["error"]) for row in sentence_rows),
            "excluded_cases": 0,
            **unit_metrics,
        },
        "sentence_metrics": sentence_metrics,
        "unit_metrics": unit_metrics,
        "categories": {key: group_metrics(value) for key, value in sorted(categories.items())},
        "languages": {key: group_metrics(value) for key, value in sorted(languages.items())},
        "language_categories": {
            language: {category: group_metrics(rows) for category, rows in sorted(groups.items())}
            for language, groups in sorted(language_categories.items())
        },
        "diagnostics": {
            "failure_families": failure_family_counts(sentence_rows + unit_rows),
            **diagnostic_aggregates(sentence_rows + unit_rows),
        },
        "quarantine": {"cases": 0, "units": unit_metrics["units_quarantined"]},
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "spokenform_version": _package_version("spokenform"),
            "abbr2words_version": _package_version("abbr2words"),
            "num2words_version": _package_version("num2words"),
            "configuration": {
                "profile": profile,
                "normalize_literals": normalize_literals,
                "oracle_categories_passed_to_prepare": False,
            },
        },
    }
    for key, value in unit_metrics.items():
        summary[key] = value
    summary["semantic_failure_count"] = sum(row["semantic_failure"] for row in sentence_rows)
    summary["speech_exact_equivalent_count"] = sum(
        row["speech_equivalent"] for row in sentence_rows
    )
    summary["literal_exact_count"] = sum(row["literal_exact"] for row in sentence_rows)
    summary["failure_families"] = summary["diagnostics"]["failure_families"]
    if candidate_oracle:
        sentence_languages: dict[str, list[dict[str, Any]]] = defaultdict(list)
        sentence_categories: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in sentence_rows:
            sentence_languages[str(row["source_language"])].append(row)
            sentence_categories[str(row["category"])].append(row)
        summary["candidate_oracle"] = {
            **oracle_aggregates(sentence_rows),
            "configuration_oracle": configuration_oracle_aggregates(sentence_rows),
            "by_language": {
                language: oracle_aggregates(rows)
                for language, rows in sorted(sentence_languages.items())
            },
            "by_category": {
                category: oracle_aggregates(rows)
                for category, rows in sorted(sentence_categories.items())
            },
            "by_ownership": {
                ownership: oracle_aggregates(
                    [row for row in sentence_rows if str(row.get("ownership")) == ownership]
                )
                for ownership in sorted({str(row.get("ownership")) for row in sentence_rows})
            },
            "by_risk_tier": {
                tier: oracle_aggregates(
                    [row for row in sentence_rows if str(row.get("risk_tier")) == tier]
                )
                for tier in RISK_TIERS
            },
            "by_primary_rule": {
                rule: oracle_aggregates(
                    [
                        row
                        for row in sentence_rows
                        if str(row.get("primary_rule") or "unrecognized") == rule
                    ]
                )
                for rule in sorted(
                    {str(row.get("primary_rule") or "unrecognized") for row in sentence_rows}
                )
            },
            "by_failure_family": {
                family: oracle_aggregates(
                    [row for row in sentence_rows if str(row.get("failure_family")) == family]
                )
                for family in sorted({str(row.get("failure_family")) for row in sentence_rows})
            },
        }
    return summary


__all__ = [
    "BENCHMARK_PROFILES",
    "ExpectedMapping",
    "UnitProjection",
    "build_expected_mapping",
    "evaluate",
    "evaluate_cases",
    "project_actual_unit",
    "project_expected_unit",
    "project_unit",
]
