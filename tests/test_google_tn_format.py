from __future__ import annotations

import io

import pytest

from benchmarks.google_tn_format import (
    SURFACE_POLICY,
    assemble_case,
    iter_tsv_sentences,
    project_spoken,
)


def test_parser_reads_rows_and_eos_with_exact_joined_spans() -> None:
    rows = next(
        iter_tsv_sentences(
            io.StringIO(
                "PLAIN\tThe\t<self>\n"
                "DATE\t2005\ttwo thousand five\n"
                "PUNCT\t.\t<self>\n"
                "<eos>\t<eos>\n"
            )
        )
    )
    case = assemble_case(rows, source_file="output-00099-of-00100", shard=99, sentence_index=123)
    assert case.original_text == "The 2005 ."
    assert case.normalized_text == "The two thousand five ."
    assert [(row.source_line, row.source_start, row.source_end) for row in case.rows] == [
        (1, 0, 3),
        (2, 4, 8),
        (3, 9, 10),
    ]
    assert [case.original_text[row.source_start : row.source_end] for row in case.rows] == [
        row.written for row in case.rows
    ]
    assert case.case_id == "en:099:000123"
    assert case.has_normalization
    assert SURFACE_POLICY == "field_join_v1"


def test_self_sil_and_compatibility_sil_are_identity_for_forward_tn() -> None:
    assert project_spoken("<self>", ".") == "."
    assert project_spoken("sil", ".") == "."
    assert project_spoken("<sil>", ".") == "."
    rows = next(iter_tsv_sentences(["PUNCT\t.\tsil\n", "<eos>\t<eos>\n"]))
    assert rows[0].is_identity
    assert rows[0].expected_spoken == "."


def test_internal_spaces_stay_inside_one_written_and_spoken_field() -> None:
    rows = next(iter_tsv_sentences(["PLAIN\tcompany 's\t<self>\n", "<eos>\t<eos>\n"]))
    assert rows[0].written == "company 's"
    assert rows[0].source_end - rows[0].source_start == len("company 's")


@pytest.mark.parametrize(
    "text",
    [
        "DATE\t2005\n<eos>\t<eos>\n",
        "DATE\t2005\ttwo thousand five\textra\n<eos>\t<eos>\n",
        "\t2005\ttwo thousand five\n<eos>\t<eos>\n",
        "CUSTOM\tvalue\t<self>\n",
    ],
)
def test_malformed_or_unterminated_input_fails_closed(text: str) -> None:
    with pytest.raises(ValueError):
        tuple(iter_tsv_sentences(io.StringIO(text)))


def test_unknown_classes_are_preserved() -> None:
    rows = next(iter_tsv_sentences(["CUSTOM_CLASS\tvalue\tspoken\n", "<eos>\t<eos>\n"]))
    assert rows[0].semiotic_class == "CUSTOM_CLASS"


def test_empty_sentence_boundary_is_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        tuple(iter_tsv_sentences(["<eos>\t<eos>\n"]))


def test_relaxed_mode_can_finalize_at_eof() -> None:
    rows = tuple(iter_tsv_sentences(["PLAIN\tHello\t<self>\n"], strict=False))
    assert rows[0][0].written == "Hello"
