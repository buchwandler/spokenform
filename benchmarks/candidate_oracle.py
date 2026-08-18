"""Structured-candidate oracle helpers shared by benchmark evaluators."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any

from spokenform import PreparedText
from spokenform.config import GenericAcronymCase, GenericAcronymMode
from spokenform.mapping import Replacement, apply_replacements, resolve_replacements
from spokenform.models import SourceReplacement
from spokenform.structured import (
    iter_structured_candidates,
    resolve_structured_candidates,
)

from .text_metrics import literal_key, speech_key, speech_key_equivalent, word_error_rate

MAX_COMPONENT_PATHS = 128
MAX_GLOBAL_COMBINATIONS = 512


@dataclass(frozen=True, slots=True)
class PathEnumeration:
    """The bounded set of non-overlapping paths for one conflict component."""

    paths: tuple[tuple[Replacement, ...], ...]
    truncated: bool = False


@dataclass(frozen=True, slots=True)
class OracleAnalysis:
    """Benchmark-neutral selector-headroom analysis for one prepared result."""

    candidate_count: int
    ambiguous_component_count: int
    alternative_path_count: int
    combinations_evaluated: int
    actual_speech_wer: float
    oracle_speech_wer: float
    selector_regret: float
    actual_speech_equivalent: bool
    oracle_speech_equivalent: bool
    oracle_literal_exact: bool
    oracle_rules: tuple[str, ...]
    oracle_spans: tuple[tuple[int, int], ...]
    baseline_structured_rules: tuple[str, ...]
    oracle_changed_rules: tuple[str, ...]
    scorable: bool
    truncated: bool
    gap_type: str
    reason: str | None = None


def _candidate_key(candidate: Replacement) -> tuple[int, int, str, str | None]:
    return (candidate.start, candidate.end, candidate.text, candidate.rule)


def _path_key(path: tuple[Replacement, ...]) -> tuple[tuple[int, int, str, str | None], ...]:
    return tuple(_candidate_key(candidate) for candidate in path)


def _path_sort_key(path: tuple[Replacement, ...]) -> tuple[Any, ...]:
    return (
        len(path),
        tuple(
            (
                candidate.start,
                candidate.end,
                candidate.rule or "",
                candidate.text,
            )
            for candidate in path
        ),
    )


def _ordered_candidates(
    candidates: tuple[Replacement, ...],
) -> tuple[Replacement, ...]:
    return tuple(
        candidate
        for _, candidate in sorted(
            enumerate(candidates),
            key=lambda item: (item[1].start, item[1].end, item[0]),
        )
    )


def _spans_overlap(
    left_start: int,
    left_end: int,
    right_start: int,
    right_end: int,
) -> bool:
    return left_start < right_end and right_start < left_end


def _same_path(
    left: tuple[Replacement, ...],
    right: tuple[Replacement, ...],
) -> bool:
    return _path_key(left) == _path_key(right)


def _group_spans(replacements: tuple[Replacement, ...]) -> tuple[tuple[int, int], ...]:
    if not replacements:
        return ()
    ordered = _ordered_candidates(replacements)
    spans: list[list[int]] = [[ordered[0].start, ordered[0].end]]
    for replacement in ordered[1:]:
        current = spans[-1]
        if replacement.start < current[1]:
            current[1] = max(current[1], replacement.end)
        else:
            spans.append([replacement.start, replacement.end])
    return tuple((start, end) for start, end in spans)


def _structured_source_replacements(
    result: PreparedText,
) -> tuple[SourceReplacement, ...]:
    return tuple(
        replacement
        for replacement in result.source_replacements
        if "structured" in replacement.stages
    )


def _source_replacements_as_replacements(
    replacements: tuple[SourceReplacement, ...],
) -> tuple[Replacement, ...]:
    return tuple(
        Replacement(
            item.source_start,
            item.source_end,
            item.replacement,
            kind=item.kind,
            language=item.language,
            rule=item.rule,
        )
        for item in replacements
    )


def _baseline_rules(replacements: tuple[Replacement, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item.rule for item in replacements if item.rule))


def _changed_rule_pairs(
    baseline_paths: tuple[tuple[Replacement, ...], ...],
    oracle_paths: tuple[tuple[Replacement, ...], ...],
) -> tuple[str, ...]:
    changed: list[str] = []
    for baseline, oracle in zip(baseline_paths, oracle_paths, strict=True):
        if _same_path(baseline, oracle):
            continue
        before = "|".join(item.rule or "<none>" for item in baseline) or "<none>"
        after = "|".join(item.rule or "<none>" for item in oracle) or "<none>"
        changed.append(f"{before} -> {after}")
    return tuple(changed)


def _oracle_rules(
    baseline_paths: tuple[tuple[Replacement, ...], ...],
    oracle_paths: tuple[tuple[Replacement, ...], ...],
) -> tuple[str, ...]:
    changed = [
        rule
        for baseline, oracle in zip(baseline_paths, oracle_paths, strict=True)
        if not _same_path(baseline, oracle)
        for rule in (item.rule for item in oracle if item.rule)
    ]
    return tuple(dict.fromkeys(changed))


def _oracle_spans(
    baseline_paths: tuple[tuple[Replacement, ...], ...],
    oracle_paths: tuple[tuple[Replacement, ...], ...],
) -> tuple[tuple[int, int], ...]:
    spans = [
        (item.start, item.end)
        for baseline, oracle in zip(baseline_paths, oracle_paths, strict=True)
        if not _same_path(baseline, oracle)
        for item in oracle
    ]
    return tuple(dict.fromkeys(spans))


def _score_text(
    actual: str,
    expected: str,
    *,
    language: str,
) -> tuple[bool, float, bool]:
    speech_equivalent = speech_key_equivalent(actual, language=language) == speech_key_equivalent(
        expected,
        language=language,
    )
    speech_wer = word_error_rate(speech_key(expected), speech_key(actual))
    literal_exact = literal_key(actual) == literal_key(expected)
    return speech_equivalent, speech_wer, literal_exact


def conflict_components(
    candidates: tuple[Replacement, ...],
) -> tuple[tuple[Replacement, ...], ...]:
    """Group transitive overlap components without changing candidate order."""
    ordered = _ordered_candidates(candidates)
    if not ordered:
        return ()
    components: list[list[Replacement]] = []
    current: list[Replacement] = []
    current_end = -1
    for candidate in ordered:
        if not current or candidate.start < current_end:
            current.append(candidate)
            current_end = max(current_end, candidate.end)
        else:
            components.append(current)
            current = [candidate]
            current_end = candidate.end
    if current:
        components.append(current)
    return tuple(tuple(component) for component in components)


def enumerate_component_paths(
    component: tuple[Replacement, ...],
    *,
    max_paths: int = MAX_COMPONENT_PATHS,
) -> PathEnumeration:
    """Enumerate bounded non-overlapping candidate paths for one component."""
    ordered = _ordered_candidates(component)
    if not ordered:
        return PathEnumeration(())
    seen: set[tuple[tuple[int, int, str, str | None], ...]] = set()
    paths: list[tuple[Replacement, ...]] = []
    truncated = False

    def backtrack(
        index: int,
        current: list[Replacement],
        current_end: int,
    ) -> None:
        nonlocal truncated
        if truncated:
            return
        if index == len(ordered):
            if not current:
                return
            path = tuple(current)
            key = _path_key(path)
            if key in seen:
                return
            seen.add(key)
            paths.append(path)
            if len(paths) > max_paths:
                truncated = True
            return
        backtrack(index + 1, current, current_end)
        if truncated:
            return
        candidate = ordered[index]
        if not current or candidate.start >= current_end:
            current.append(candidate)
            backtrack(index + 1, current, candidate.end)
            current.pop()

    backtrack(0, [], -1)
    limited = tuple(sorted(paths[:max_paths], key=_path_sort_key))
    return PathEnumeration(limited, truncated=truncated)


def counterfactual_text(
    source: str,
    result: PreparedText,
    alternative: tuple[Replacement, ...],
    *,
    language: str,
) -> str | None:
    """Compose a final-text counterfactual from source-aligned replacements."""
    if not alternative:
        return result.spoken_text
    alternative = resolve_structured_candidates(source, alternative, language=language)
    affected_spans = _group_spans(alternative)
    baseline = _source_replacements_as_replacements(
        tuple(getattr(result, "source_replacements", ()) or ())
    )
    for span_start, span_end in affected_spans:
        overlapping = tuple(
            item for item in baseline if _spans_overlap(item.start, item.end, span_start, span_end)
        )
        if overlapping and min(item.start for item in overlapping) < span_start:
            return None
        if overlapping and max(item.end for item in overlapping) > span_end:
            return None
    kept = tuple(
        item
        for item in baseline
        if not any(
            _spans_overlap(item.start, item.end, start, end) for start, end in affected_spans
        )
    )
    replacements = resolve_replacements((*kept, *alternative), source_length=len(source))
    value, _, _ = apply_replacements(source, replacements, stage="candidate-oracle")
    return value


def _baseline_reconstruction_matches(source: str, result: PreparedText) -> bool:
    baseline = _source_replacements_as_replacements(
        tuple(getattr(result, "source_replacements", ()) or ())
    )
    reconstructed, _, _ = apply_replacements(source, baseline, stage="oracle-baseline")
    return reconstructed == result.spoken_text


def _analysis_without_choices(
    *,
    candidate_count: int,
    actual_speech_wer: float,
    actual_speech_equivalent: bool,
    actual_literal_exact: bool,
    baseline_structured_rules: tuple[str, ...],
    gap_type: str,
    reason: str | None = None,
    truncated: bool = False,
) -> OracleAnalysis:
    return OracleAnalysis(
        candidate_count=candidate_count,
        ambiguous_component_count=0,
        alternative_path_count=1,
        combinations_evaluated=1,
        actual_speech_wer=actual_speech_wer,
        oracle_speech_wer=actual_speech_wer,
        selector_regret=0.0,
        actual_speech_equivalent=actual_speech_equivalent,
        oracle_speech_equivalent=actual_speech_equivalent,
        oracle_literal_exact=actual_literal_exact,
        oracle_rules=(),
        oracle_spans=(),
        baseline_structured_rules=baseline_structured_rules,
        oracle_changed_rules=(),
        scorable=gap_type != "oracle-unscorable",
        truncated=truncated,
        gap_type=gap_type,
        reason=reason,
    )


def analyze_candidate_oracle(
    source: str,
    expected: str,
    result: PreparedText,
    *,
    language: str,
    promote_literals: bool = False,
    generic_acronym_mode: GenericAcronymMode = "known_only",
    generic_acronym_case: GenericAcronymCase = "upper",
    max_component_paths: int = MAX_COMPONENT_PATHS,
    max_global_combinations: int = MAX_GLOBAL_COMBINATIONS,
) -> OracleAnalysis:
    """Measure selection headroom among existing structured candidates."""
    stages = tuple(getattr(result, "stages", ()) or ())
    protected_spans = tuple(getattr(result, "protected_spans", ()) or ())
    actual_speech_equivalent, actual_speech_wer, actual_literal_exact = _score_text(
        result.spoken_text,
        expected,
        language=language,
    )
    if any(stage.name == "unicode" and stage.changed for stage in stages):
        return _analysis_without_choices(
            candidate_count=0,
            actual_speech_wer=actual_speech_wer,
            actual_speech_equivalent=actual_speech_equivalent,
            actual_literal_exact=actual_literal_exact,
            baseline_structured_rules=(),
            gap_type="oracle-unscorable",
            reason="pre-structured-unicode-change",
        )
    candidates = iter_structured_candidates(
        source,
        language=language,
        protected_ranges=tuple((span.start, span.end) for span in protected_spans),
        promote_literals=promote_literals,
        generic_acronym_mode=generic_acronym_mode,
        generic_acronym_case=generic_acronym_case,
    )
    for candidate in candidates:
        if any(
            _spans_overlap(candidate.start, candidate.end, span.start, span.end)
            for span in protected_spans
        ):
            return _analysis_without_choices(
                candidate_count=len(candidates),
                actual_speech_wer=actual_speech_wer,
                actual_speech_equivalent=actual_speech_equivalent,
                actual_literal_exact=actual_literal_exact,
                baseline_structured_rules=(),
                gap_type="oracle-unscorable",
                reason="protected-candidate-overlap",
            )
    baseline_structured = resolve_structured_candidates(source, candidates, language=language)
    baseline_structured_rules = _baseline_rules(baseline_structured)
    if not _baseline_reconstruction_matches(source, result):
        return _analysis_without_choices(
            candidate_count=len(candidates),
            actual_speech_wer=actual_speech_wer,
            actual_speech_equivalent=actual_speech_equivalent,
            actual_literal_exact=actual_literal_exact,
            baseline_structured_rules=baseline_structured_rules,
            gap_type="oracle-unscorable",
            reason="baseline-reconstruction-failed",
        )
    components = conflict_components(candidates)
    enumerations: list[PathEnumeration] = []
    baseline_paths: list[tuple[Replacement, ...]] = []
    ambiguous_indices: list[int] = []
    for index, component in enumerate(components):
        enumeration = enumerate_component_paths(component, max_paths=max_component_paths)
        span_start = min(item.start for item in component)
        span_end = max(item.end for item in component)
        baseline_path = tuple(
            item
            for item in baseline_structured
            if _spans_overlap(item.start, item.end, span_start, span_end)
        )
        if baseline_path and not any(_same_path(baseline_path, path) for path in enumeration.paths):
            enumeration = PathEnumeration(
                tuple(sorted((*enumeration.paths, baseline_path), key=_path_sort_key)),
                truncated=enumeration.truncated,
            )
        enumerations.append(enumeration)
        baseline_paths.append(baseline_path)
        if len(enumeration.paths) > 1:
            ambiguous_indices.append(index)
    if not ambiguous_indices:
        gap_type = "no-ambiguous-candidates" if candidates else "no-ambiguous-candidates"
        return _analysis_without_choices(
            candidate_count=len(candidates),
            actual_speech_wer=actual_speech_wer,
            actual_speech_equivalent=actual_speech_equivalent,
            actual_literal_exact=actual_literal_exact,
            baseline_structured_rules=baseline_structured_rules,
            gap_type=gap_type,
        )

    ambiguous_paths = [enumerations[index].paths for index in ambiguous_indices]
    ambiguous_baseline_paths = [baseline_paths[index] for index in ambiguous_indices]
    total_exact_combinations = 1
    for paths in ambiguous_paths:
        total_exact_combinations *= len(paths)
    truncated = any(enumerations[index].truncated for index in ambiguous_indices)
    if total_exact_combinations <= max_global_combinations and not truncated:
        combinations = tuple(product(*ambiguous_paths))
    else:
        truncated = True
        candidate_combinations: list[tuple[tuple[Replacement, ...], ...]] = [
            tuple(ambiguous_baseline_paths)
        ]
        seen = {_path_key(tuple(item for path in ambiguous_baseline_paths for item in path))}
        for component_index, paths in enumerate(ambiguous_paths):
            for path in paths:
                selected = list(ambiguous_baseline_paths)
                selected[component_index] = path
                flattened = tuple(item for component_path in selected for item in component_path)
                key = _path_key(flattened)
                if key in seen:
                    continue
                seen.add(key)
                candidate_combinations.append(tuple(selected))
        combinations = tuple(candidate_combinations)
    scored: list[tuple[Any, ...]] = []
    for selected_paths in combinations:
        candidate_text: str | None
        if all(
            _same_path(baseline, selected)
            for baseline, selected in zip(ambiguous_baseline_paths, selected_paths, strict=True)
        ):
            candidate_text = result.spoken_text
        else:
            flattened = tuple(item for path in selected_paths for item in path)
            candidate_text = counterfactual_text(source, result, flattened, language=language)
        if candidate_text is None:
            continue
        oracle_speech_equivalent, oracle_speech_wer, oracle_literal_exact = _score_text(
            candidate_text,
            expected,
            language=language,
        )
        changed_components = sum(
            not _same_path(baseline, selected)
            for baseline, selected in zip(ambiguous_baseline_paths, selected_paths, strict=True)
        )
        changed_rules = _changed_rule_pairs(tuple(ambiguous_baseline_paths), selected_paths)
        scored.append(
            (
                not oracle_speech_equivalent,
                oracle_speech_wer,
                not oracle_literal_exact,
                changed_components,
                tuple(
                    (
                        item.start,
                        item.end,
                        item.rule or "",
                        item.text,
                    )
                    for path in selected_paths
                    for item in path
                ),
                selected_paths,
                oracle_speech_equivalent,
                oracle_speech_wer,
                oracle_literal_exact,
                changed_rules,
            )
        )
    if not scored:
        return OracleAnalysis(
            candidate_count=len(candidates),
            ambiguous_component_count=len(ambiguous_indices),
            alternative_path_count=len(combinations),
            combinations_evaluated=len(combinations),
            actual_speech_wer=actual_speech_wer,
            oracle_speech_wer=actual_speech_wer,
            selector_regret=0.0,
            actual_speech_equivalent=actual_speech_equivalent,
            oracle_speech_equivalent=actual_speech_equivalent,
            oracle_literal_exact=actual_literal_exact,
            oracle_rules=(),
            oracle_spans=(),
            baseline_structured_rules=baseline_structured_rules,
            oracle_changed_rules=(),
            scorable=False,
            truncated=truncated,
            gap_type="oracle-unscorable",
            reason="no-scorable-counterfactual",
        )
    winner = min(scored)
    selected_paths = winner[5]
    oracle_speech_equivalent = winner[6]
    oracle_speech_wer = winner[7]
    oracle_literal_exact = winner[8]
    changed_rules = winner[9]
    gap_type = "candidates-no-gain"
    if truncated:
        gap_type = "oracle-truncated"
    elif oracle_speech_wer < actual_speech_wer:
        gap_type = "selection"
    return OracleAnalysis(
        candidate_count=len(candidates),
        ambiguous_component_count=len(ambiguous_indices),
        alternative_path_count=len(combinations),
        combinations_evaluated=len(combinations),
        actual_speech_wer=actual_speech_wer,
        oracle_speech_wer=oracle_speech_wer,
        selector_regret=max(0.0, actual_speech_wer - oracle_speech_wer),
        actual_speech_equivalent=actual_speech_equivalent,
        oracle_speech_equivalent=oracle_speech_equivalent,
        oracle_literal_exact=oracle_literal_exact,
        oracle_rules=_oracle_rules(tuple(ambiguous_baseline_paths), selected_paths),
        oracle_spans=_oracle_spans(tuple(ambiguous_baseline_paths), selected_paths),
        baseline_structured_rules=baseline_structured_rules,
        oracle_changed_rules=changed_rules,
        scorable=True,
        truncated=truncated,
        gap_type=gap_type,
    )


def analysis_fields(analysis: OracleAnalysis) -> dict[str, Any]:
    """Project one oracle analysis into stable flat row fields."""
    return {
        "candidate_count": analysis.candidate_count,
        "ambiguous_component_count": analysis.ambiguous_component_count,
        "alternative_path_count": analysis.alternative_path_count,
        "combinations_evaluated": analysis.combinations_evaluated,
        "actual_speech_wer": analysis.actual_speech_wer,
        "oracle_speech_wer": analysis.oracle_speech_wer,
        "selector_regret": analysis.selector_regret,
        "actual_speech_equivalent": analysis.actual_speech_equivalent,
        "oracle_speech_equivalent": analysis.oracle_speech_equivalent,
        "oracle_literal_exact": analysis.oracle_literal_exact,
        "oracle_rules": list(analysis.oracle_rules),
        "oracle_spans": [list(span) for span in analysis.oracle_spans],
        "baseline_structured_rules": list(analysis.baseline_structured_rules),
        "oracle_changed_rules": list(analysis.oracle_changed_rules),
        "oracle_scorable": analysis.scorable,
        "oracle_truncated": analysis.truncated,
        "oracle_reason": analysis.reason,
        "oracle_internal_gap_type": analysis.gap_type,
    }


__all__ = [
    "analysis_fields",
    "MAX_COMPONENT_PATHS",
    "MAX_GLOBAL_COMBINATIONS",
    "OracleAnalysis",
    "PathEnumeration",
    "analyze_candidate_oracle",
    "conflict_components",
    "counterfactual_text",
    "enumerate_component_paths",
]
