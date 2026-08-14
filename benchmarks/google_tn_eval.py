"""Streaming evaluator for the Google TN diagnostic benchmark."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Iterator
from typing import Any, Literal

from spokenform import PreparedText, prepare

from .failure_reporting import failure_family, ownership_for_rule
from .google_tn_format import GoogleTNCase, GoogleTNRow
from .text_metrics import literal_key, speech_key, speech_key_equivalent, word_error_rate

BENCHMARK_PROFILES = ("default", "extended")
LongNumberMode = Literal["preserve", "cardinal"]

GOOGLE_CLASS_CATEGORIES = {
    "CARDINAL": "Cardinal",
    "ORDINAL": "Ordinal",
    "DECIMAL": "Decimal",
    "FRACTION": "Fraction",
    "DATE": "Date",
    "TIME": "Time",
    "MONEY": "Currency",
    "MEASURE": "Unit",
    "TELEPHONE": "Phone Number",
    "ADDRESS": "Address",
    "ELECTRONIC": "URL or Email",
    "LETTERS": "Letters/Acronym",
    "VERBATIM": "Verbatim",
    "DIGIT": "Digit Sequence",
    "PLAIN": "Plain",
    "PUNCT": "Punctuation",
}


def canonical_category(semiotic_class: str) -> str:
    """Map known upstream labels while retaining unknown labels verbatim."""
    return GOOGLE_CLASS_CATEGORIES.get(semiotic_class, semiotic_class)


def _source_rules(result: PreparedText, row: GoogleTNRow) -> tuple[str, ...]:
    rules = {
        edit.rule
        for edit in result.source_replacements
        if edit.rule
        and edit.source_start < row.source_end
        and edit.source_end > row.source_start
    }
    return tuple(sorted(rules))


def _changed_stages(result: PreparedText) -> tuple[str, ...]:
    return tuple(stage.name for stage in result.stages if stage.changed)


def _mapping_for_row(
    result: PreparedText, row: GoogleTNRow
) -> tuple[int, int, bool, tuple[str, ...]]:
    """Map one upstream row and flag replacements crossing row boundaries."""
    output_start, output_end = result.map_source_span(row.source_start, row.source_end)
    ambiguous = any(
        edit.source_start < row.source_start or edit.source_end > row.source_end
        for edit in result.source_replacements
        if edit.source_start < row.source_end and edit.source_end > row.source_start
    )
    return output_start, output_end, ambiguous, _source_rules(result, row)


def _row_outcome(
    row: GoogleTNRow,
    *,
    actual: str,
    expected: str,
    speech_exact: bool,
    speech_exact_equivalent: bool,
    ambiguous: bool,
) -> str:
    if ambiguous:
        return "mapping-ambiguous"
    if speech_exact and literal_key(actual) != literal_key(expected):
        return "presentation-only"
    if speech_exact:
        return "identity-preserved" if row.is_identity else "correct-transform"
    if speech_exact_equivalent:
        return "presentation-only"
    if row.is_identity:
        return "identity-mutation"
    if literal_key(actual) == literal_key(row.written):
        return "transform-miss"
    return "wrong-transform"


def _row_record(
    case: GoogleTNCase,
    row: GoogleTNRow,
    result: PreparedText | None,
    *,
    error: str | None = None,
) -> dict[str, Any]:
    expected = row.expected_spoken
    actual = row.written
    output_start = output_end = None
    ambiguous = False
    source_rules: tuple[str, ...] = ()
    changed_stages: tuple[str, ...] = ()
    if result is not None and error is None:
        output_start, output_end, ambiguous, source_rules = _mapping_for_row(result, row)
        actual = result.spoken_text[output_start:output_end]
        changed_stages = _changed_stages(result)
    speech_exact = not error and speech_key(actual) == speech_key(expected)
    speech_equivalent = not error and speech_key_equivalent(actual) == speech_key_equivalent(expected)
    outcome = "runtime-error" if error else _row_outcome(
        row,
        actual=actual,
        expected=expected,
        speech_exact=speech_exact,
        speech_exact_equivalent=speech_equivalent,
        ambiguous=ambiguous,
    )
    record: dict[str, Any] = {
        "case_id": case.case_id,
        "semiotic_class": row.semiotic_class,
        "canonical_category": canonical_category(row.semiotic_class),
        "written": row.written,
        "expected": expected,
        "actual": actual,
        "source_line": row.source_line,
        "source_start": row.source_start,
        "source_end": row.source_end,
        "output_start": output_start,
        "output_end": output_end,
        "literal_exact": not error and literal_key(actual) == literal_key(expected),
        "speech_exact": speech_exact,
        "speech_exact_equivalent": speech_equivalent,
        "ambiguous_span_mapping": ambiguous,
        "normalization_outcome": outcome,
        "source_rules": list(source_rules),
        "primary_rule": source_rules[0] if source_rules else None,
        "changed_stages": list(changed_stages),
        "error": error,
            "warnings": list(getattr(result, "warnings", ()))
            if result is not None and error is None
            else [],
    }
    record["failure_family"] = failure_family(record)
    record["ownership"] = ownership_for_rule(record["primary_rule"])
    return record


def _sentence_record(
    case: GoogleTNCase,
    result: PreparedText | None,
    *,
    error: str | None = None,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    actual = result.spoken_text if result is not None and error is None else case.original_text
    literal_exact = not error and literal_key(actual) == literal_key(case.normalized_text)
    speech_exact = not error and speech_key(actual) == speech_key(case.normalized_text)
    equivalent = not error and speech_key_equivalent(actual) == speech_key_equivalent(case.normalized_text)
    presentation_only = bool(not error and not speech_exact and equivalent)
    semantic_failure = bool(not error and not equivalent)
    row_records = tuple(_row_record(case, row, result, error=error) for row in case.rows)
    outcome_counts = Counter(item["normalization_outcome"] for item in row_records)
    record: dict[str, Any] = {
        "id": case.case_id,
        "language": case.language,
        "spokenform_language": "en_US",
        "source_file": case.source_file,
        "line_start": case.line_start,
        "line_end": case.line_end,
        "semiotic_classes": sorted({row.semiotic_class for row in case.rows}),
        "original_text": case.original_text,
        "expected": case.normalized_text,
        "actual": actual,
        "speech_wer": word_error_rate(speech_key(case.normalized_text), speech_key(actual))
        if not error
        else 0.0,
        "literal_exact": literal_exact,
        "speech_exact": speech_exact,
        "speech_exact_equivalent": equivalent,
        "presentation_only": presentation_only,
        "semantic_failure": semantic_failure,
        "unchanged": actual == case.original_text if not error else False,
        "normalization_sentences": case.has_normalization,
        "identity_sentence": not case.has_normalization,
        "changed_stages": list(_changed_stages(result)) if result is not None and not error else [],
        "source_rules": sorted({rule for row in row_records for rule in row["source_rules"]}),
        "structured_claimed": any(
            stage == "structured"
            for stage in (_changed_stages(result) if result is not None and not error else ())
        ),
        "error": error,
        "warnings": list(getattr(result, "warnings", ()))
        if result is not None and error is None
        else [],
        "normalization_outcomes": dict(sorted(outcome_counts.items())),
        "failed_spans": [
            row
            for row in row_records
            if row["normalization_outcome"]
            not in {"correct-transform", "identity-preserved"}
        ],
    }
    record["primary_rule"] = record["source_rules"][0] if record["source_rules"] else None
    record["failure_family"] = failure_family(record)
    return record, row_records


def _empty_summary(profile: str) -> dict[str, Any]:
    return {
        "evaluated": 0,
        "exceptions": 0,
        "literal_exact": 0,
        "speech_exact": 0,
        "speech_exact_equivalent": 0,
        "presentation_only": 0,
        "semantic_failure": 0,
        "speech_wer": 0.0,
        "unchanged": 0,
        "normalization_sentences": 0,
        "identity_sentences": 0,
        "normalization_success_rate": 0.0,
        "identity_preservation_rate": 0.0,
        "span_count": 0,
        "scorable_span_count": 0,
        "ambiguous_span_mapping_count": 0,
        "span_literal_exact_count": 0,
        "span_speech_exact_count": 0,
        "span_speech_exact_equivalent_count": 0,
        "correct_transform_count": 0,
        "transform_miss_count": 0,
        "wrong_transform_count": 0,
        "identity_preserved_count": 0,
        "identity_mutation_count": 0,
        "runtime_error_count": 0,
        "by_semiotic_class": {},
        "profile": profile,
        "normalize_literals": profile == "extended",
        "long_number_mode": "preserve",
    }


def _increment_summary(summary: dict[str, Any], record: dict[str, Any], rows: Iterable[dict[str, Any]]) -> None:
    summary["evaluated"] += 1
    summary["exceptions"] += int(bool(record["error"]))
    for key in ("literal_exact", "speech_exact", "speech_exact_equivalent", "presentation_only", "semantic_failure", "unchanged"):
        summary[key] += int(bool(record[key]))
    summary["speech_wer"] += float(record["speech_wer"])
    if record["normalization_sentences"]:
        summary["normalization_sentences"] += 1
        summary["normalization_success_rate"] += int(record["speech_exact_equivalent"])
    else:
        summary["identity_sentences"] += 1
        summary["identity_preservation_rate"] += int(record["speech_exact_equivalent"])
    for row in rows:
        summary["span_count"] += 1
        if row["ambiguous_span_mapping"]:
            summary["ambiguous_span_mapping_count"] += 1
        else:
            summary["scorable_span_count"] += 1
            summary["span_literal_exact_count"] += int(row["literal_exact"])
            summary["span_speech_exact_count"] += int(row["speech_exact"])
            summary["span_speech_exact_equivalent_count"] += int(row["speech_exact_equivalent"])
        outcome = row["normalization_outcome"]
        key = {"runtime-error": "runtime_error_count"}.get(outcome, f"{outcome.replace('-', '_')}_count")
        if key in summary:
            summary[key] += 1
        by_class = summary["by_semiotic_class"].setdefault(row["semiotic_class"], {"count": 0})
        by_class["count"] += 1
        for count_key in (
            "correct_transform_count", "transform_miss_count", "wrong_transform_count",
            "identity_preserved_count", "identity_mutation_count", "runtime_error_count",
            "presentation_only_count", "mapping_ambiguous_count",
        ):
            if outcome == count_key.removesuffix("_count").replace("_", "-"):
                by_class[count_key] = by_class.get(count_key, 0) + 1


def finalize_summary(summary: dict[str, Any]) -> dict[str, Any]:
    """Finalize aggregate rates and averages after streaming evaluation."""
    evaluated = summary["evaluated"]
    summary["speech_wer"] = summary["speech_wer"] / evaluated if evaluated else 0.0
    normalization = summary["normalization_sentences"]
    identity = summary["identity_sentences"]
    summary["normalization_success_rate"] = (
        summary["normalization_success_rate"] / normalization if normalization else 0.0
    )
    summary["identity_preservation_rate"] = (
        summary["identity_preservation_rate"] / identity if identity else 0.0
    )
    return summary


def evaluate(
    cases: Iterable[GoogleTNCase],
    *,
    profile: Literal["default", "extended"] = "default",
    normalize_literals: bool | None = None,
    long_number_mode: LongNumberMode = "preserve",
    prepare_fn: Callable[..., PreparedText] = prepare,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    """Evaluate cases without using upstream classes as preparation hints."""
    if profile not in BENCHMARK_PROFILES:
        raise ValueError(f"unsupported benchmark profile {profile!r}")
    if long_number_mode not in {"preserve", "contextual", "cardinal"}:
        raise ValueError("long_number_mode must be preserve, contextual, or cardinal")
    if normalize_literals is None:
        normalize_literals = profile == "extended"
    summary = _empty_summary(profile)
    summary["normalize_literals"] = normalize_literals
    summary["long_number_mode"] = long_number_mode
    rows_out: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for case in cases:
        result: PreparedText | None = None
        error: str | None = None
        try:
            result = prepare_fn(
                case.original_text,
                language="en_US",
                use_spacy=False,
                symbol_mode="none",
                normalize_literals=normalize_literals,
                generic_acronym_mode="known_only",
                generic_acronym_case="upper",
                long_number_mode=long_number_mode,
            )
        except Exception as exc:  # benchmark discovery continues per case
            error = f"{type(exc).__name__}: {exc}"
        record, row_records = _sentence_record(case, result, error=error)
        _increment_summary(summary, record, row_records)
        rows_out.append(record)
        rows_out.extend({"record_type": "span", **row} for row in row_records)
        if error or not record["speech_exact"] or record["presentation_only"]:
            failures.append(record)
    return finalize_summary(summary), tuple(rows_out), tuple(failures)


__all__ = [
    "BENCHMARK_PROFILES",
    "GOOGLE_CLASS_CATEGORIES",
    "canonical_category",
    "evaluate",
    "finalize_summary",
]
