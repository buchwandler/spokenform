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

## Optional Lexhint integration

Install the optional provider and an explicit local runtime artifact. Lexhint `0.1.2 <= x < 0.3.0` is supported; Lexhint 0.1.x uses schema-7 runtime artifacts, while Lexhint 0.2.x requires a separately published schema-8 runtime artifact:

```bash
python -m pip install "spokenform[lexhint]"
lexhint dataset download <language> --variant runtime
```

Spokenform does not import Lexhint or download data unless the caller supplies a provider. The API accepts a structural `LexicalEvidenceProvider`, so applications may adapt Lexhint without coupling core normalization to that package. Provider language must match the Spokenform base language.
