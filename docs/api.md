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
skipping the whitespace stage entirely. `normalize_literals=True` opts into
high-confidence URL, e-mail, semantic-version, and contextual Roman rendering;
caller-protected spans always take precedence.

`symbol_mode="none"` is the backward-compatible default and applies no general
residual-symbol filter. `symbol_mode="remove"` removes Unicode punctuation and
symbol characters (`P*` and `S*`) left after semantic recognition. With
`symbol_mode="keep"`, `keep_symbols` is an exact-codepoint allowlist; it must
not be empty. An allowlist is invalid in `none` or `remove` mode. The active
filter is recorded as a `symbols` stage before whitespace normalization and
never changes protected spans. Symbol deletions are included in stage and
source/output mapping.

`generic_acronym_case="upper"` is the default. Set it to `"lower"` to lowercase
only generic grapheme-spaced uppercase acronyms; lexical acronyms, preserved
terms, known initialisms, identifiers, and mixed-case tokens keep their normal
policies.

## Configuration policy modes

The policy modes below are passed through the selected language's `abbr2words`
registry where abbreviation or initialism data is involved. They are available
for every language profile, but the exact recognized vocabulary and number
grammar remain locale-specific. They are safety controls: conservative modes
prefer leaving an ambiguous token unchanged, while expansive modes can create
false positives in identifiers, product names, headlines, years, and other
uppercase or digit-heavy text.

### Generic acronyms

`generic_acronym_mode="known_only"` is the default. It lets registered or
otherwise known initialisms follow their registry policy and leaves unknown
uppercase words alone. For example, an unknown `TST` remains unchanged while a
known entry such as `ABC` can be rendered according to the registry.

`"conservative_unknown"` additionally spells unknown uppercase initialisms
when the context provides abbreviation evidence, reducing accidental changes
to ordinary uppercase prose. `"spell_unknown"` is the broadest mode: eligible
unknown uppercase initialisms are spelled even without as much contextual
evidence, so it is useful for abbreviation-heavy input but has the highest
false-positive risk.

```python
PreparationConfig(language="en", generic_acronym_mode="known_only")
PreparationConfig(
    language="en",
    generic_acronym_mode="spell_unknown",
    generic_acronym_case="upper",
)
```

For example, with `use_spacy=False`, `prepare("ABC TST", generic_acronym_mode="conservative_unknown")`
produces `"A B C T S T"` in the current English registry, while the default
keeps the unknown `TST` unchanged. `generic_acronym_case="lower"` changes only
generic grapheme-spaced output (`"a b c t s t"` in that example); it does not
lowercase lexical acronyms or registered terms. These modes are delegated to
`abbr2words`' initialism policy rather than implemented as a second local
abbreviation registry.

### Registered acronyms

`registered_acronym_mode="expand"` is the default and uses the registered
initialism expansion supplied by `abbr2words`. Set it to `"spell"` when the
letters of registered initialisms are preferable to their lexical expansion,
for example `CEO MIT` -> `C E O M I T` in English. This mode has lower lexical
interpretation risk but may be less natural for acronyms whose full names are
well known. It affects registered entries, not arbitrary unknown uppercase
words, and is forwarded to `abbr2words` as `registered_initialism_mode`.

```python
PreparationConfig(language="en", registered_acronym_mode="spell")
```

### Long numbers

`long_number_mode="preserve"` is the default. It leaves long ungrouped digit
strings alone when they could be years, identifiers, account numbers, or other
downstream-owned sequences. `"contextual"` verbalizes a long number when
quantity evidence makes cardinal reading safe, such as `844361 items`, while
continuing to protect identifier-like uses. `"cardinal"` requests cardinal
verbalization for eligible long numbers regardless of that contextual evidence;
it is useful for prose known to contain quantities but carries a higher risk of
rewriting IDs and years. The number grammar and rendered words are selected by
the active language, and this policy is independent of `abbr2words`' lexical
abbreviation registry.

```python
PreparationConfig(language="en", long_number_mode="contextual")
```

For English, `prepare("844361 items", long_number_mode="preserve")` keeps the
digits, while `"contextual"` and `"cardinal"` produce
`"eight hundred forty four thousand three hundred sixty one items"`.

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
