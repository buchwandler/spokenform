from __future__ import annotations

from dataclasses import replace

import pytest

from benchmarks import async_tn_eval as evaluator
from benchmarks.async_tn_data import AsyncTNCase, AsyncTNUnit
from benchmarks.async_tn_eval import build_expected_mapping, project_expected_unit
from spokenform import prepare as real_prepare


def unit(source: str, text: str, start: int, index: int = 0) -> AsyncTNUnit:
    return AsyncTNUnit(index, text, "test", start, start + len(text))


def case(source: str, expected: str, item: AsyncTNUnit) -> AsyncTNCase:
    return AsyncTNCase(
        "english:test",
        "english",
        "en",
        "en_US",
        source,
        expected,
        (item,),
        ("test",),
        "test",
    )


def test_simple_replacement_projects_to_expected_unit():
    source = "pay 5 now"
    item = unit(source, "5", 4)
    projection = project_expected_unit(case(source, "pay five now", item), item)
    assert projection.text == "five"
    assert not projection.ambiguous


def test_adjacent_units_project_independently():
    source = "5 6"
    first = unit(source, "5", 0, 0)
    second = unit(source, "6", 2, 1)
    target = case(source, "five six", first)
    mapping = build_expected_mapping(source, target.normalized_text)
    assert project_expected_unit(target, first, mapping).text == "five"
    assert project_expected_unit(replace(target, units=(second,)), second, mapping).text == "six"


def test_repeated_values_use_source_coordinates():
    source = "7 and 7"
    first = unit(source, "7", 0, 0)
    second = unit(source, "7", 6, 1)
    target = case(source, "seven and seven", first)
    mapping = build_expected_mapping(source, target.normalized_text)
    assert project_expected_unit(target, first, mapping).text == "seven"
    assert project_expected_unit(replace(target, units=(second,)), second, mapping).text == "seven"


@pytest.mark.parametrize(
    ("source", "expected", "start", "end", "text"),
    [
        ("x 5", "hello x five", 2, 3, "five"),
        ("x 5", "5", 2, 3, "5"),
        ("x 5 y", "x five y", 2, 3, "five"),
    ],
)
def test_insertions_deletions_and_outside_edits_shift_coordinates(
    source: str, expected: str, start: int, end: int, text: str
):
    item = unit(source, source[start:end], start)
    projection = project_expected_unit(case(source, expected, item), item)
    assert projection.text == text
    assert not projection.ambiguous


def test_replacement_inside_unit_is_scorable():
    source = "ID ABC"
    item = unit(source, "ABC", 3)
    projection = project_expected_unit(case(source, "ID letters", item), item)
    assert projection.text == "letters"
    assert not projection.ambiguous


def test_edit_crossing_left_boundary_is_ambiguous():
    source = "old 5 tail"
    item = unit(source, "5", 4)
    projection = project_expected_unit(case(source, "new", item), item)
    assert projection.ambiguous


def test_edit_crossing_right_boundary_is_ambiguous():
    source = "5 old tail"
    item = unit(source, "5", 0)
    projection = project_expected_unit(case(source, "new", item), item)
    assert projection.ambiguous


def test_one_diff_block_crossing_two_units_marks_both_ambiguous():
    source = "A 5 B 6 C"
    first = unit(source, "5", 2, 0)
    second = unit(source, "6", 6, 1)
    expected = "A X C"
    mapping = build_expected_mapping(source, expected)
    assert project_expected_unit(case(source, expected, first), first, mapping).ambiguous
    assert project_expected_unit(case(source, expected, second), second, mapping).ambiguous


def test_punctuation_around_unit_does_not_make_it_ambiguous():
    source = "at 5."
    item = unit(source, "5", 3)
    projection = project_expected_unit(case(source, "at five.", item), item)
    assert projection.text == "five"
    assert not projection.ambiguous


def test_mapping_reproduces_expected_text():
    mapping = build_expected_mapping("a 5 b", "a five b")
    assert mapping.expected_text == "a five b"
    assert mapping.offset_map.map_source_span(2, 3) == (2, 6)


def test_actual_projection_uses_prepared_source_mapping():
    result = real_prepare("pay 5", language="en_US")
    item = unit("pay 5", "5", 4)
    projection = evaluator.project_actual_unit(result, item)
    assert projection.text
    assert not projection.ambiguous


def test_actual_projection_crossing_unit_boundary_is_ambiguous():
    result = real_prepare("7 AM", language="en_US")
    item = unit("7 AM", "AM", 2)
    projection = evaluator.project_actual_unit(result, item)
    assert projection.text == "seven A M"
    assert projection.ambiguous


def test_evaluator_uses_one_runtime_call_without_category_oracle(monkeypatch):
    calls = []
    original_prepare = evaluator.prepare

    def wrapped(text, **kwargs):
        calls.append((text, kwargs))
        return original_prepare(text, **kwargs)

    monkeypatch.setattr(evaluator, "prepare", wrapped)
    test_case = case("pay 5", "pay five", unit("pay 5", "5", 4))
    summary, rows, units, failures = evaluator.evaluate_cases([test_case])
    assert len(calls) == 1
    assert "category" not in calls[0][1]
    assert summary["counts"]["units_total"] == 1
    assert rows[0]["case_id"] == "english:test"
    assert units[0]["unit_id"] == "english:test:unit:0"
    assert isinstance(failures, tuple)


def test_runtime_errors_are_isolated_per_case(monkeypatch):
    original_prepare = evaluator.prepare

    def failing_prepare(text, **kwargs):
        if "boom" in text:
            raise RuntimeError("synthetic failure")
        return original_prepare(text, **kwargs)

    monkeypatch.setattr(evaluator, "prepare", failing_prepare)
    good = case("pay 5", "pay five", unit("pay 5", "5", 4))
    bad = case("boom 5", "boom five", unit("boom 5", "5", 5))
    summary, rows, units, _ = evaluator.evaluate_cases([good, bad])
    assert len(rows) == 2
    assert rows[1]["outcome"] == "runtime-error"
    assert summary["counts"]["runtime_error_cases"] == 1
    assert sum(item["outcome"] == "runtime-error" for item in units) == 1


def test_ambiguous_unit_rows_keep_sentence_and_projection_values_separate():
    item = unit("7 AM", "AM", 2)
    summary, rows, units, _ = evaluator.evaluate_cases([case("7 AM", "seven A M", item)])
    assert summary["counts"]["units_total"] == 1
    assert rows[0]["actual"] == "seven A M"
    assert units[0]["expected"] == "A M"
    assert units[0]["actual"] == "seven A M"
    assert units[0]["actual_mapping_ambiguous"] is True
    assert units[0]["outcome"] == "mapping-ambiguous"


def test_unit_and_sentence_metrics_keep_separate_denominators():
    item = unit("5", "5", 0)
    test_case = case("5", "five", item)
    summary, rows, units, _ = evaluator.evaluate_cases([test_case])
    assert summary["counts"]["units_total"] == 1
    assert summary["counts"]["units_scorable"] == 1
    assert summary["categories"]["test"]["units_total"] == 1
    assert "speech_wer" in rows[0]
    assert "speech_wer" in units[0]
    assert rows[0]["all_units_correct"] is not None


def test_profile_changes_configuration_without_changing_category_arguments():
    test_case = case("5", "five", unit("5", "5", 0))
    default, _, _, _ = evaluator.evaluate_cases([test_case], profile="default")
    extended, _, _, _ = evaluator.evaluate_cases([test_case], profile="extended")
    assert default["normalize_literals"] is False
    assert extended["normalize_literals"] is True


def test_candidate_oracle_adds_sentence_level_fields():
    test_case = case("5", "five", unit("5", "5", 0))
    summary, rows, units, _ = evaluator.evaluate_cases([test_case], candidate_oracle=True)
    assert "candidate_count" in rows[0]
    assert "oracle_gap_type" in rows[0]
    assert "oracle_changed_span" in units[0]
    assert summary["candidate_oracle"]["enabled"] is True
