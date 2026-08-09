# API reference

## Preparation

```{autofunction} spokenform.prepare

```

```{autofunction} spokenform.prepare_for_kokorog2p

```

```{autofunction} spokenform.normalize_spacing

```

`normalize_unicode`, `strip_outer_whitespace`, `collapse_horizontal_whitespace`,
`normalize_line_whitespace`, and `collapse_blank_lines` are independent policy
controls. `normalize_whitespace=False` remains the compatibility switch for
skipping the whitespace stage entirely.

```{autoclass} spokenform.PreparationConfig
:members:
```

## Result models

```{autoclass} spokenform.PreparedText
:members:
```

All public source offsets refer to the original string passed to `prepare()`;
final offsets refer to `PreparedText.spoken_text`; stage-local offsets remain
available only under each `PreparationStage`. `PreparedText.to_adapter_dict()`
is the stable JSON-ready projection for a kokorog2p adapter.

`prepare_for_kokorog2p()` requires an explicit language and performs no language
detection, tokenization, G2P, or model-punctuation rewriting. Its default profile
preserves run boundary whitespace. Pass caller-owned `protected_spans` to prevent
semantic replacements; partial overlap is handled fail-closed by protecting the
complete recognized quantity expression. Use `source_replacements` and the offset
helpers to rebase downstream token and override coordinates.

The preferred downstream surface is `PreparationConfig.for_kokorog2p()`,
`prepare_for_kokorog2p()`, `PreparedText.source_replacements`,
`PreparedText.offset_map`, and `NumberPolicy`. The lower-level mapping and stage
helpers are advanced exports rather than requirements for a normal adapter.

## Export classification

The stable application-facing surface is `prepare()`,
`prepare_for_kokorog2p()`, `prepare_text`, `PreparationConfig`, `NumberPolicy`,
`PreparedText`, `ProtectedSpan`, `ProtectionError`, `TokenAnnotation`, and
`__version__`. `number_policy_for_language()` and `normalize_numbers()` are
stable locale-policy helpers. The annotation adapters, spaCy model helpers,
structured-stage helpers, `StageResult`, and mapping/replacement classes and
conversion functions are advanced public APIs: they remain exported for
compatibility and diagnostics, but downstream integrations should prefer the
high-level preparation surface. No exported symbol is removed in 0.2.2.

```{autoclass} spokenform.PreparationStage
:members:
```

```{autoclass} spokenform.TextEdit

```

```{autoclass} spokenform.MappedEdit

```

## Annotation adapters

```{autoclass} spokenform.TokenAnnotation

```

```{autofunction} spokenform.annotations_from_spacy

```

```{autofunction} spokenform.spacy_annotations

```

```{autofunction} spokenform.validate_annotations

```

## Number normalization

The Czech `normalize_numbers(language="cs")` path delegates to the reviewed
structured and structured-safe plain-number grammar. It verbalizes ordinary
numbers, validated dates, quantities, temperatures, and canonical currencies;
colon-time candidates remain unchanged for caller-managed handling.

```{autofunction} spokenform.normalize_numbers

```

```{autofunction} spokenform.normalize_structured

```

```{autofunction} spokenform.iter_structured_replacements

```
