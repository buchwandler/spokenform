"""Evaluation and local report generation for the Proteno benchmark."""

from __future__ import annotations

import json
import platform
import re
import string
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
from typing import Any

from spokenform import PreparedText, prepare
from spokenform.numeric_lexeme import numeric_speech_policy
from spokenform.sequences import render_letters

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

SEMANTIC_SYMBOLS = frozenset("$€£%@/°+=#&")
FAILURE_MARKDOWN_MAX_BYTES = 1024 * 1024


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


def speech_key_equivalent(text: str, *, language: str = "en") -> tuple[str, ...]:
    """Fold exact localized spoken letter names to their ASCII graphemes."""
    reverse: dict[str, str] = {}
    for character in "abcdefghijklmnopqrstuvwxyz":
        rendered = speech_key(render_letters(character, language=language))
        if len(rendered) == 1:
            reverse.setdefault(rendered[0], character)
    return tuple(reverse.get(token, token) for token in speech_key(text))


def word_error_rate(reference: Iterable[str], hypothesis: Iterable[str]) -> float:
    """Return word-level Levenshtein error rate."""
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


def residual_symbols(text: str) -> dict[str, int]:
    """Count source-like symbols left in generated speech."""
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


def environment_fingerprint(languages: Iterable[str]) -> dict[str, object]:
    from spokenform.language import resolve_abbr2words_language, resolve_num2words_language

    resolution = {
        language: {
            "spokenform": PROTENO_TO_SPOKENFORM[language],
            "num2words": resolve_num2words_language(PROTENO_TO_SPOKENFORM[language]),
            "abbr2words": resolve_abbr2words_language(PROTENO_TO_SPOKENFORM[language]),
        }
        for language in sorted(set(languages))
    }
    return {
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
            "prepare": {"use_spacy": False},
            "semantic_symbols": "".join(sorted(SEMANTIC_SYMBOLS)),
            "benchmark_commit": PROTENO_COMMIT,
        },
    }


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
        ("sports", "sports_score"),
        ("hashtag", "literal_payload"),
        ("mention", "literal_payload"),
        ("roman", "roman"),
        ("math", "mathematical_expression"),
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
    candidates = [edit for edit in (*replacements, *mapped_edits) if getattr(edit, "rule", None)]
    candidates.sort(
        key=lambda edit: (
            -(int(getattr(edit, "source_end", 0)) - int(getattr(edit, "source_start", 0))),
            int(getattr(edit, "source_start", 0)),
        )
    )
    winner = candidates[0] if candidates else None
    primary_rule = getattr(winner, "rule", None) if winner is not None else None
    winning_span = (
        None
        if winner is None
        else {
            "start": int(getattr(winner, "source_start", 0)),
            "end": int(getattr(winner, "source_end", 0)),
            "source": str(getattr(winner, "source", "")),
            "rule": primary_rule,
        }
    )
    rules = tuple(str(edit.rule) for edit in mapped_edits if getattr(edit, "rule", None))
    if presentation_only:
        phase = "presentation_only"
    elif primary_rule is None:
        phase = "unrecognized"
    elif any(getattr(edit, "stage", None) == "structured" for edit in mapped_edits):
        phase = "structured_rendering"
    elif any(getattr(edit, "stage", None) == "numbers" for edit in mapped_edits):
        phase = "locale_rendering"
    elif semantic_failure:
        phase = "downstream_rendering"
    else:
        phase = "downstream_rendering"
    return {
        "primary_rule": primary_rule,
        "winning_span": winning_span,
        "failure_phase": phase,
        "render_mode": _render_mode(primary_rule, rules),
        "numeric_policy": asdict(numeric_speech_policy(language)),
    }


def evaluate_cases(
    cases: Iterable[ProtenoCase],
    *,
    prepare_fn: Callable[..., PreparedText] = prepare,
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
            result = prepare_fn(case.original_text, language=language, use_spacy=False)
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
            **provenance,
        }
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
    }
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
        f"- Primary rule: `{failure['primary_rule']}`",
        f"- Failure phase: `{failure['failure_phase']}`",
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
        "Failure details are split into source-bearing Markdown shards so each "
        "file remains manageable in an editor.",
        "",
        f"- Total failures: {sum(report['failure_count'] for report in reports):,}",
        f"- Maximum shard size: {max_bytes:,} bytes",
        "",
    ]
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


def evaluate_and_write(
    cases: Iterable[ProtenoCase],
    *,
    exclusions: Iterable[ProtenoExclusion] = (),
    split: str = "all",
    output_root: Path | str = "benchmark-results/proteno",
) -> tuple[Path, dict[str, Any]]:
    """Evaluate cases and write metadata and local source-bearing reports."""
    case_list = tuple(cases)
    exclusion_list = tuple(exclusions)
    summary, failures = evaluate_cases(case_list)
    languages = sorted({case.proteno_language for case in case_list})
    output_dir = Path(output_root) / _run_id()
    output_dir.mkdir(parents=True, exist_ok=False)
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
        "environment": environment_fingerprint(languages),
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
        **summary,
    }
    with (output_dir / "failures.jsonl").open("w", encoding="utf-8") as handle:
        for failure in failures:
            handle.write(json.dumps(failure, ensure_ascii=False, sort_keys=True) + "\n")
    with (output_dir / "excluded.jsonl").open("w", encoding="utf-8") as handle:
        for exclusion in exclusion_list:
            handle.write(json.dumps(exclusion.as_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    summary_payload["failure_reports"] = _write_failures_markdown(failures, output_dir)
    (output_dir / "summary.json").write_text(
        json.dumps(summary_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return output_dir, summary_payload


__all__ = [
    "FAILURE_MARKDOWN_MAX_BYTES",
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
