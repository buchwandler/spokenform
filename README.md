# spokenform

`spokenform` converts written text into a readable form intended for speech systems.
It is a text-to-text frontend: raw text in, reviewable spoken text out.

The MVP combines:

- context-aware abbreviation and numeric-unit expansion from `abbr2words`;
- number, date, time, currency, decimal, and ordinal verbalization with `num2words`;
- stage-level provenance through `PreparedText`;
- optional provider-neutral spaCy annotations;
- optional whole-document language detection through Lingua;
- conservative protection for URLs, email addresses, and semantic versions.

It intentionally does **not** generate phonemes and does not depend on `kokorog2p`.

## Layout

The import package is directly in the repository root. There is no `src/` directory:

```text
spokenform/
├── spokenform/
├── tests/
├── examples/
├── pyproject.toml
└── README.md
```

## Start developing

```bash
python -m venv .venv
. .venv/bin/activate             # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

Initialize Git before the first real release so `setuptools-scm` can derive versions:

```bash
git init
git add .
git commit -m "feat: initial spokenform MVP"
git tag v0.1.0
```

`pyproject.toml` declares `dynamic = ["version"]`. Builds derive the version from Git
tags and write `spokenform/_version.py`. The fallback version is `0.1.0` so the
unpacked ZIP can be installed before Git is initialized.

## Basic API

```python
from spokenform import prepare

prepared = prepare(
    "Prof. Klein bringt am 14.05.2026 um 18:20 Uhr 2 kg mit.",
    language="de",
)

print(prepared.spoken_text)
print(prepared.render_changes())
```

The result contains:

- `source_text`: unchanged caller input;
- `clean_text`: currently the same source text; reserved for future SSMD parsing;
- `spoken_text`: readable normalized output;
- `language` and `language_spans`;
- ordered stages and edit scripts;
- warnings for future recoverable normalization issues.

## CLI

```bash
spokenform --lang de "Prof. Klein hat 2 kg."
spokenform --lang de --changes "Prof. Klein hat 2 kg."
spokenform --lang de --json "Prof. Klein hat 2 kg."
echo "The value is 2." | spokenform --lang en
```

## Optional spaCy annotations

The core does not import or require spaCy. Supply an already loaded pipeline:

```python
import spacy
from spokenform import prepare, spacy_annotations

text = "The box is 2 in. wide."
nlp = spacy.load("en_core_web_sm")
annotations = spacy_annotations(text, nlp)
prepared = prepare(text, language="en", annotations=annotations)
```

Install support with:

```bash
python -m pip install -e ".[spacy]"
```

## Optional language detection

```python
from spokenform import prepare

prepared = prepare("Das ist ein Test.", detect_language=True)
```

```bash
python -m pip install -e ".[langdetect]"
```

A custom detector can be injected without installing Lingua:

```python
prepared = prepare(
    "Das ist ein Test.",
    detect_language=True,
    detector=lambda text: "de",
)
```

## Current MVP limits

- Language detection assigns one language to the complete document. Span-level code-switching is a later milestone.
- Stage edits are exact within each stage, but there is not yet a composed source-to-output offset map.
- Date, time, currency, and ordinal grammar is deliberately conservative and not yet exhaustive.
- SSMD parsing and serialization are not part of the MVP. `clean_text` and language spans leave a stable extension point.
- `abbr2words` currently exposes final expanded text rather than public semantic replacement objects, so edits are reconstructed deterministically at stage boundaries.

## Intended dependency direction

```text
abbr2words ─┐
            ├─ spokenform ── kokorog2p
num2words ──┘
```

`spokenform` must remain independent of phoneme generation.

## License

Apache License 2.0.
