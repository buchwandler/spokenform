import json
from types import SimpleNamespace

from benchmarks.proteno_compare import compare_runs
from benchmarks.proteno import _parser
from benchmarks.proteno_data import ProtenoCase, ProtenoExclusion
from benchmarks.proteno_eval import (
    _write_failures_markdown,
    _filter_failures_by_speech_wer,
    evaluate_and_write,
    evaluate_cases,
    literal_key,
    speech_key,
    speech_key_equivalent,
    word_error_rate,
)


def _markdown_failure(case_id, *, language="en", case_kind="normalization"):
    return {
        "id": case_id,
        "proteno_language": language,
        "case_kind": case_kind,
        "split": "train",
        "source_tokens": ("source", "tokens"),
        "original_text": "source text",
        "expected": "expected text",
        "actual": "actual text",
        "speech_wer": 0.5,
        "primary_rule": "en.cardinal",
        "failure_phase": "downstream_rendering",
        "error": None,
    }


def _case(language, index, source, expected, *, normalization=None):
    return ProtenoCase(
        language,
        index,
        "train",
        tuple(source.split()),
        source,
        expected,
        source != expected if normalization is None else normalization,
    )


def test_comparison_layers_and_wer():
    assert literal_key("  A\n  B  ") == "A B"
    assert speech_key("Hello, world!") == speech_key("Hello world")
    assert speech_key("Pay $5") != speech_key("Pay five")
    assert speech_key_equivalent("i ese be ene", language="es") == ("i", "s", "b", "n")
    assert word_error_rate(("one", "two"), ("one", "three")) == 0.5


def test_speech_wer_threshold_is_strict_and_optional():
    failures = tuple(
        {"id": case_id, "speech_wer": wer}
        for case_id, wer in (("low", 0.25), ("equal", 0.5), ("high", 0.75))
    )

    assert [item["id"] for item in _filter_failures_by_speech_wer(failures, 0.5)] == ["high"]
    assert _filter_failures_by_speech_wer(failures, None) == failures
    assert _parser().parse_args(["--speech-wer-threshold", "0.5"]).speech_wer_threshold == 0.5


def test_speech_wer_threshold_keeps_proteno_summary_metrics(tmp_path, monkeypatch):
    failures = tuple(
        {
            "id": case_id,
            "proteno_language": "en",
            "case_kind": "normalization",
            "split": "train",
            "source_tokens": ("source",),
            "original_text": "source",
            "expected": "expected",
            "actual": "actual",
            "speech_wer": wer,
            "primary_rule": "en.cardinal",
            "failure_phase": "downstream_rendering",
            "error": None,
        }
        for case_id, wer in (("low", 0.25), ("equal", 0.5), ("high", 0.75))
    )
    monkeypatch.setattr(
        "benchmarks.proteno_eval.evaluate_cases",
        lambda cases: ({"cases": 3, "error_count": 0}, failures),
    )

    output_dir, summary = evaluate_and_write((), output_root=tmp_path, speech_wer_threshold=0.5)

    assert summary["cases"] == 3
    assert summary["speech_wer_threshold"] == 0.5
    assert summary["stored_failure_count"] == 1
    stored = [json.loads(line)["id"] for line in (output_dir / "failures.jsonl").read_text().splitlines()]
    assert stored == ["high"]
    report = next(output_dir.glob("failures-en-normalization-*.md")).read_text()
    assert "#### high" in report
    assert "#### equal" not in report
    assert "#### low" not in report


def test_normalization_identity_mapping_and_provenance():
    cases = (
        _case("en", 1, "2", "two"),
        _case("en", 2, "hello", "hello", normalization=False),
    )
    calls = []

    def fake_prepare(text, **kwargs):
        calls.append((text, kwargs))
        if text == "2":
            edit = SimpleNamespace(
                rule="en.cardinal", stage="structured", source_start=0, source_end=1, source="2"
            )
            return SimpleNamespace(
                spoken_text="two",
                warnings=(),
                stages=(SimpleNamespace(name="structured", changed=True),),
                mapped_edits=(edit,),
                source_replacements=(),
            )
        return SimpleNamespace(spoken_text="hello", warnings=(), stages=(), mapped_edits=())

    summary, failures = evaluate_cases(cases, prepare_fn=fake_prepare)
    assert summary["normalization_cases"] == 1
    assert summary["normalization_success_count"] == 1
    assert summary["identity_cases"] == 1
    assert summary["identity_preserved_count"] == 1
    assert summary["identity_mutation_count"] == 0
    assert calls[0][1] == {"language": "en_US", "use_spacy": False}
    assert failures == ()


def test_identity_mutation_and_exception_isolation():
    cases = (
        _case("en", 1, "hello", "hello", normalization=False),
        _case("es", 2, "hola", "hola", normalization=False),
        _case("en", 3, "later", "later", normalization=False),
    )

    def fake_prepare(text, **kwargs):
        if text == "hola":
            raise RuntimeError("synthetic")
        return SimpleNamespace(spoken_text="changed" if text == "hello" else text, warnings=())

    summary, failures = evaluate_cases(cases, prepare_fn=fake_prepare)
    assert summary["error_count"] == 1
    assert summary["identity_mutation_count"] == 1
    assert summary["cases"] == 3
    assert [failure["id"] for failure in failures] == ["en:00001", "es:00002"]


def test_report_privacy_layout_and_metadata(tmp_path):
    cases = (_case("en", 1, "2", "wrong"),)
    exclusions = (ProtenoExclusion("en:00002", "en", 2, "train", "adapter_error", "bad tag"),)
    output_dir, summary = evaluate_and_write(cases, exclusions=exclusions, output_root=tmp_path)
    summary_json = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    encoded = json.dumps(summary_json)
    for secret_field in ("original_text", "source_tokens", "expected", "actual"):
        assert secret_field not in encoded
    failures = json.loads(
        (output_dir / "failures.jsonl").read_text(encoding="utf-8").splitlines()[0]
    )
    assert failures["original_text"] == "2"
    assert (output_dir / "failures.md").is_file()
    assert (output_dir / "excluded.jsonl").is_file()
    assert summary["dataset_commit"]
    assert summary["excluded_by_reason"] == {"adapter_error": 1}
    assert summary["failure_reports"]["index"] == "failures.md"
    assert summary["failure_reports"]["shards"]
    assert "original_text" not in (output_dir / "failures.md").read_text(encoding="utf-8")


def test_failure_markdown_is_split_into_bounded_linked_shards(tmp_path):
    failures = tuple(_markdown_failure(f"en:{index:05d}") for index in range(1, 13)) + (
        _markdown_failure("es:00001", language="es", case_kind="identity"),
    )

    manifest = _write_failures_markdown(failures, tmp_path, max_bytes=2048)
    index = (tmp_path / "failures.md").read_text(encoding="utf-8")

    assert len(manifest["shards"]) >= 3
    assert "Total failures: 13" in index
    assert "source text" not in index
    for report in manifest["shards"]:
        shard = tmp_path / report["path"]
        assert shard.is_file()
        assert shard.stat().st_size <= 2048
        assert report["path"] in index
        assert report["failure_count"] > 0
    rendered = "".join(
        (tmp_path / report["path"]).read_text(encoding="utf-8") for report in manifest["shards"]
    )
    for failure in failures:
        assert f"#### {failure['id']}" in rendered


def test_compare_runs_reports_metrics_and_stable_case_deltas(tmp_path):
    before = tmp_path / "before"
    after = tmp_path / "after"
    before.mkdir()
    after.mkdir()
    fields = {
        "semantic_failure_count": 3,
        "speech_exact_equivalent_count": 7,
        "literal_exact_count": 4,
        "identity_mutation_count": 2,
        "normalization_unchanged_miss_count": 3,
    }
    before_summary = fields
    after_summary = {key: value - 1 for key, value in fields.items()}
    for directory, summary, failures in (
        (before, before_summary, ("en:00001", "en:00002")),
        (after, after_summary, ("en:00002", "en:00003")),
    ):
        (directory / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
        (directory / "failures.jsonl").write_text(
            "".join(json.dumps({"id": failure}) + "\n" for failure in failures), encoding="utf-8"
        )
    comparison = compare_runs(before, after)
    assert comparison["summary_delta"]["identity_mutation_count"] == -1
    assert comparison["case_delta"] == {
        "resolved": ["en:00001"],
        "new_failures": ["en:00003"],
        "remaining": ["en:00002"],
    }
