# spokenform

`spokenform` converts written text into a readable form intended for speech systems.
It is a text-to-text frontend: raw text in, reviewable spoken text out.

The package provides a staged written-to-spoken boundary:

- context-aware abbreviation and numeric-unit expansion from `abbr2words`;
- number, date, time, currency, decimal, and ordinal verbalization with `num2words`;
- stage-level provenance through `PreparedText`;
- composed clean-text-to-spoken-text offset maps with left/right boundary bias;
- protected literal and caller-supplied phoneme ranges;
- optional SSMD parsing and explicit language-mark rendering;
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

from spokenform import PreparationConfig

prepared = prepare(
    '[Bonjour]{lang="fr"} paid 2 EUR',
    config=PreparationConfig(language="en", markup="ssmd"),
)
print(prepared.clean_text)   # SSMD-free text
print(prepared.spoken_text)  # text intended for a G2P frontend
print(prepared.offset_map.map_source_span(0, 7))
```

The result contains:

- `source_text`: unchanged caller input;
- `clean_text`: SSMD-free written text;
- `spoken_text`: readable normalized output;
- `language` and `language_spans`;
- ordered stages, mapped edits, and a composed `offset_map`;
- semantic/protected spans and structured warnings;
- optional `marked_text` and `render_ssmd()` output.

Offsets in `language_spans` and `semantic_spans` refer to `clean_text`. The
offset map maps clean-text boundaries to `spoken_text`; use `bias="left"` or
`bias="right"` at an expansion boundary.

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

An injected pipeline is reused by the preparation call. To let spokenform load
a named installed model, pass `use_spacy=True, spacy_model="..."`. Models are
never downloaded automatically and are cached by language/model key; call
`reset_spacy_cache()` in tests or long-lived hosts when needed.

## SSMD and protection

Install SSMD support with `python -m pip install -e ".[ssmd]"`. The default
`markup="plain"` mode never interprets bracket syntax. `markup="ssmd"` parses
language, phoneme, say-as, substitution, and literal annotations before
normalization. Explicit SSMD language spans take precedence over caller spans
and detection. `ph` and literal semantics are protected from generic
abbreviation and number rules.

Use `ProtectedSpan(start, end, kind="phoneme")` or a `(start, end)` tuple to
protect a clean-text range. Invalid or overlapping ranges warn by default and
raise `ProtectionError` with `strict=True`.

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
- Date, time, currency, and ordinal grammar is deliberately conservative and not yet exhaustive.
- `abbr2words` currently exposes final expanded text rather than public semantic replacement objects, so edits are reconstructed deterministically at stage boundaries.

## Ownership boundary

`spokenform` owns written-text cleanup, semantic verbalization, language spans,
SSMD extraction, protection, provenance, and source/output mapping. A downstream
G2P package owns punctuation normalization, tokenization, lexicons, phoneme
selection, overrides after remapping, and vocabulary/token IDs. `spokenform`
does not generate phonemes and does not import `kokorog2p`.

## Intended dependency direction

```text
abbr2words ─┐
            ├─ spokenform ── kokorog2p
num2words ──┘
```

`spokenform` must remain independent of phoneme generation.

## License

Apache License 2.0.
