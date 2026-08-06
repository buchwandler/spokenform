# spokenform

`spokenform` converts written text in one explicitly selected language into a
readable form intended for speech systems. It is a text-to-text frontend:
written text in, reviewable spoken text out.

The package provides a staged written-to-spoken boundary:

- context-aware abbreviation and numeric-unit expansion from `abbr2words`;
- number, date, time, currency, decimal, and ordinal verbalization with `num2words`;
- optional provider-neutral spaCy annotations for higher-quality contextual expansion;
- stage-level provenance through `PreparedText`;
- composed input-to-spoken offset maps with left/right boundary bias;
- caller-supplied and automatically discovered protected ranges;
- conservative protection for URLs, email addresses, and semantic versions.

It intentionally does **not** detect languages, parse or render SSMD, segment
mixed-language text, generate phonemes, or depend on `kokorog2p`.

## Language boundary

Every `prepare()` call processes exactly one language. The caller must select the
language before invoking `spokenform`:

```python
from spokenform import prepare

prepared = prepare("Prof. Klein hat 2 kg.", language="de")
```

Language detection and mixed-language handling belong in the orchestration or G2P
layer. A foreign word can remain unchanged through normalization and be detected or
marked on `prepared.spoken_text` afterward. Existing source spans can be transferred
with `prepared.offset_map`.

Markup must also be parsed outside this package. After external parsing, pass plain
text to `prepare()` and use `ProtectedSpan` for ranges that generic normalization
must not change.

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

Install optional spaCy support with:

```bash
python -m pip install -e ".[spacy]"
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
print(prepared.offset_map.map_source_span(0, 11))
```

The result contains:

- `source_text`: unchanged caller input;
- `clean_text`: the plain input text used by the normalization pipeline;
- `spoken_text`: readable normalized output;
- `language`: the normalized processing-language code;
- ordered stages, mapped edits, and a composed `offset_map`;
- structured warnings.

The offset map maps `clean_text` boundaries to `spoken_text`; use `bias="left"` or
`bias="right"` at an expansion boundary.

## Configuration

```python
from spokenform import PreparationConfig, prepare

config = PreparationConfig(
    language="en",
    expand_abbreviations=True,
    expand_numbers=True,
    normalize_whitespace=True,
    context=True,
)

prepared = prepare("The box is 2 in. wide.", config=config)
```

Passing a `PreparationConfig` makes it the authoritative source for pipeline options.

## spaCy support

spaCy improves abbreviation expansion where part-of-speech context disambiguates a
written form. The normalization API remains provider-neutral.

Supply an already loaded pipeline:

```python
import spacy
from spokenform import prepare

nlp = spacy.load("en_core_web_sm")
prepared = prepare(
    "The box is 2 in. wide.",
    language="en",
    nlp=nlp,
)
```

Or let `spokenform` load a named model that is already installed:

```python
prepared = prepare(
    "The box is 2 in. wide.",
    language="en",
    spacy_model="en_core_web_sm",
)
```

Models are never downloaded automatically. Loaded models are cached by
language/model key; call `reset_spacy_cache()` in tests or long-lived hosts when
needed. Explicit `annotations` take precedence over `nlp` and `spacy_model`.

The CLI exposes the same model-loading path:

```bash
spokenform --lang en --spacy-model en_core_web_sm "The box is 2 in. wide."
```

## Protection

Use `ProtectedSpan(start, end, kind="literal")` or a `(start, end)` tuple to protect
a plain-input range from abbreviation and number normalization:

```python
from spokenform import ProtectedSpan, prepare

text = "Keep Dr. literal, but verbalize 12."
prepared = prepare(
    text,
    language="en",
    protected_spans=[ProtectedSpan(5, 8, kind="literal")],
)
```

Invalid or overlapping ranges warn by default and raise `ProtectionError` with
`strict=True`. URLs, email addresses, and semantic versions are protected
automatically.

## CLI

```bash
spokenform --lang de "Prof. Klein hat 2 kg."
spokenform --lang de --changes "Prof. Klein hat 2 kg."
spokenform --lang de --json "Prof. Klein hat 2 kg."
echo "The value is 2." | spokenform --lang en
```

## Current limits

- One processing language is supported per call.
- Language detection, mixed-language segmentation, and language marking are external.
- SSMD and other markup must be parsed before calling `spokenform`.
- Date, time, currency, and ordinal grammar is deliberately conservative and not yet exhaustive.
- `abbr2words` currently exposes final expanded text rather than public semantic replacement objects, so edits are reconstructed deterministically at stage boundaries.

## Ownership boundary

`spokenform` owns plain written-text cleanup, semantic verbalization, protected
ranges, provenance, and input/output mapping. A caller or orchestration layer owns
language detection, markup parsing, and mixed-language segmentation. A downstream
G2P package owns punctuation normalization, tokenization, lexicons, phoneme
selection, language marks, overrides after remapping, and vocabulary/token IDs.

`spokenform` does not generate phonemes and does not import `kokorog2p`.

## Intended dependency direction

```text
abbr2words ─┐
            ├─ spokenform ── kokorog2p
num2words ──┘
```

spaCy is an optional quality-enhancement dependency. `spokenform` remains independent
of language-detection, markup, and phoneme-generation packages.

## License

Apache License 2.0.
