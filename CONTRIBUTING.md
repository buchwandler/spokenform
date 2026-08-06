# Contributing

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy spokenform examples
python -m build
python -m twine check dist/*
```

Build the MyST Markdown documentation with:

```bash
python -m pip install -r docs/requirements.txt
sphinx-build -W --keep-going -b html docs docs/_build/html
```

Run the real spaCy integration tests after installing the optional dependency:

```bash
python -m pip install -e ".[dev,spacy]"
python -m pytest tests/test_spacy_integration.py
```

Use annotated Git tags such as `v0.1.0`; `setuptools-scm` derives package versions
from those tags.
