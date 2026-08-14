from __future__ import annotations

from dataclasses import dataclass

from benchmarks.google_tn_eval import evaluate
from benchmarks.google_tn_format import assemble_case
from spokenform.models import SourceReplacement


def _case(written: str, spoken: str, semiotic_class: str = "DATE"):
    return assemble_case(
        [
            __import__("benchmarks.google_tn_format", fromlist=["GoogleTNRow"]).GoogleTNRow(
                semiotic_class, written, spoken, 1, 0, len(written)
            )
        ],
        source_file="output-00099-of-00100",
        shard=99,
        sentence_index=1,
    )


@dataclass(frozen=True)
class FakeResult:
    spoken_text: str
    source_replacements: tuple = ()
    stages: tuple = ()

    def map_source_span(self, start: int, end: int) -> tuple[int, int]:
        return (0, len(self.spoken_text))


def test_outcomes_distinguish_correct_miss_wrong_and_identity_mutation() -> None:
    cases = [
        _case("2005", "two thousand five"),
        _case("2005", "two thousand five", "CARDINAL"),
        _case("2005", "two thousand five"),
        _case("plain", "<self>", "PLAIN"),
    ]
    outputs = [
        "two thousand five",
        "2005",
        "twenty five",
        "changed",
    ]

    def fake_prepare(text: str, **kwargs):
        return FakeResult(outputs.pop(0))

    summary, rows, failures = evaluate(cases, prepare_fn=fake_prepare)
    spans = [row for row in rows if row.get("record_type") == "span"]
    assert [row["normalization_outcome"] for row in spans] == [
        "correct-transform",
        "transform-miss",
        "wrong-transform",
        "identity-mutation",
    ]
    assert summary["correct_transform_count"] == 1
    assert summary["transform_miss_count"] == 1
    assert summary["wrong_transform_count"] == 1
    assert summary["identity_mutation_count"] == 1
    assert len(failures) == 3


def test_evaluator_calls_prepare_without_upstream_class_oracle() -> None:
    seen: list[dict] = []

    def fake_prepare(text: str, **kwargs):
        seen.append(kwargs)
        return FakeResult("spoken")

    evaluate([_case("2005", "spoken", "DATE")], prepare_fn=fake_prepare)
    assert seen == [
        {
            "language": "en_US",
            "use_spacy": False,
            "symbol_mode": "none",
            "normalize_literals": False,
            "generic_acronym_mode": "known_only",
            "generic_acronym_case": "upper",
            "long_number_mode": "preserve",
        }
    ]


def test_presentation_only_and_class_aggregation() -> None:
    case = _case("2005", "two thousand five", "DATE")

    def fake_prepare(text: str, **kwargs):
        return FakeResult("Two thousand five")

    summary, rows, _ = evaluate([case], prepare_fn=fake_prepare)
    span = next(row for row in rows if row.get("record_type") == "span")
    assert span["normalization_outcome"] == "presentation-only"
    assert summary["by_semiotic_class"]["DATE"]["count"] == 1


def test_runtime_exception_is_recorded_and_does_not_stop_stream() -> None:
    calls = 0

    def fake_prepare(text: str, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("boom")
        return FakeResult("two thousand five")

    summary, rows, failures = evaluate(
        [_case("2005", "two thousand five"), _case("2005", "two thousand five")],
        prepare_fn=fake_prepare,
    )
    assert summary["evaluated"] == 2
    assert summary["runtime_error_count"] == 1
    assert len(failures) == 1


def test_replacement_crossing_row_boundary_is_explicitly_ambiguous() -> None:
    case = assemble_case(
        [
            __import__("benchmarks.google_tn_format", fromlist=["GoogleTNRow"]).GoogleTNRow(
                "DATE", "2005", "two thousand five", 1, 0, 4
            ),
            __import__("benchmarks.google_tn_format", fromlist=["GoogleTNRow"]).GoogleTNRow(
                "PLAIN", ".", "<self>", 2, 5, 6
            ),
        ],
        source_file="output-00099-of-00100",
        shard=99,
        sentence_index=2,
    )

    def fake_prepare(text: str, **kwargs):
        return FakeResult(
            "two thousand five .",
            source_replacements=(
                SourceReplacement(
                    0, 6, 0, 20, "2005 .", "two thousand five .", ("structured",), rule="sequence.date"
                ),
            ),
        )

    summary, rows, _ = evaluate([case], prepare_fn=fake_prepare)
    spans = [row for row in rows if row.get("record_type") == "span"]
    assert all(row["normalization_outcome"] == "mapping-ambiguous" for row in spans)
    assert summary["ambiguous_span_mapping_count"] == 2
