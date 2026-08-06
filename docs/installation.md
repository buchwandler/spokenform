# Installation

## Runtime

```bash
python -m pip install spokenform
```

For development from a checkout:

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

On Windows, activate with `.venv\Scripts\activate`.

## Optional spaCy support

```bash
python -m pip install "spokenform[spacy]"
python -m spacy download de_core_news_sm
```

The spaCy library and trained pipeline are separate packages. Installing the
`spacy` extra does not install or download a language pipeline.

## Documentation

The documentation source uses MyST Markdown. Install the supplied requirements
file together with the project:

```bash
python -m pip install -e .
python -m pip install -r docs/requirements.txt
sphinx-build -W -b html docs docs/_build/html
```
