# Quickstart

```python
from spokenform import prepare

result = prepare(
    "Prof. Klein bringt am 14.05.2026 um 18:20 Uhr 2 kg mit.",
    language="de",
)

print(result.spoken_text)
print(result.render_changes())
```

The output is a `PreparedText` object. Its main fields are:

- `source_text`: input exactly as supplied;
- `clean_text`: plain text entering the pipeline;
- `spoken_text`: normalized text intended for a speech system;
- `stages`: ordered before/after records;
- `mapped_edits`: edits with source and output coordinates;
- `offset_map`: composed source/output boundary map;
- `warnings`: recoverable protection or spaCy issues.

## Configuration object

```python
from spokenform import PreparationConfig, prepare

config = PreparationConfig(
    language="en",
    expand_abbreviations=True,
    expand_numbers=True,
    normalize_whitespace=True,
    context=True,
)

result = prepare("The board is 2 in. wide.", config=config)
```

When `config` is supplied, it is authoritative for pipeline options.
