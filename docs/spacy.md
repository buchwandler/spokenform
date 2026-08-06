# spaCy integration

spaCy is optional. `spokenform` uses it only to obtain source-aligned lexical annotations for POS-aware abbreviation rules.

## Current effect with `abbr2words` 0.2.0

`abbr2words` 0.2.0 accepts POS annotations, but its bundled language registries do not currently require POS labels. A trained model may therefore produce the same default output as the non-spaCy path. The integration is useful for custom entries with POS guards and keeps `spokenform` ready for future bundled POS-aware rules.

## Load an installed model by name

```python
from spokenform import prepare

result = prepare(
    "The board is 2 in. wide.",
    language="en",
    spacy_model="en_core_web_sm",
    strict=True,
)
```

The model name or path is passed to `spacy.load()`. Models are never downloaded
automatically.

## Inject an application-owned pipeline

```python
import spacy
from spokenform import prepare

nlp = spacy.load("de_core_news_sm")
result = prepare(
    "Prof. Klein liefert 2 kg.",
    language="de",
    nlp=nlp,
)
```

Injection is preferred in services that already manage model lifecycle, device
selection, disabled components, and process-level caching.

## Supply annotations directly

```python
from spokenform import TokenAnnotation, prepare

annotations = (
    TokenAnnotation(start=0, end=2, text="in", pos="ADP", tag="IN"),
)
result = prepare("in.", language="en", annotations=annotations)
```

Explicit annotations take precedence over `nlp` and `spacy_model`.

## Required token contract

A spaCy-compatible pipeline must return iterable tokens exposing:

- `text`;
- `idx`, the character offset in the original text;
- optional `pos_`, `tag_`, `lemma_`, and `lang_` strings.

`lang_` is retained as metadata only; `spokenform` does not perform token-level language detection.

A blank tokenizer such as `spacy.blank("en")` provides token boundaries but no
statistical POS tags. Use a trained pipeline containing an appropriate tagging or
morphological component when POS-aware rules are required. Annotations are remapped around protected spans so their offsets remain aligned with the internal text sent to `abbr2words`.

## Error behavior

With `strict=False`, a requested but unavailable model produces a warning in
`PreparedText.warnings` and normalization continues without spaCy. With
`strict=True`, `SpacyModelError` is raised.
