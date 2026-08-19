"""Evaluation and local report generation for the Proteno benchmark."""

from __future__ import annotations

import json
import platform
import re
import subprocess
import sys
import unicodedata
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

from .candidate_oracle import (
    MAX_COMPONENT_PATHS,
    MAX_GLOBAL_COMBINATIONS,
    analyze_candidate_oracle,
)
from .candidate_oracle import (
    analysis_fields as candidate_oracle_fields,
)
from .compare_common import with_configuration_hash
from .failure_reporting import (
    RISK_TIERS,
    diagnostic_aggregates,
    failure_family,
    failure_family_counts,
    oracle_aggregates,
    oracle_gap_type,
    outcome_for_row,
    ownership_for_rule,
    rank_provenance,
    reason_code,
    risk_tier_for_row,
)
from .proteno_data import (
    PROTENO_COMMIT,
    PROTENO_DATASET_COMMIT,
    PROTENO_DATASET_COUNTS,
    PROTENO_FILES,
    PROTENO_REPOSITORY,
    PROTENO_TO_SPOKENFORM,
    ProtenoCase,
    ProtenoExclusion,
    split_policy,
)
from .text_metrics import literal_key, speech_key, speech_key_equivalent, word_error_rate

SEMANTIC_SYMBOLS = frozenset("$€£%@/°+=#&")
BENCHMARK_PROFILES = ("default", "extended")
LiteralProfile = Literal["default", "extended"]
FAILURE_MARKDOWN_MAX_BYTES = 1024 * 1024

# Local benchmark-quality annotations.  Keep this mapping empty until a
# concrete upstream row has been reviewed with a reproducible source/target
# mismatch; adapter failures must never be quarantined merely because runtime
# normalization currently disagrees.
PROTENO_QUARANTINE: dict[str, dict[str, str]] = {}


def residual_symbols(text: str) -> dict[str, int]:
    """Count source-like symbols left in generated speech."""
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


def _foreign_script_characters(text: str) -> tuple[str, ...]:
    """Return conservative non-Latin alphabetic characters for adapter triage."""
    return tuple(
        character
        for character in text
        if character.isalpha() and "LATIN" not in unicodedata.name(character, "")
    )


def _is_external_language_projection(case: ProtenoCase) -> bool:
    """Identify lossy language/script projections without changing normalization."""
    if case.had_lang_span:
        return True
    foreign = _foreign_script_characters(case.original_text)
    if not foreign:
        return False
    return any(
        case.original_text.count(character) > case.normalized_text.count(character)
        for character in foreign
    )


def _package_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "not-installed"


def source_commit() -> str | None:
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
    languages: Iterable[str], *, profile: LiteralProfile = "default"
) -> dict[str, Any]:
    from spokenform.language import resolve_abbr2words_language, resolve_num2words_language

    resolution = {
        language: {
            "spokenform": PROTENO_TO_SPOKENFORM[language],
            "num2words": resolve_num2words_language(PROTENO_TO_SPOKENFORM[language]),
            "abbr2words": resolve_abbr2words_language(PROTENO_TO_SPOKENFORM[language]),
        }
        for language in sorted(set(languages))
    }
    return with_configuration_hash(
        {
            "dataset_repository": PROTENO_REPOSITORY,
            "dataset_commit": PROTENO_DATASET_COMMIT,
            "spokenform_version": _package_version("spokenform"),
            "spokenform_source_commit": source_commit(),
            "abbr2words_version": _package_version("abbr2words"),
            "num2words_version": _package_version("num2words"),
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
            "locale_mapping": resolution,
            "configuration": {
                "prepare": {
                    "use_spacy": False,
                    "symbol_mode": "remove",
                    "normalize_literals": profile == "extended",
                },
                "profile": profile,
                "acronym_policy": {
                    "generic_mode": "conservative_unknown"
                    if profile == "extended"
                    else "known_only",
                    "generic_case": "lower" if profile == "extended" else "upper",
                    "registered_mode": "spell" if profile == "extended" else "expand",
                },
                "semantic_symbols": "".join(sorted(SEMANTIC_SYMBOLS)),
                "benchmark_commit": PROTENO_COMMIT,
            },
        }
    )


def _metric_counts(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    values = list(rows)
    count = len(values)
    literal_count = sum(bool(item["literal_exact"]) for item in values)
    speech_count = sum(bool(item["speech_exact"]) for item in values)
    equivalent_count = sum(bool(item["speech_exact_equivalent"]) for item in values)
    wers = [float(item["speech_wer"]) for item in values if not item["error"]]
    return {
        "cases": count,
        "literal_exact_count": literal_count,
        "literal_exact_rate": literal_count / count if count else 0.0,
        "speech_exact_count": speech_count,
        "speech_exact_rate": speech_count / count if count else 0.0,
        "speech_exact_equivalent_count": equivalent_count,
        "speech_exact_equivalent_rate": equivalent_count / count if count else 0.0,
        "presentation_only_count": sum(bool(item["presentation_only"]) for item in values),
        "semantic_failure_count": sum(bool(item["semantic_failure"]) for item in values),
        "mean_speech_wer": mean(wers) if wers else 0.0,
        "median_speech_wer": median(wers) if wers else 0.0,
        "unchanged_count": sum(bool(item["unchanged"]) for item in values),
        "error_count": sum(bool(item["error"]) for item in values),
        "failure_family_count": len(failure_family_counts(values)),
    }


def _residual_counts(rows: Iterable[dict[str, Any]]) -> dict[str, int]:
    totals: defaultdict[str, int] = defaultdict(int)
    for row in rows:
        for symbol, count in row["residual_symbols"].items():
            totals[symbol] += int(count)
    return dict(sorted(totals.items()))


def _render_mode(primary_rule: str | None, rules: Iterable[str]) -> str:
    haystack = " ".join(rule.casefold() for rule in rules)
    for marker, mode in (
        ("isbn", "digit_sequence"),
        ("phone", "digit_sequence"),
        ("serial", "digit_sequence"),
        ("product", "typed_code"),
        ("address", "address"),
        ("coordinate", "coordinate"),
        ("legal", "legal_reference"),
        ("formula", "chemical_formula"),
        ("biology", "biological_classification"),
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
    return "cardinal" if primary_rule else "unchanged"


def _provenance(
    result: Any, *, language: str, semantic_failure: bool, presentation_only: bool
) -> dict[str, Any]:
    mapped_edits = tuple(getattr(result, "mapped_edits", ()) or ())
    replacements = tuple(getattr(result, "source_replacements", ()) or ())
    diagnostics = rank_provenance(
        (*replacements, *mapped_edits),
        semantic_failure=semantic_failure,
        presentation_only=presentation_only,
        protected_spans=tuple(getattr(result, "protected_spans", ()) or ()),
    )
    primary_rule = diagnostics["primary_rule"]
    diagnostics.update(
        {
            "render_mode": _render_mode(
                primary_rule,
                (primary_rule, *diagnostics["secondary_rules"])
                if primary_rule
                else diagnostics["secondary_rules"],
            ),
            "numeric_policy": asdict(numeric_speech_policy(language)),
        }
    )
    if primary_rule == "sequence.version":
        diagnostics.update({"separator": ".", "separator_role": "version"})
    return diagnostics


def _candidate_oracle_kwargs(profile: LiteralProfile) -> dict[str, Any]:
    return {
        "promote_literals": profile == "extended",
        "generic_acronym_mode": "conservative_unknown" if profile == "extended" else "known_only",
        "generic_acronym_case": "lower" if profile == "extended" else "upper",
        "max_component_paths": MAX_COMPONENT_PATHS,
        "max_global_combinations": MAX_GLOBAL_COMBINATIONS,
    }


def _oracle_row_fields(
    row: dict[str, Any],
    result: PreparedText | Any,
    *,
    expected: str,
    language: str,
    profile: LiteralProfile,
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
                row["original_text"],
                expected,
                result,
                language=language,
                **_candidate_oracle_kwargs(profile),
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


def evaluate_cases(
    cases: Iterable[ProtenoCase],
    *,
    prepare_fn: Callable[..., PreparedText] = prepare,
    profile: LiteralProfile = "default",
    candidate_oracle: bool = False,
) -> tuple[dict[str, Any], tuple[dict[str, Any], ...]]:
    """Evaluate cases while isolating individual runtime errors."""
    rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for case in cases:
        language = PROTENO_TO_SPOKENFORM[case.proteno_language]
        error: str | None = None
        actual = ""
        warnings: list[str] = []
        result: Any = None
        changed_stages: tuple[str, ...] = ()
        source_rules: tuple[str, ...] = ()
        structured_claimed = False
        try:
            kwargs: dict[str, object] = {
                "language": language,
                "use_spacy": False,
                "symbol_mode": "remove",
            }
            if profile == "extended":
                kwargs.update(
                    {
                        "normalize_literals": True,
                        "generic_acronym_mode": "conservative_unknown",
                        "generic_acronym_case": "lower",
                        "registered_acronym_mode": "spell",
                    }
                )
            result = prepare_fn(case.original_text, **kwargs)
            actual = result.spoken_text
            warnings = list(getattr(result, "warnings", ()) or ())
            changed_stages = tuple(
                stage.name for stage in (getattr(result, "stages", ()) or ()) if stage.changed
            )
            source_rules = tuple(
                sorted(
                    {
                        edit.rule
                        for edit in (getattr(result, "mapped_edits", ()) or ())
                        if getattr(edit, "rule", None)
                    }
                )
            )
            structured_claimed = any(
                getattr(edit, "stage", None) == "structured"
                for edit in (getattr(result, "mapped_edits", ()) or ())
            )
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
        provenance = _provenance(
            result,
            language=language,
            semantic_failure=semantic_failure,
            presentation_only=presentation_only,
        )
        if error:
            provenance["failure_phase"] = "parse_error"
        row: dict[str, Any] = {
            "id": case.case_id,
            "proteno_language": case.proteno_language,
            "spokenform_language": language,
            "index": case.index,
            "split": case.split,
            "case_kind": case.case_kind,
            "profile": profile,
            "original_text": case.original_text,
            "expected": case.normalized_text,
            "actual": actual,
            "literal_exact": literal_exact,
            "speech_exact": speech_exact,
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
            "had_lang_span": case.had_lang_span,
            "had_error_span": case.had_error_span,
            "projection_notes": case.projection_notes,
            **provenance,
        }
        if candidate_oracle:
            row.update(
                _oracle_row_fields(
                    row,
                    result,
                    expected=case.normalized_text,
                    language=language,
                    profile=profile,
                )
            )

        quarantine = PROTENO_QUARANTINE.get(case.case_id)
        row["quarantine"] = quarantine
        row["ownership"] = (
            "external-language"
            if _is_external_language_projection(case)
            else ownership_for_rule(row.get("primary_rule"), protected=False)
        )
        row["outcome"] = outcome_for_row(row)
        row["failure_family"] = failure_family(row)
        row["risk_tier"] = risk_tier_for_row(row)
        rows.append(row)
        if error or not literal_exact or not speech_exact:
            failures.append(
                {
                    **row,
                    "source_tokens": case.source_tokens,
                    "original_text": case.original_text,
                    "expected": case.normalized_text,
                    "actual": actual,
                    "warnings": warnings,
                }
            )

    grouped_language: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_split: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
    grouped_language_kind: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for row in rows:
        grouped_language[row["proteno_language"]].append(row)
        grouped_split[row["split"]].append(row)
        grouped_kind[row["case_kind"]].append(row)
        grouped_language_kind[row["proteno_language"]][row["case_kind"]].append(row)
    normalization = grouped_kind.get("normalization", [])
    identity = grouped_kind.get("identity", [])
    normalization_success = sum(
        bool(row["speech_exact_equivalent"]) for row in normalization if not row["error"]
    )
    identity_preserved = sum(
        bool(row["speech_exact_equivalent"]) for row in identity if not row["error"]
    )
    diagnostics = diagnostic_aggregates(rows)
    reported_failures = tuple(failures)
    ownership_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        ownership_groups[str(row["ownership"])].append(row)
    summary: dict[str, Any] = {
        **_metric_counts(rows),
        "by_language": {
            key: _metric_counts(value) for key, value in sorted(grouped_language.items())
        },
        "by_split": {key: _metric_counts(value) for key, value in sorted(grouped_split.items())},
        "by_case_kind": {key: _metric_counts(value) for key, value in sorted(grouped_kind.items())},
        "by_language_case_kind": {
            language: {kind: _metric_counts(kind_rows) for kind, kind_rows in sorted(kinds.items())}
            for language, kinds in sorted(grouped_language_kind.items())
        },
        "residual_symbols": _residual_counts(rows),
        "residual_symbols_by_language": {
            language: _residual_counts(language_rows)
            for language, language_rows in sorted(grouped_language.items())
        },
        "normalization_cases": len(normalization),
        "normalization_success_count": normalization_success,
        "normalization_success_rate": normalization_success / len(normalization)
        if normalization
        else 0.0,
        "normalization_unchanged_miss_count": sum(bool(row["unchanged"]) for row in normalization),
        "identity_cases": len(identity),
        "identity_preserved_count": identity_preserved,
        "identity_preservation_rate": identity_preserved / len(identity) if identity else 0.0,
        "identity_mutation_count": sum(
            bool(not row["speech_exact_equivalent"]) for row in identity if not row["error"]
        ),
        "failure_families": failure_family_counts(rows),
        "diagnostic_aggregates": diagnostics,
        "outcome_counts": diagnostics["by_outcome"],
        "risk_tier_counts": {
            tier: sum(row.get("risk_tier") == tier for row in reported_failures)
            for tier in RISK_TIERS
        },
        "reviewed": _metric_counts([row for row in rows if row["quarantine"] is None]),
        "quarantine_count": sum(row["quarantine"] is not None for row in rows),
        "profile": profile,
        "normalize_literals": profile == "extended",
    }
    if candidate_oracle:
        summary["candidate_oracle"] = {
            **oracle_aggregates(rows),
            "by_language": {
                key: oracle_aggregates(value) for key, value in sorted(grouped_language.items())
            },
            "by_split": {
                key: oracle_aggregates(value) for key, value in sorted(grouped_split.items())
            },
            "by_case_kind": {
                key: oracle_aggregates(value) for key, value in sorted(grouped_kind.items())
            },
            "by_language_case_kind": {
                language: {
                    kind: oracle_aggregates(kind_rows) for kind, kind_rows in sorted(kinds.items())
                }
                for language, kinds in sorted(grouped_language_kind.items())
            },
            "by_ownership": {
                key: oracle_aggregates(value) for key, value in sorted(ownership_groups.items())
            },
            "by_risk_tier": {
                tier: oracle_aggregates([row for row in rows if str(row.get("risk_tier")) == tier])
                for tier in RISK_TIERS
            },
            "by_primary_rule": {
                rule: oracle_aggregates(
                    [row for row in rows if str(row.get("primary_rule") or "unrecognized") == rule]
                )
                for rule in sorted({str(row.get("primary_rule") or "unrecognized") for row in rows})
            },
            "by_failure_family": {
                family: oracle_aggregates(
                    [row for row in rows if str(row.get("failure_family")) == family]
                )
                for family in sorted({str(row.get("failure_family")) for row in rows})
            },
        }
    summary["gate_metrics"] = {
        "safety": {
            "identity_cases": len(identity),
            "identity_mutation_count": summary["identity_mutation_count"],
            "protected_mutation_count": sum(bool(row.get("protected_mutation")) for row in rows),
        },
        "owned": _metric_counts(ownership_groups.get("owned", [])),
        "dependency-abbr2words": _metric_counts(ownership_groups.get("dependency-abbr2words", [])),
        "extended": _metric_counts(ownership_groups.get("extended-candidate", [])),
        "protected": _metric_counts(ownership_groups.get("protected", [])),
        "downstream": _metric_counts(ownership_groups.get("downstream", [])),
        "unsupported": _metric_counts(ownership_groups.get("unsupported", [])),
        "external-language": _metric_counts(ownership_groups.get("external-language", [])),
        "questionable-target": _metric_counts(ownership_groups.get("questionable-target", [])),
        "quarantine": _metric_counts([row for row in rows if row.get("quarantine") is not None]),
    }
    summary["unrecognized_count"] = sum(
        row.get("failure_phase") == "unrecognized" for row in reported_failures
    )
    summary["structured_rendering_count"] = sum(
        row.get("failure_phase") == "structured_rendering" for row in reported_failures
    )
    summary["dependency_abbreviation_count"] = sum(
        row.get("ownership") == "dependency-abbr2words" for row in reported_failures
    )
    summary["_rows"] = tuple(rows)
    return summary, tuple(failures)


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _failure_markdown_entry(failure: dict[str, Any]) -> str:
    lines = [
        f"#### {failure['id']}",
        f"- Split: `{failure['split']}`",
        f"- Source tokens: `{failure['source_tokens']}`",
        f"- Original: `{failure['original_text']}`",
        f"- Expected: `{failure['expected']}`",
        f"- Actual: `{failure['actual']}`",
        f"- Speech WER: `{failure['speech_wer']:.4f}`",
        f"- Primary rule: `{failure.get('primary_rule')}`",
        f"- Failure phase: `{failure.get('failure_phase')}`",
        f"- Ownership: `{failure.get('ownership')}`",
        f"- Risk tier: `{failure.get('risk_tier')}`",
        f"- Error: `{failure['error']}`" if failure["error"] else "- Error: none",
        "",
    ]
    return "\n".join(lines)


def _failure_markdown_shard_header(
    language: str, case_kind: str, part: int, total_parts: int
) -> str:
    return f"# Proteno failures: {language} / {case_kind}\n\nPart {part} of {total_parts}.\n\n"


def _write_failures_markdown(
    failures: Iterable[dict[str, Any]],
    output_dir: Path,
    *,
    max_bytes: int = FAILURE_MARKDOWN_MAX_BYTES,
    identity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a small Markdown index and bounded, source-bearing detail shards."""
    if max_bytes <= 1024:
        raise ValueError("max_bytes must be greater than 1024")
    grouped: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for failure in failures:
        grouped[failure["proteno_language"]][failure["case_kind"]].append(failure)

    reports: list[dict[str, Any]] = []
    for language, kinds in sorted(grouped.items()):
        for kind, kind_failures in sorted(kinds.items()):
            entries = [_failure_markdown_entry(failure) for failure in kind_failures]
            header_bytes = len(
                _failure_markdown_shard_header(language, kind, 999999, 999999).encode("utf-8")
            )
            body_limit = max_bytes - header_bytes
            chunks: list[list[str]] = []
            current: list[str] = []
            current_bytes = 0
            for entry_index, entry in enumerate(entries):
                entry_bytes = len(entry.encode("utf-8"))
                if entry_bytes + header_bytes > max_bytes:
                    raise ValueError(
                        f"failure {kind_failures[entry_index]['id']} exceeds the Markdown "
                        f"shard limit of {max_bytes} bytes"
                    )
                if current and current_bytes + entry_bytes > body_limit:
                    chunks.append(current)
                    current = []
                    current_bytes = 0
                current.append(entry)
                current_bytes += entry_bytes
            if current:
                chunks.append(current)

            total_parts = len(chunks)
            for part, chunk in enumerate(chunks, 1):
                filename = f"failures-{language}-{kind}-{part:03d}.md"
                shard_path = output_dir / filename
                shard_path.write_text(
                    _failure_markdown_shard_header(language, kind, part, total_parts)
                    + "".join(chunk),
                    encoding="utf-8",
                )
                reports.append(
                    {
                        "path": filename,
                        "language": language,
                        "case_kind": kind,
                        "part": part,
                        "parts": total_parts,
                        "failure_count": len(chunk),
                    }
                )

    lines = [
        "# Proteno failures",
        "",
        "## Run identity",
        "",
    ]
    if identity:
        lines.extend(f"- {key}: `{value}`" for key, value in sorted(identity.items()))
    else:
        lines.append("Identity metadata is available in summary.json.")
    lines.extend(
        [
            "",
            "Failure details are split into source-bearing Markdown shards so each "
            "file remains manageable in an editor.",
            "Each shard records the primary rule, failure phase, ownership, and Risk tier.",
            "",
            f"- Total failures: {sum(report['failure_count'] for report in reports):,}",
            f"- Maximum shard size: {max_bytes:,} bytes",
            "",
        ]
    )
    if reports:
        lines.extend(["## Reports", ""])
        for report in reports:
            lines.append(
                f"- [{report['language']} / {report['case_kind']} "
                f"(part {report['part']} of {report['parts']})]({report['path']}) — "
                f"{report['failure_count']:,} failures"
            )
    else:
        lines.append("No failures.")
    (output_dir / "failures.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "index": "failures.md",
        "max_bytes": max_bytes,
        "shards": reports,
    }


def _filter_failures_by_speech_wer(
    failures: Iterable[dict[str, Any]], threshold: float | None
) -> tuple[dict[str, Any], ...]:
    """Select persisted failures without changing complete-run evaluation metrics."""
    values = tuple(failures)
    if threshold is None:
        return values
    return tuple(failure for failure in values if float(failure["speech_wer"]) > threshold)


def evaluate_and_write(
    cases: Iterable[ProtenoCase],
    *,
    exclusions: Iterable[ProtenoExclusion] = (),
    split: str = "all",
    output_root: Path | str = "benchmark-results/proteno",
    speech_wer_threshold: float | None = None,
    profile: LiteralProfile = "default",
    candidate_oracle: bool = False,
    report: str = "html",
) -> tuple[Path, dict[str, Any]]:
    """Evaluate cases and write metadata and local source-bearing reports."""
    case_list = tuple(cases)
    exclusion_list = tuple(exclusions)
    if candidate_oracle:
        summary, failures = (
            evaluate_cases(case_list, profile=profile, candidate_oracle=True)
            if profile == "extended"
            else evaluate_cases(case_list, candidate_oracle=True)
        )
    else:
        summary, failures = (
            evaluate_cases(case_list, profile=profile)
            if profile == "extended"
            else evaluate_cases(case_list)
        )
    all_rows = summary.pop("_rows", ())
    stored_failures = _filter_failures_by_speech_wer(failures, speech_wer_threshold)
    languages = sorted({case.proteno_language for case in case_list})
    output_dir = Path(output_root) / _run_id()
    output_dir.mkdir(parents=True, exist_ok=False)
    environment = environment_fingerprint(languages, profile=profile)
    if candidate_oracle:
        environment = with_configuration_hash(
            {
                **environment,
                "configuration": {
                    **environment["configuration"],
                    "candidate_oracle_enabled": True,
                    "candidate_oracle_schema_version": 2,
                    "max_component_paths": MAX_COMPONENT_PATHS,
                    "max_global_combinations": MAX_GLOBAL_COMBINATIONS,
                },
            }
        )
    summary_payload: dict[str, Any] = {
        "benchmark": "Proteno",
        "repository": PROTENO_REPOSITORY,
        "dataset_commit": PROTENO_DATASET_COMMIT,
        "commit": PROTENO_COMMIT,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "languages": languages,
        "spokenform_languages": sorted({PROTENO_TO_SPOKENFORM[language] for language in languages}),
        "split": split,
        "split_policy": split_policy(PROTENO_DATASET_COUNTS),
        "environment": environment,
        "identity": {
            "benchmark": "Proteno",
            "dataset_commit": PROTENO_DATASET_COMMIT,
            "spokenform_source_commit": environment["spokenform_source_commit"],
            "abbr2words_version": environment["abbr2words_version"],
            "num2words_version": environment["num2words_version"],
            "profile": profile,
            "config_hash": environment["config_hash"],
            "locale_mapping": environment["locale_mapping"],
        },
        "profile": profile,
        "normalize_literals": profile == "extended",
        "source_file_git_blobs": {
            language: {kind: file.git_blob_sha for kind, file in PROTENO_FILES[language].items()}
            for language in languages
        },
        "source_file_sizes": {
            language: {kind: file.size for kind, file in PROTENO_FILES[language].items()}
            for language in languages
        },
        "dataset_counts": {language: PROTENO_DATASET_COUNTS[language] for language in languages},
        "selected_case_count": len(case_list),
        "excluded_count": len(exclusion_list),
        "excluded_by_reason": {
            reason: sum(item.reason == reason for item in exclusion_list)
            for reason in sorted({item.reason for item in exclusion_list})
        },
        "excluded_by_reason_code": {
            reason_code(item.reason): sum(
                reason_code(other.reason) == reason_code(item.reason) for other in exclusion_list
            )
            for item in exclusion_list
        },
        "speech_wer_threshold": speech_wer_threshold,
        "stored_failure_count": len(stored_failures),
        **summary,
    }
    with (output_dir / "failures.jsonl").open("w", encoding="utf-8") as handle:
        for failure in stored_failures:
            handle.write(json.dumps(failure, ensure_ascii=False, sort_keys=True) + "\n")
    with (output_dir / "rows.jsonl").open("w", encoding="utf-8") as handle:
        for row in all_rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    with (output_dir / "excluded.jsonl").open("w", encoding="utf-8") as handle:
        for exclusion in exclusion_list:
            payload = {**exclusion.as_dict(), "reason_code": reason_code(exclusion.reason)}
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    summary_payload["failure_reports"] = _write_failures_markdown(
        stored_failures, output_dir, identity=summary_payload["identity"]
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if candidate_oracle and "candidate_oracle" in summary_payload:
        (output_dir / "oracle_summary.json").write_text(
            json.dumps(
                {
                    "benchmark": summary_payload["benchmark"],
                    "profile": profile,
                    "generated_at": summary_payload["generated_at"],
                    "identity": {
                        **summary_payload["identity"],
                        "candidate_oracle_schema_version": 2,
                        "max_component_paths": MAX_COMPONENT_PATHS,
                        "max_global_combinations": MAX_GLOBAL_COMBINATIONS,
                    },
                    "candidate_oracle": summary_payload["candidate_oracle"],
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
    if report == "html":
        from .proteno_report import render_report

        render_report(summary_payload, all_rows, output_dir / "report.html")
    return output_dir, summary_payload


__all__ = [
    "FAILURE_MARKDOWN_MAX_BYTES",
    "BENCHMARK_PROFILES",
    "SEMANTIC_SYMBOLS",
    "environment_fingerprint",
    "evaluate_and_write",
    "evaluate_cases",
    "literal_key",
    "residual_symbols",
    "speech_key",
    "speech_key_equivalent",
    "word_error_rate",
]
