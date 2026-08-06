# Offset mapping and provenance

Every enabled stage records its input, output, and deterministic edits. The final
`OffsetMap` composes those stage maps.

```python
from spokenform import prepare

source = "Prof. Klein has 2 kg."
result = prepare(source, language="de")

start = source.index("Prof.")
end = start + len("Prof.")
spoken_start, spoken_end = result.offset_map.map_source_span(start, end)
print(result.spoken_text[spoken_start:spoken_end])
```

Boundary mappings support `bias="left"` and `bias="right"` because one source
boundary may correspond to both sides of an expanded replacement.

`map_source_span()` uses left bias for the start and right bias for the end.
`map_output_span()` performs the inverse operation.

Structured edits are available on the structured stage and expose the complete
source expression, spoken replacement, `kind`, language, and locale `rule`.
For downstream adapters, prefer `PreparedText.source_edits`,
`PreparedText.map_source_span()`, and `PreparedText.map_output_span()` rather
than importing mapping internals.
