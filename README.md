[![PyPI - Version](https://img.shields.io/pypi/v/spokenform)](https://pypi.org/project/spokenform/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/spokenform)
![PyPI - Downloads](https://img.shields.io/pypi/dm/spokenform)
[![codecov](https://codecov.io/gh/buchwandler/spokenform/graph/badge.svg?token=FeOQeR94qo)](https://codecov.io/gh/buchwandler/spokenform)

# spokenform

`spokenform` converts plain written text in one selected language into reviewable
text intended for speech systems. It is a text-to-text frontend: written text in,
spoken form out.

The package provides:

- context-aware abbreviation and source-aligned numeric-unit expansion through `abbr2words`;
- a locale-aware structured-value stage for quantities, dates, times, currencies,
  temperatures, labels, and contextual ordinals;
- locale-policy-wrapped number, date, time, currency, decimal, and ordinal verbalization;
- optional provider-neutral spaCy annotations for POS-aware abbreviation rules;
- stage-level provenance through `PreparedText`;
- composed input-to-output offset maps with left/right boundary bias;
- caller-defined and automatically discovered protected ranges;
- conservative protection for URLs, email addresses, and semantic versions.

It intentionally does **not** detect languages, parse or render SSMD, segment mixed
languages, generate phonemes, or depend on `kokorog2p`.

## Installation

```bash
python -m pip install spokenform
```

For optional spaCy integration:

```bash
python -m pip install "spokenform[spacy]"
python -m spacy download de_core_news_sm
```

spaCy and its trained pipelines are separate packages. `spokenform` never downloads
a model automatically.

## Quickstart

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
- `clean_text`: plain text used by the normalization pipeline;
- `spoken_text`: readable normalized output;
- `language`: normalized processing-language code;
- ordered stages and mapped edits;
- a composed `offset_map`;
- structured warnings.

`PreparedText.text` is an alias for `spoken_text`.

## kokorog2p adapter

Use `prepare_for_kokorog2p(text, language=...)` for one explicitly selected
language run. The adapter preserves caller-owned run whitespace and protected
overrides, emits exact source-coordinate replacements, and leaves tokenization,
G2P, phonemization, and model punctuation to kokorog2p. German, French, Spanish,
Italian, Portuguese, Czech, and English are parity-gated semantic migration
targets. English is active on the kokorog2p spokenform adapter for reviewed
structured semantics and safe ordinary-number categories; phoneme-sensitive
years, suffix ordinals, Roman numerals, phone/ID and dotted sequences, numeric
suffixes, and G2P decisions remain downstream in kokorog2p.

German quantity symbols are recognized by `abbr2words.iter_unit_matches()`.
spokenform owns only the canonical German grammar that realizes those matches,
including gender, invariant `Stück`, currency decomposition, and lexical decimal
digits. French likewise realizes canonical `abbr2words` quantity and currency
identities, including French dates, times, ordinals, decimal digits, plural
grammar, temperatures, and major/minor currency units. Spanish realizes
canonical quantities, temperatures, currencies, dates, and ordinary numbers;
Spanish `18:20`-style time expressions remain caller-managed. Italian realizes
reviewed dates, quantities, temperatures, currencies, and ordinary numbers;
Italian colon times remain caller-managed. Portuguese realizes reviewed dates,
quantities, temperatures, currencies, and ordinary numbers; Portuguese colon
times remain caller-managed. Czech realizes reviewed dates, ordinary numbers,
quantities, temperatures, currencies, and canonical extended units; Czech colon
times remain caller-managed. No locale copies raw symbol inventories or
downstream tokenizer/phoneme rules.

## Language boundary

Each call processes one language. Production callers should always pass
`language=...`; English remains the API default for compatibility and simple CLI
usage.

Language detection and mixed-language handling belong in the orchestration or G2P
layer. A foreign word may remain unchanged through normalization and be handled
afterward. Existing source spans can be transferred with `prepared.offset_map`.

Markup must also be parsed outside this package. Pass plain text to `prepare()` and
use `ProtectedSpan` for ranges generic normalization must not change.

## Configuration

```python
from spokenform import PreparationConfig, prepare

config = PreparationConfig(
    language="en",
    expand_abbreviations=True,
    expand_structured=True,
    expand_numbers=True,
    normalize_whitespace=True,
    context=True,
)

prepared = prepare("The board is 2 in. wide.", config=config)
```

When a `PreparationConfig` is supplied, it is authoritative for pipeline options.

## spaCy support

spaCy supplies POS annotations for abbreviation rules that opt into POS guards. The public normalization API remains provider-neutral.

`abbr2words` accepts POS annotations, but its bundled registries do not necessarily
require POS labels. Therefore installing spaCy alone may not change default
normalization output. The integration is usable for custom POS-guarded entries.

Load and inject a pipeline in the application:

```python
import spacy
from spokenform import prepare

nlp = spacy.load("en_core_web_sm")
prepared = prepare(
    "The board is 2 in. wide.",
    language="en",
    nlp=nlp,
)
```

Or ask `spokenform` to load an already installed model:

```python
prepared = prepare(
    "The board is 2 in. wide.",
    language="en",
    spacy_model="en_core_web_sm",
    strict=True,
)
```

Model names and paths are passed to `spacy.load()`. Loaded models are cached by
language/model key. `reset_spacy_cache()` clears that cache.

The adapter reads the token attributes `text`, `idx`, `pos_`, `tag_`, `lemma_`, and `lang_`. `lang_` is carried as provider metadata; it is not used as language detection. Annotation spans are validated against the exact input text and remapped when protected ranges are replaced by internal sentinels.
A trained pipeline with POS or morphological annotations is required for quality
improvement; `spacy.blank(...)` supplies tokenization but normally no useful POS
tags.

Explicit `annotations` take precedence over `nlp` and `spacy_model`.

## Protection

Use `ProtectedSpan(start, end)` or a `(start, end)` tuple to protect a source range:

```python
from spokenform import ProtectedSpan, prepare

text = "Keep Dr. literal, but verbalize 12."
start = text.index("Dr.")
prepared = prepare(
    text,
    language="en",
    protected_spans=[ProtectedSpan(start, start + 3)],
)
```

Invalid or overlapping ranges warn by default and raise `ProtectionError` with
`strict=True`. URLs, email addresses, and semantic versions are protected
automatically.

## Offset mapping

```python
from spokenform import prepare

source = "Prof. Klein has 2 kg."
prepared = prepare(source, language="de")

start = source.index("Prof.")
end = start + len("Prof.")
spoken_start, spoken_end = prepared.offset_map.map_source_span(start, end)

print(prepared.spoken_text[spoken_start:spoken_end])
```

Use `bias="left"` or `bias="right"` when mapping an individual boundary at an
expansion.

## CLI

```bash
spokenform --lang de "Prof. Klein hat 2 kg."
spokenform --lang de --changes "Prof. Klein hat 2 kg."
spokenform --lang de --json "Prof. Klein hat 2 kg."
spokenform --lang en --spacy-model en_core_web_sm --strict "The board is 2 in. wide."
echo "The value is 2." | spokenform --lang en
```

## Examples

Executable examples are in [`examples/`](examples/README.md):

```bash
python examples/basic.py
python examples/german.py
python examples/german.py --spacy-model de_core_news_sm
python examples/protected_text.py
python examples/offset_mapping.py
```

## Documentation

Documentation sources use MyST Markdown. No reStructuredText source files are
required.

```bash
python -m pip install -e .
python -m pip install -r docs/requirements.txt
sphinx-build -W -b html docs docs/_build/html
```

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy spokenform examples
python -m build
python -m twine check dist/*
```

On Windows, activate the environment with `.venv\Scripts\activate`.

## Current limits

- One processing language is supported per call.
- Language detection, mixed-language segmentation, and language marking are external.
- SSMD and other markup must be parsed before calling `spokenform`.
- Date, time, currency, and ordinal grammar is conservative and not exhaustive.
- Spanish parity ownership covers reviewed dates, quantities, temperatures,
  currencies, and ordinary numbers; time expressions remain caller-managed.
- Italian parity ownership covers reviewed dates, quantities, temperatures,
  currencies, and ordinary numbers; colon times remain caller-managed.
- Czech and English own reviewed structured and safe plain-number categories;
  Czech colon-time candidates remain caller-managed. English years, suffix
  ordinals, Roman numerals, phone/ID and dotted sequences, numeric suffixes,
  and G2P decisions remain downstream in kokorog2p.
- `abbr2words` currently exposes final expanded text rather than semantic replacement objects, so stage edits are reconstructed deterministically from diffs.
- Trained spaCy pipelines must be installed and version-compatible with the spaCy runtime.

## Dependency direction

```text
abbr2words ─┐
            ├─ spokenform ── kokorog2p
num2words ──┘
```

spaCy is an optional quality dependency. `spokenform` remains independent of
language detection, markup parsing, and phoneme generation.

## Release versioning

`setuptools-scm` derives versions from Git tags and writes
`spokenform/_version.py` during builds. Use annotated tags such as `v0.2.2`.
The source-tree fallback when SCM metadata has not been generated is the neutral
version `0+unknown`; release builds derive their version from the annotated tag.

Before publishing, ensure the released `abbr2words>=0.2.4` prerequisite exists
on the target package index and run the checklist in
[`docs/release-checklist.md`](docs/release-checklist.md).

## License

Apache License 2.0.
