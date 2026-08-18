from __future__ import annotations

import hashlib
import json

import pytest

from benchmarks import async_tn_data as data


def english_record(**overrides):
    record = {
        "row_index": 42,
        "original_text": "Pay $5 on 05/20/2023.",
        "normalized_text": "Pay five dollars on May twentieth twenty twenty three.",
        "categories": ["currency", "date", "future_category"],
        "units": [
            {"text": "$5", "norm_category": "currency"},
            {"text": "05/20/2023", "norm_category": "date"},
        ],
    }
    record.update(overrides)
    return record


def multilingual_record(**overrides):
    record = {
        "sentence_id": "curated-7",
        "languages": {
            "de": {
                "original_text": "Am 05.01.2024.",
                "normalized_text": "Am fünften Januar zweitausendvierundzwanzig.",
                "categories": ["date"],
                "units": [{"text": "05.01.2024", "norm_category": "date"}],
            },
            "pt": {
                "original_text": "É o dia 5.",
                "normalized_text": "É o dia cinco.",
                "units": [{"text": "5", "norm_category": "cardinal"}],
            },
        },
    }
    record.update(overrides)
    return record


def test_parse_english_preserves_unknown_categories_and_stable_ids():
    cases, exclusions = data.parse_english([english_record()])
    assert not exclusions
    assert cases[0].case_id == "english:42"
    assert cases[0].spokenform_language == "en_US"
    assert cases[0].categories[-1] == "future_category"
    assert cases[0].units[0].source_start == 4
    assert cases[0].units[0].span_source == "resolved-exact"
    assert cases[0].unit_id(0) == "english:42:unit:0"


def test_parse_multilingual_maps_supported_languages():
    cases, exclusions = data.parse_multilingual([multilingual_record()])
    assert not exclusions
    assert [(case.case_id, case.spokenform_language) for case in cases] == [
        ("multilingual:de:curated-7", "de"),
        ("multilingual:pt:curated-7", "pt"),
    ]


def test_unknown_multilingual_language_is_quarantined():
    record = multilingual_record()
    record["languages"]["xx"] = record["languages"]["de"]
    cases, exclusions = data.parse_multilingual([record])
    assert len(cases) == 2
    assert [(item.language, item.reason) for item in exclusions] == [("xx", "unsupported-language")]


def test_upstream_offsets_are_validated():
    record = english_record(
        units=[{"text": "$5", "norm_category": "currency", "start": 4, "end": 6}]
    )
    cases, exclusions = data.parse_english([record])
    assert not exclusions
    assert cases[0].units[0].span_source == "upstream"


def test_invalid_offsets_fall_back_when_unique():
    record = english_record(
        units=[{"text": "$5", "norm_category": "currency", "start": 0, "end": 2}]
    )
    cases, exclusions = data.parse_english([record])
    assert not exclusions
    assert cases[0].units[0].source_start == 4


def test_repeated_units_are_disambiguated_in_unit_order():
    record = {
        "row_index": 1,
        "original_text": "ID 7 and 7.",
        "normalized_text": "ID seven and seven.",
        "units": [
            {"text": "7", "norm_category": "cardinal"},
            {"text": "7", "norm_category": "cardinal"},
        ],
    }
    cases, exclusions = data.parse_english([record])
    assert not exclusions
    assert [(unit.source_start, unit.source_end) for unit in cases[0].units] == [(3, 4), (9, 10)]


def test_genuinely_ambiguous_span_is_quarantined():
    record = {
        "row_index": 1,
        "original_text": "7 or 7",
        "normalized_text": "seven or seven",
        "units": [{"text": "7", "norm_category": "cardinal"}],
    }
    cases, exclusions = data.parse_english([record])
    assert not cases
    assert exclusions[0].reason == "unit-source-span-ambiguous"


@pytest.mark.parametrize(
    ("record", "reason"),
    [
        (english_record(units=[]), "missing-unit-annotations"),
        (english_record(units=None), "missing-unit-annotations"),
        (
            english_record(units=[{"text": "missing", "norm_category": "date"}]),
            "unit-source-span-not-found",
        ),
        (
            english_record(
                original_text="77",
                normalized_text="seventy seven",
                units=[
                    {"text": "77", "norm_category": "cardinal", "start": 0, "end": 2},
                    {"text": "7", "norm_category": "cardinal", "start": 1, "end": 2},
                ],
            ),
            "unit-source-span-overlap",
        ),
        (english_record(units=[{"norm_category": "date"}]), "invalid-source-record"),
    ],
)
def test_source_irregularities_are_quarantined(record, reason):
    cases, exclusions = data.parse_english([record])
    assert not cases
    assert exclusions[0].reason == reason


def test_malformed_record_does_not_abort_other_records():
    cases, exclusions = data.parse_english(["bad", english_record()])
    assert [case.case_id for case in cases] == ["english:42"]
    assert exclusions[0].reason == "invalid-source-record"


def test_filters_preserve_ids():
    cases, _ = data.parse_english([english_record(row_index=1), english_record(row_index=2)])
    assert [case.case_id for case in data.filter_cases(cases, category="future_category")] == [
        "english:1",
        "english:2",
    ]
    assert [case.case_id for case in data.filter_cases(cases, limit=1)] == ["english:1"]
    assert [case.case_id for case in data.filter_cases(cases, case_id="english:2")] == ["english:2"]


def test_cache_download_records_hashes_and_commit(monkeypatch, tmp_path):
    payloads = {
        name.rsplit("/", 1)[-1]: json.dumps([]).encode()
        if name.endswith("sentences.json")
        else b"{}"
        for name in data._required_files((data.ENGLISH_SUITE,))
    }

    class Response:
        def __init__(self, payload):
            self.payload = payload

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return self.payload

    monkeypatch.setattr(
        data,
        "urlopen",
        lambda url, timeout: Response(payloads[url.split("/data/", 1)[1]]),
    )
    root = data.ensure_data((data.ENGLISH_SUITE,), cache_dir=tmp_path)
    metadata = json.loads((root / "metadata.json").read_text())
    assert metadata["source_commit"] == data.SOURCE_COMMIT
    assert set(metadata["files"]) == set(data._required_files((data.ENGLISH_SUITE,)))
    for relative_path, record in metadata["files"].items():
        assert record["sha256"] == hashlib.sha256((root / relative_path).read_bytes()).hexdigest()


def test_offline_cache_miss_is_clear(tmp_path):
    with pytest.raises(FileNotFoundError, match="Offline Async TN cache is missing"):
        data.ensure_data((data.ENGLISH_SUITE,), cache_dir=tmp_path, offline=True)


def test_offline_cache_uses_existing_files(tmp_path):
    cache = data.cache_path(tmp_path)
    for relative_path in data._required_files((data.ENGLISH_SUITE,)):
        path = cache / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[]" if relative_path.endswith("sentences.json") else "{}")
    data.ensure_data((data.ENGLISH_SUITE,), cache_dir=tmp_path, offline=True)
    assert data.source_metadata(tmp_path)["source_commit"] == data.SOURCE_COMMIT


def test_language_validation():
    assert data.spokenform_language("en") == "en_US"
    with pytest.raises(ValueError, match="unsupported Async TN language"):
        data.spokenform_language("xx")
    with pytest.raises(ValueError, match="unsupported Async TN suite"):
        data._required_files(("other",))
