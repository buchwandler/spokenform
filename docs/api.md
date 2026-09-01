# API reference

## Preparation

```{autofunction} spokenform.prepare

```

```{autofunction} spokenform.prepare_language

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

## Language identifiers and number backends

Canonical runtime identifiers include `cs`, `de`, `en`, `es`, `fr`, `it`, `ja`, `ko`, `pt`, `ru`, `sv`, `vi`, and `zh`. Regional forms such as `ru-RU`, `ru_RU`, `sv-SE`, `vi-VN`, and `vi_VN` are normalized internally. `jp` aliases to `ja`, `cn` aliases to `zh_CN`, and `swe` and `rus` are compatibility aliases; `vn` and `kr` are not accepted.

All existing supported languages use released `num2words` except Chinese, which uses released `cn2an`. `number_backend_for_language()` reports this generic backend choice. Swedish resolves to `sv` for both numeric and abbreviation dependency calls, while `resolve_num2words_language()` remains a num2words-specific query and rejects Chinese. `resolve_abbr2words_language()` preserves exact regional overlays such as `zh_CN`.

```python
from spokenform import (
    normalize_language,
    resolve_abbr2words_language,
    resolve_num2words_language,
    supported_languages,
)

assert "sv" in supported_languages()
assert normalize_language("sv-SE") == "sv_SE"
assert resolve_num2words_language("sv-SE") == "sv"
assert resolve_abbr2words_language("sv-SE") == "sv"
```

assert "vi" in supported_languages()
assert normalize_language("vi-VN") == "vi_VN"
assert resolve_num2words_language("vi-VN") == "vi"
assert resolve_abbr2words_language("vi-VN") == "vi"

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

For example, with `use_spacy=False`, `prepare("ABC TST", language="en", generic_acronym_mode="conservative_unknown")`
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

For English, `prepare("844361 items", language="en", long_number_mode="preserve")` keeps the
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

`PreparationConfig.for_speech(language)` provides the generic one-language speech
preset. It contains no TTS-engine policy. `prepare_for_kokorog2p()` and
`PreparationConfig.for_kokorog2p()` remain compatibility conveniences for that
adapter and are not the architectural center of Spokenform.

`PreparedText` mappings describe source and output coordinates, not a linguistic
analysis of generated tokens. When normalization changes a token, source POS, tag,
lemma, or morphology must not be reused for the generated text. Run a fresh
linguistic analysis after preparation when downstream processing requires it.
The preferred application surface is `prepare_language()` with
`PreparationConfig.for_speech(language)`, `PreparedText.source_replacements`,
and `PreparedText.offset_map`. The KokoroG2P compatibility surface additionally
uses `PreparationConfig.for_kokorog2p()`, `prepare_for_kokorog2p()`, and
`NumberPolicy`. Lower-level mapping and stage helpers are advanced exports rather
than requirements for a normal adapter.

The stable application-facing surface is `prepare_language()`, `prepare()`,
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

## Interpretation policy

`PreparationConfig` and `prepare()` expose two orthogonal recognition controls:

- `interpretation_mode="contextual"` (default) permits reviewed contextual semantic evidence.
- `interpretation_mode="surface"` permits only candidates marked with intrinsic evidence and fails closed on missing metadata.
- `disabled_domains={"chemistry", ...}` suppresses selected `RecognitionDomain` families before precedence resolution.
- `allowed_domains={"quantities", ...}` permits only selected semantic families and fails closed for candidates without domain metadata. If a domain appears in both sets, configuration raises `ValueError`.

```python
from spokenform import prepare_language

prepare_language(
    "The sample contains H2O.",
    language="en",
    interpretation_mode="surface",
    disabled_domains={"chemistry"},
)
```

`context` remains the legacy abbreviation-context switch. Surface mode clamps its effective abbreviation context off, but `context=False` under contextual mode does not disable structured recognizers. `InterpretationMode`, `RecognitionDomain`, and `RecognitionEvidence` are exported public types. Policy-suppressed candidates are visible in structured trace diagnostics.

`sequence_fallback_mode="preserve"` is the compatibility default. Set it to `"spell"` to render conservative residual sequence-shaped spans such as `AAPL` or `H2O` orthographically after semantic recognition. It does not spell ordinary lexical prose, does not claim a semantic domain, and never overrides caller-protected or auto-protected literal spans. `SequenceFallbackMode`, `InterpretationMode`, `RecognitionDomain`, and `RecognitionEvidence` are exported public types. Policy-suppressed candidates are visible in structured trace diagnostics.

The Swedish `normalize_numbers(language="sv")` path preserves comma-decimal precision and valid numeric grouping, while dates, digital times, and ambiguous dot forms remain caller-managed. Swedish structured quantities, temperatures, and SEK currency are owned by the locale grammar used by `prepare()`.

The Vietnamese `normalize_numbers(language="vi")` path uses structured-safe normalization. Comma decimals preserve exact fractional precision, dot and space-family grouping are validated, and reviewed quantities and VND/₫ are locale-owned through `abbr2words`. Date, time, and ordinal semantics remain caller-managed.

Thai `normalize_numbers(language="th")` uses point decimals, comma or space-family grouping, accepts Thai digits, and preserves decimal precision digitwise. Structured quantities, temperatures, and THB/`฿` use reviewed `abbr2words` identities while Spokenform owns numeric realization. `th_TH` and `th-TH` resolve to the base dependency registries; dates, times, eras, ordinals, ranges, and unsupported specialist semantics remain caller-managed or fail closed.

Russian `normalize_numbers(language="ru")` uses the structured-safe path. It preserves comma-decimal precision, accepts regular/NBSP/NNBSP grouping, and renders reviewed quantity grammar through `abbr2words` canonical IDs. Dates, digital times, year abbreviations, phone spans, RUB, and unreviewed specialist semantics remain caller-managed or fail closed. `rus` is accepted only as a compatibility alias.

## Lexhint evidence provider

Lexhint `0.1.2 <= x < 0.3.0` is supported as an optional provider. Lexhint 0.1.x uses schema-7 artifacts, while Lexhint 0.2.x requires schema-8 artifacts installed separately with `lexhint dataset download <language> --variant runtime`. Spokenform never downloads datasets automatically.

Pass an installed Lexhint runtime `Lexicon` explicitly through `lexical_evidence`. No dataset is resolved or downloaded when the argument is omitted. URL lexical segmentation may work with a lexical-only provider. Contextual computing and sports support requires the semantic capability, and missing semantic evidence never vetoes an existing candidate.

```python
from lexhint import Lexicon
from spokenform import prepare

lexicon = Lexicon("en", variant="runtime")
result = prepare(
    "compiler 8.3.2 and chatgpt.com",
    language="en",
    normalize_literals=True,
    lexical_evidence=lexicon,
    use_spacy=False,
)
```

Lexhint semantic domains are mapped to Spokenform use cases rather than copied into `RecognitionDomain`. Surface mode ignores semantic evidence. URL lexical evidence is a rendering aid for a URL already recognized or promoted by Spokenform.
