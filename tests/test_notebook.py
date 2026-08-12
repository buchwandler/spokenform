"""Regression checks for the committed Binder notebook."""

from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK = Path(__file__).parents[1] / "notebooks" / "spokenform_playground.ipynb"


def _notebook() -> dict:
    return json.loads(NOTEBOOK.read_text(encoding="utf-8"))


def _source(*, code_only: bool = False) -> str:
    cells = _notebook()["cells"]
    if code_only:
        cells = [cell for cell in cells if cell.get("cell_type") == "code"]
    return "\n".join("".join(cell.get("source", [])) for cell in cells)


def test_notebook_is_valid_basic_v4_shape() -> None:
    notebook = _notebook()

    assert notebook["nbformat"] == 4
    assert isinstance(notebook["cells"], list)
    assert notebook["cells"]
    assert notebook["metadata"]["kernelspec"]["name"] == "python3"


def test_notebook_is_committed_without_outputs() -> None:
    for cell in _notebook()["cells"]:
        if cell.get("cell_type") != "code":
            continue
        assert cell.get("outputs", []) == []
        assert cell.get("execution_count") is None


def test_notebook_uses_public_spokenform_surface() -> None:
    source = _source(code_only=True)

    assert "from spokenform.recognizers" not in source
    assert "from spokenform.locales" not in source
    assert "pip install spokenform" not in source
    assert "spacy download" not in source


def test_notebook_contains_binder_playground() -> None:
    source = _source()

    for required in (
        "ipywidgets",
        "symbol_mode",
        "generic_acronym_case",
        "ProtectedSpan",
        "render_changes",
        "map_source_span",
        "normalize_literals",
        "source_replacements",
        "on_click",
    ):
        assert required in source
