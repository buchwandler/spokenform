"""Sphinx configuration for the spokenform documentation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

project = "spokenform"
author = "Holger Nahrstaedt"
copyright = "2026, Holger Nahrstaedt"

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]
source_suffix = {".md": "markdown"}
master_doc = "index"
exclude_patterns = ["_build"]
html_theme = "sphinx_rtd_theme"
autodoc_typehints = "description"
myst_enable_extensions = ["colon_fence", "deflist"]
