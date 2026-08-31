from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).parents[1]
KOKORO_TESTS = ROOT.parent / "kokorog2p" / "tests"
MANIFEST = ROOT / "tests" / "data" / "kokorog2p_semantic_transfer_manifest.json"
TRACKED_MODULES = (
    "test_en_abbreviations.py",
    "test_guarded_abbreviation_merging.py",
    "test_abbreviation_customization.py",
    "test_de_normalizer.py",
    "test_en_numbers.py",
    "test_temperature_normalization.py",
    "test_cs_normalizer.py",
    "test_th_normalizer.py",
    "test_spokenform_migration.py",
    "test_pipeline_api.py",
)


def _test_origins(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    origins: set[str] = set()

    def visit(nodes: list[ast.stmt], prefix: str = "") -> None:
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                visit(node.body, f"{prefix}{node.name}.")
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test_"
            ):
                origins.add(f"kokorog2p:tests/{path.name}::{prefix}{node.name}")

    visit(tree.body)
    return origins


def test_transfer_manifest_is_complete_and_classified() -> None:
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert isinstance(rows, list) and rows
    assert {row["classification"] for row in rows} <= {
        "ported",
        "already-covered",
        "g2p-only",
    }
    assert all(row["origin"].startswith("kokorog2p:") for row in rows)
    assert all(row["reason"] for row in rows)
    assert all(row["destination"] is None or row["destination"] for row in rows)

    manifest_origins = {row["origin"] for row in rows}
    expected_origins = {
        origin for module in TRACKED_MODULES for origin in _test_origins(KOKORO_TESTS / module)
    }
    assert expected_origins <= manifest_origins


def test_live_kokoro_test_data_files_are_audited() -> None:
    rows = json.loads(MANIFEST.read_text(encoding="utf-8"))
    origins = {row["origin"] for row in rows}
    for path in sorted((*KOKORO_TESTS.glob("data/*.json"), *KOKORO_TESTS.glob("data/*.jsonl"))):
        assert f"kokorog2p:tests/{path.relative_to(KOKORO_TESTS)}" in origins
