from __future__ import annotations

import hashlib

import pytest

from benchmarks.google_tn_data import (
    GOOGLE_TN_TEST_FILE,
    GOOGLE_TN_TEST_LINE_LIMIT,
    discover_source_files,
    file_sha256,
    iter_cases,
    shard_number,
    source_metadata,
)


def _write_shard(root, name: str, sentences: int) -> None:
    lines: list[str] = []
    for index in range(sentences):
        lines.extend(
            [
                f"PLAIN\tword{index}\t<self>\n",
                "DATE\t2005\ttwo thousand five\n",
                "<eos>\t<eos>\n",
            ]
        )
    (root / name).write_text("".join(lines), encoding="utf-8")


def test_shard_discovery_and_split_policy(tmp_path) -> None:
    _write_shard(tmp_path, GOOGLE_TN_TEST_FILE, 2)
    _write_shard(tmp_path, "output-00001-of-00100", 1)
    assert discover_source_files(tmp_path, split="test") == (tmp_path / GOOGLE_TN_TEST_FILE,)
    assert discover_source_files(tmp_path, split="test-full") == (tmp_path / GOOGLE_TN_TEST_FILE,)
    assert [path.name for path in discover_source_files(tmp_path, split="all")] == [
        "output-00001-of-00100",
        GOOGLE_TN_TEST_FILE,
    ]
    assert shard_number("output-00099-of-00100") == 99
    assert shard_number("custom-test") is None
    assert GOOGLE_TN_TEST_LINE_LIMIT == 100002


def test_ids_are_stable_when_class_and_limit_filters_change(tmp_path) -> None:
    _write_shard(tmp_path, GOOGLE_TN_TEST_FILE, 3)
    all_cases = list(iter_cases(tmp_path, split="test-full"))
    date_cases = list(iter_cases(tmp_path, split="test-full", semiotic_class="DATE", limit=1))
    assert [case.case_id for case in all_cases] == [
        "en:099:000000",
        "en:099:000001",
        "en:099:000002",
    ]
    assert date_cases[0].case_id == all_cases[0].case_id


def test_case_filter_does_not_renumber_source_ids(tmp_path) -> None:
    _write_shard(tmp_path, GOOGLE_TN_TEST_FILE, 3)
    selected = list(iter_cases(tmp_path, split="test-full", case_id="en:099:000002"))
    assert [case.case_id for case in selected] == ["en:099:000002"]


def test_file_hash_and_metadata_are_deterministic(tmp_path) -> None:
    _write_shard(tmp_path, GOOGLE_TN_TEST_FILE, 1)
    path = tmp_path / GOOGLE_TN_TEST_FILE
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert file_sha256(path) == expected
    metadata = source_metadata(path, split="test")
    assert metadata["source_file_sha256"] == expected
    assert metadata["selected_line_end"] == GOOGLE_TN_TEST_LINE_LIMIT
    assert metadata["surface_policy"] == "field_join_v1"


def test_default_test_line_limit_is_physical_and_can_fail_on_partial_sentence(tmp_path) -> None:
    path = tmp_path / GOOGLE_TN_TEST_FILE
    path.write_text("PLAIN\tword\t<self>\n", encoding="utf-8")
    with pytest.raises(ValueError, match="EOF"):
        list(iter_cases(tmp_path, split="test"))
