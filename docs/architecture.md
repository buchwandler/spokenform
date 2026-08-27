# Architecture

`spokenform.prepare()` applies explicit stages in this order:

1. validate the selected language and protected ranges;
2. discover caller-protected ranges and auto-detected literals such as URLs,
   email addresses, and (when not claimed semantically) semantic versions;
   `normalize_literals=True` opts high-confidence URL, e-mail, version, and
   contextual Roman rendering into structured ownership while caller spans
   remain absolute;
3. obtain or validate optional lexical annotations;
4. replace protected ranges with internal sentinels and remap annotation offsets;
5. normalize Unicode independently when enabled;
6. recognize complete high-confidence structured sequences, then ask `abbr2words`
   for source-aligned structured quantity identities and realize them with the
   selected locale's semantic grammar;
7. expand lexical abbreviations with exact `abbr2words` replacements;
8. verbalize remaining generic numeric forms according to `NumberPolicy`;
9. when requested, filter residual Unicode punctuation/symbol characters under
   the caller's `symbol_mode`, while protected sentinels remain opaque;
10. normalize whitespace according to independently configurable controls;
11. restore protected text and compose stage offset maps.

Each stage records its input, output, edits, and mapped edits. Structured and
abbreviation stages emit exact replacements; temporary text-only stages retain
deterministic diff edits only at stage scope. The final
`PreparedText.offset_map` composes all stage maps from `clean_text` coordinates to
`spoken_text` coordinates. `PreparedText.source_edits` contains composed
`SourceReplacement` records in original-source/final-output coordinates; it must
not be confused with stage-local `mapped_edits`.

All public source offsets refer to the original string passed to `prepare()`.
Final offsets refer to `PreparedText.spoken_text`. Boundary APIs expose explicit
left/right bias for insertions, deletions, and generated replacement text.

## Ownership boundary

`spokenform` owns plain-text normalization, protection, provenance, and coordinate
mapping. Callers own language selection, markup parsing, and mixed-language
segmentation. Downstream G2P systems own tokenization for phoneme generation,
lexicons, pronunciations, and vocabulary IDs.

spokenform owns semantic spacing and punctuation consumed by a structured or
lexical expression. Downstream G2P owns quote style, dash canonicalization,
apostrophe variants, and punctuation choices required only by a model tokenizer.

The optional `symbols` stage is a caller-requested final residual-output policy,
not semantic recognition. It is disabled for `symbol_mode="none"`; semantic
punctuation is consumed first by structured recognizers, and model-specific
punctuation remains downstream unless the caller explicitly requests filtering.

The structured boundary is deliberately split by locale: `abbr2words` recognizes
numeric symbols and returns the exact span, numeric lexeme, category, and canonical
identity; `spokenform.structured` dispatches to locale-owned semantic grammar.
No symbol or alias inventory is copied into spokenform. French owns its dates,
h/colon times, ordinals, decimal digit reading, quantities, temperatures, and
currency decomposition. Spanish, Italian, Portuguese, and Czech own their
reviewed dates, quantities, temperatures, currencies, ordinary numbers, and
locale-specific extensions; caller-managed time boundaries remain documented.
English owns reviewed dates, validated clock times, canonical quantities and
currencies, conservative ordinary numbers, and contextual release labels.
Japanese, Korean, and Chinese use explicit native numeric and sequence
vocabularies, with Chinese routed through `cn2an`. Swedish owns comma-decimal
numbers, reviewed quantities, temperatures, SEK grammar, and canonical
`abbr2words` unit identities. Swedish dates, digital times, arbitrary initialisms,
and unreviewed specialist sequence domains remain caller-managed or fail closed.
Vietnamese owns comma-decimal numbers, exact fractional precision, reviewed quantities, temperatures, VND/₫ currency, and canonical `abbr2words` unit identities. `num2words` owns generic Vietnamese cardinals, while `abbr2words` owns reviewed Vietnamese abbreviation, unit, currency recognition, and labels. Vietnamese dates, digital times, ordinals, arbitrary initialisms, and unreviewed specialist sequence domains remain caller-managed or fail closed.
Thai follows the same small-locale architecture: `num2words` owns generic Thai cardinals, `abbr2words` owns reviewed Thai abbreviation, unit, and baht identities, and Spokenform owns compact digitwise numeric realization and source mapping. Thai calendar protection is applied after abbreviation expansion and before the plain number pass, so structured values -> abbreviation expansion -> plain number pass preserves date, era, and time bodies. Thai unsupported ranges and specialist sequences fail closed without English vocabulary.
Every locale replacement retains exact source spans and composed source/output
mapping. Supported languages never borrow English fallback words merely because a
shared renderer lacks a locale entry. All reviewed quantity and currency symbols
continue to come from `abbr2words`.

The dependency direction is:

```text
abbr2words ──────────┐
num2words (ja/ko/sv/vi) ──┼─> spokenform
cn2an (zh) ─────────┘
```

Full-width numeric compatibility forms are folded in a dedicated mapped stage after NFC and only inside numeric-looking spans. Compatibility symbols such as `㈱` remain available to `abbr2words`; global NFKC is not used.
`prepare_for_kokorog2p()` is a deterministic one-language adapter. Its profile
preserves run boundaries, honors protected spans fail-closed, and does not perform
language detection, tokenization, G2P, or model-punctuation rewriting.

The downstream migration set currently includes `cs`, `de`, `fr`, `es`, `it`,
`pt`, and `en`. English is active on the kokorog2p spokenform adapter for
reviewed structured semantics, contextual single-dot release labels, and safe
ordinary-number categories. Years, suffix ordinals, Roman numerals, phone/ID and
arbitrary multi-dot sequences, numeric suffixes, and G2P decisions remain
downstream-owned.

## Structured precedence

Caller protection is absolute. Auto-detected literals are a fallback reservation
against partial generic rewrites; a complete semantic recognizer may claim an
auto-literal before it is reserved. Candidate conflict resolution gives priority
to canonical identifiers, then coordinates and formulas, contextual legal,
sports, and address forms, dates and times, contextual sequences,
quantities/currencies/temperatures, specialist music/math forms, and generic
acronym/product candidates. Fractions and date/phone ambiguity are resolved by
semantic candidate priority rather than regex iteration order.
Unclaimed or ambiguous forms remain opaque. The concrete rule-family ordering is
centralized in `spokenform.precedence.SequencePriority`; recognizers do not rely
on source regex iteration order to resolve time/reference, ISBN/phone,
version/decimal, version/IPv4, or year/identifier conflicts. Every selected candidate is still an
exact `Replacement`, so precedence does not weaken source/output mapping or
protected-span behavior.

Address numbers use the library's stable default address policy: ordinary
street numbers are rendered cardinally when the full address is recognized,
while compact plates, suites, postal codes, and model identifiers retain their
category-specific digitwise policies. Contradictory benchmark conventions are
reported as data-quality evidence rather than encoded as row-specific rules.

## Recognition policy boundary

Structured recognizers first emit candidates annotated with a semantic domain and evidence basis (`intrinsic` or `contextual`). `spokenform.recognition_policy` filters those candidates before `SequencePriority` overlap resolution. Surface mode admits intrinsic evidence only and treats missing metadata as contextual, while disabled domains suppress their ownership family and reserve overlapping spans against weaker semantic takeover. This keeps interpretation depth, semantic ownership, and rendering settings as separate policy axes. Diagnostics retain suppressed candidates with machine-readable reasons such as `context-not-allowed`, `disabled-domain`, and `blocked-by-disabled-domain`.

## Optional Lexhint boundary

Lexhint is an optional, provider-neutral evidence source. Spokenform supports Lexhint `0.1.2 <= x < 0.3.0`; Lexhint 0.1.x uses schema-7 artifacts and Lexhint 0.2.x requires separately published schema-8 runtime artifacts. Applications install the desired local dataset with `lexhint dataset download <language> --variant runtime` and inject the provider; normalization never downloads data.

The production boundary uses exact lexical lookup, authoritative segmentation, and positive semantic-domain corroboration only. Lexhint fuzzy completion, headword matching, and dictionary-definition search remain development/diagnostic capabilities and do not alter automatic recognition.

## Semantic segment boundaries

Recognized semantic expressions may consume source punctuation while preserving a generic textual segment boundary when the punctuation carries cadence or grouping semantics. Contextual countdowns therefore render `3-2-1` as `three - two - one`. The boundary is model-neutral and downstream G2P adapters own model-specific dash canonicalization. Residual `symbol_mode` filtering does not remove punctuation intentionally emitted by an accepted structured replacement.
