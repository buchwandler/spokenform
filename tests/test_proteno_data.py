import pickle

import pytest

import benchmarks.proteno_data as data


def _write_pair(tmp_path, language="en", count=5):
    source = [["row", str(index)] for index in range(count)]
    target = ["row " + str(index) for index in range(count)]
    data.data_path(language, "unnorm", tmp_path).parent.mkdir(parents=True, exist_ok=True)
    with data.data_path(language, "unnorm", tmp_path).open("wb") as handle:
        pickle.dump(source, handle)
    with data.data_path(language, "norm", tmp_path).open("wb") as handle:
        pickle.dump(target, handle)
    return source, target


def test_cache_path_and_language_validation(tmp_path):
    assert data.PROTENO_COMMIT in str(data.cache_path(tmp_path))
    assert (
        data.data_path("en", "unnorm", tmp_path).parent
        != data.data_path("es", "unnorm", tmp_path).parent
    )
    assert data.selected_languages() == ("en", "es")
    with pytest.raises(ValueError, match="Unsupported Proteno language"):
        data.selected_languages("ta")


def test_license_and_offline_gates(tmp_path):
    with pytest.raises(PermissionError, match="--accept-license"):
        data.ensure_data(("en",), cache_dir=tmp_path)
    with pytest.raises(FileNotFoundError, match="Offline Proteno cache"):
        data.ensure_data(("en",), cache_dir=tmp_path, offline=True)


def test_git_blob_verification_and_corrupt_cache(tmp_path):
    payload = b"synthetic"
    metadata = data.ProtenoFile("x", data.git_blob_sha(payload), len(payload))
    data.verify_payload(payload, metadata)
    with pytest.raises(ValueError, match="size mismatch"):
        data.verify_payload(payload + b"!", metadata)
    with pytest.raises(ValueError, match="SHA mismatch"):
        data.verify_payload(b"different", metadata)


def test_restricted_pickle_loads_primitives_and_rejects_globals(tmp_path):
    primitive = tmp_path / "primitive.pkl"
    primitive.write_bytes(pickle.dumps([["hello"]]))
    assert data._load_pickle(primitive) == [["hello"]]

    unsafe = tmp_path / "unsafe.pkl"
    unsafe.write_bytes(pickle.dumps(ValueError("synthetic")))
    with pytest.raises(ValueError, match="class loading"):
        data._load_pickle(unsafe)


def test_pair_validation_and_stable_ids(monkeypatch, tmp_path):
    _write_pair(tmp_path, count=5)
    monkeypatch.setitem(data.PROTENO_DATASET_COUNTS, "en", 5)
    cases = data.load_cases(("en",), cache_dir=tmp_path)
    assert [case.case_id for case in cases] == [f"en:{index:05d}" for index in range(1, 6)]
    assert [case.case_id for case in data.load_cases(("en",), cache_dir=tmp_path, limit=2)] == [
        "en:00001",
        "en:00002",
    ]
    assert [
        case.case_id for case in data.load_cases(("en",), cache_dir=tmp_path, split="test")
    ] == [
        "en:00004",
        "en:00005",
    ]

    target = ["only one"]
    with data.data_path("en", "norm", tmp_path).open("wb") as handle:
        pickle.dump(target, handle)
    with pytest.raises(ValueError, match="pair length mismatch.*source count 5.*target count 1"):
        data.load_pair("en", cache_dir=tmp_path, validate_count=False)


def test_shape_mismatch_is_rejected(tmp_path):
    path = data.data_path("en", "unnorm", tmp_path)
    path.parent.mkdir(parents=True)
    path.write_bytes(pickle.dumps([{"not": "tokens"}]))
    with pytest.raises(ValueError, match="unsupported primitive|sequence of strings"):
        data._validate_source(data._load_pickle(path), path)


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        (["$", "12", ".", "50"], "$12.50"),
        (["12", "/", "03", "/", "2020"], "12/03/2020"),
        (["3", ":", "30"], "3:30"),
        (["U", ".", "S", "."], "U.S."),
        (["(", "42", "%", ")"], "(42%)"),
        (["300", ":", "29", "–", "30"], "300:29–30"),
    ],
)
def test_detokenize_preserves_tn_adjacency(tokens, expected):
    assert data.detokenize(tokens) == expected


def test_spanish_projection_and_fail_closed_markup():
    assert data.project_spanish('<error what="trescientos">300</error>') == "trescientos"
    assert (
        data.project_spanish('uno <error what="dos">2</error> <error what="tres">3</error>')
        == "uno dos tres"
    )
    assert data.project_spanish('A <lang id="en">Science</lang> B') == "A B"
    projected, notes = data.project_spanish_with_metadata(
        'A <lang id="en">Science</lang> <error what="dos">2</error>'
    )
    assert projected == "A dos"
    assert notes == ("removed-lang-span", "replaced-error-span")
    with pytest.raises(ValueError, match="missing required what"):
        data.project_spanish("<error>300</error>")
    with pytest.raises(ValueError, match="Unknown Spanish"):
        data.project_spanish("<unknown>text</unknown>")
    with pytest.raises(ValueError, match="Malformed Spanish"):
        data.project_spanish('<error what="x">1')


def test_url_and_adapter_exclusions_are_explicit(monkeypatch, tmp_path):
    source = [["visit", "https://example.com"]]
    target = ["visita"]
    data.data_path("es", "unnorm", tmp_path).parent.mkdir(parents=True, exist_ok=True)
    for kind, value in (("unnorm", source), ("norm", target)):
        with data.data_path("es", kind, tmp_path).open("wb") as handle:
            pickle.dump(value, handle)
    monkeypatch.setitem(data.PROTENO_DATASET_COUNTS, "es", 1)
    cases, exclusions = data.load_cases_with_exclusions(
        ("es",), cache_dir=tmp_path, validate_count=True
    )
    assert cases == ()
    assert exclusions[0].reason == "upstream_ignored_url"
