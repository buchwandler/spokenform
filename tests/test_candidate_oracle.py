from __future__ import annotations

from benchmarks import candidate_oracle as oracle
from spokenform.mapping import Replacement
from spokenform.models import PreparationStage, PreparedText, SourceReplacement
from spokenform.protection import ProtectedSpan


def _prepared(
    source: str,
    spoken: str,
    *,
    source_replacements: tuple[SourceReplacement, ...],
    protected_spans: tuple[ProtectedSpan, ...] = (),
    stages: tuple[PreparationStage, ...] = (),
) -> PreparedText:
    return PreparedText(
        source_text=source,
        clean_text=source,
        spoken_text=spoken,
        language="en",
        stages=stages,
        source_replacements=source_replacements,
        protected_spans=protected_spans,
    )


def test_counterfactual_text_reconstructs_baseline_output() -> None:
    source = "Value 3-2."
    result = _prepared(
        source,
        "Value three minus two.",
        source_replacements=(
            SourceReplacement(
                source.index("3-2"),
                source.index("3-2") + 3,
                source.index("3-2"),
                source.index("3-2") + len("three minus two"),
                "3-2",
                "three minus two",
                ("structured",),
                rule="sequence.numeric-range",
            ),
        ),
    )

    assert oracle.counterfactual_text(source, result, (), language="en") == result.spoken_text


def test_analyze_candidate_oracle_reports_recoverable_selection_gap(monkeypatch) -> None:
    source = "Value 3-2."
    baseline = Replacement(6, 9, "three minus two", rule="sequence.numeric-range")
    sports = Replacement(6, 9, "three to two", rule="sequence.sports")
    result = _prepared(
        source,
        "Value three minus two.",
        source_replacements=(
            SourceReplacement(
                6, 9, 6, 21, "3-2", "three minus two", ("structured",), rule=baseline.rule
            ),
        ),
    )

    monkeypatch.setattr(
        oracle, "iter_structured_candidates", lambda *args, **kwargs: (baseline, sports)
    )
    monkeypatch.setattr(
        oracle,
        "resolve_structured_candidates",
        lambda text, candidates, **kwargs: (baseline,) if len(candidates) == 2 else candidates,
    )

    analysis = oracle.analyze_candidate_oracle(source, "Value three to two.", result, language="en")

    assert analysis.gap_type == "selection"
    assert analysis.oracle_speech_wer < analysis.actual_speech_wer
    assert analysis.oracle_rules == ("sequence.sports",)
    assert analysis.oracle_changed_rules == ("sequence.numeric-range -> sequence.sports",)


def test_analyze_candidate_oracle_reports_no_ambiguous_candidates(monkeypatch) -> None:
    source = "Only 5."
    baseline = Replacement(5, 6, "five", rule="en.cardinal")
    result = _prepared(
        source,
        "Only five.",
        source_replacements=(
            SourceReplacement(5, 6, 5, 9, "5", "five", ("structured",), rule=baseline.rule),
        ),
    )

    monkeypatch.setattr(oracle, "iter_structured_candidates", lambda *args, **kwargs: (baseline,))
    monkeypatch.setattr(
        oracle, "resolve_structured_candidates", lambda text, candidates, **kwargs: candidates
    )

    analysis = oracle.analyze_candidate_oracle(source, "Only six.", result, language="en")

    assert analysis.gap_type == "no-ambiguous-candidates"
    assert analysis.selector_regret == 0.0


def test_analyze_candidate_oracle_reports_candidates_without_gain(monkeypatch) -> None:
    source = "Value 3-2."
    baseline = Replacement(6, 9, "three minus two", rule="sequence.numeric-range")
    alternate = Replacement(6, 9, "three dash two", rule="sequence.product")
    result = _prepared(
        source,
        "Value three minus two.",
        source_replacements=(
            SourceReplacement(
                6, 9, 6, 21, "3-2", "three minus two", ("structured",), rule=baseline.rule
            ),
        ),
    )

    monkeypatch.setattr(
        oracle,
        "iter_structured_candidates",
        lambda *args, **kwargs: (baseline, alternate),
    )
    monkeypatch.setattr(
        oracle,
        "resolve_structured_candidates",
        lambda text, candidates, **kwargs: (baseline,) if len(candidates) == 2 else candidates,
    )

    analysis = oracle.analyze_candidate_oracle(
        source, "Value three minus two.", result, language="en"
    )

    assert analysis.gap_type == "candidates-no-gain"
    assert analysis.selector_regret == 0.0


def test_analyze_candidate_oracle_rejects_protected_candidate_overlap(monkeypatch) -> None:
    source = "Keep 5."
    protected = ProtectedSpan(5, 6)
    baseline = Replacement(5, 6, "five", rule="en.cardinal")
    result = _prepared(
        source,
        "Keep 5.",
        source_replacements=(),
        protected_spans=(protected,),
    )

    monkeypatch.setattr(oracle, "iter_structured_candidates", lambda *args, **kwargs: (baseline,))
    monkeypatch.setattr(
        oracle, "resolve_structured_candidates", lambda text, candidates, **kwargs: candidates
    )

    analysis = oracle.analyze_candidate_oracle(source, "Keep five.", result, language="en")

    assert not analysis.scorable
    assert analysis.reason == "protected-candidate-overlap"


def test_analyze_candidate_oracle_skips_unicode_stage_changes() -> None:
    source = "A\u0301 5"
    result = _prepared(
        source,
        "Á five",
        source_replacements=(),
        stages=(PreparationStage("unicode", source, "Á 5"),),
    )

    analysis = oracle.analyze_candidate_oracle(source, "Á five", result, language="en")

    assert not analysis.scorable
    assert analysis.reason == "pre-structured-unicode-change"


def test_counterfactual_text_returns_none_for_narrower_baseline_overlap() -> None:
    source = "abc"
    result = _prepared(
        source,
        "alphabet",
        source_replacements=(
            SourceReplacement(
                0, 3, 0, 8, "abc", "alphabet", ("structured",), rule="sequence.product"
            ),
        ),
    )

    value = oracle.counterfactual_text(
        source,
        result,
        (Replacement(1, 2, "b", rule="sequence.product"),),
        language="en",
    )

    assert value is None


def test_conflict_components_and_paths_handle_transitive_overlap() -> None:
    candidates = (
        Replacement(0, 4, "A", rule="rule-a"),
        Replacement(2, 6, "B", rule="rule-b"),
        Replacement(5, 9, "C", rule="rule-c"),
    )

    components = oracle.conflict_components(candidates)
    paths = oracle.enumerate_component_paths(components[0])

    assert len(components) == 1
    assert any(
        [(item.start, item.end) for item in path] == [(0, 4), (5, 9)] for path in paths.paths
    )


def test_enumerate_component_paths_reports_truncation() -> None:
    component = tuple(
        Replacement(index, index + 2, str(index), rule=f"rule-{index}") for index in range(6)
    )

    paths = oracle.enumerate_component_paths(component, max_paths=3)

    assert paths.truncated
    assert len(paths.paths) == 3


def test_analyze_candidate_oracle_uses_deterministic_tie_break(monkeypatch) -> None:
    source = "Value X."
    baseline = Replacement(6, 7, "base wrong", rule="rule-z")
    better_rule = Replacement(6, 7, "beta", rule="rule-a")
    other_rule = Replacement(6, 7, "zeta", rule="rule-b")
    result = _prepared(
        source,
        "Value base wrong.",
        source_replacements=(
            SourceReplacement(6, 7, 6, 16, "X", "base wrong", ("structured",), rule=baseline.rule),
        ),
    )

    monkeypatch.setattr(
        oracle,
        "iter_structured_candidates",
        lambda *args, **kwargs: (baseline, better_rule, other_rule),
    )
    monkeypatch.setattr(
        oracle,
        "resolve_structured_candidates",
        lambda text, candidates, **kwargs: (baseline,) if len(candidates) == 3 else candidates,
    )

    analysis = oracle.analyze_candidate_oracle(source, "Value target.", result, language="en")

    assert analysis.gap_type == "selection"
    assert analysis.oracle_rules == ("rule-a",)
