# Contributing

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy spokenform
python -m build
python -m twine check dist/*
```

Use annotated Git tags such as `v0.1.0`; `setuptools-scm` derives package versions
from those tags.
