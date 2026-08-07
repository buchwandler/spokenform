# Architecture

`spokenform.prepare()` applies explicit stages in this order:

1. validate the selected language and protected ranges;
2. discover literal ranges such as URLs, email addresses, and semantic versions;
3. obtain or validate optional lexical annotations;
4. replace protected ranges with internal sentinels and remap annotation offsets;
5. normalize Unicode independently when enabled;
6. ask `abbr2words` for source-aligned structured quantity identities and realize
   them with the selected locale's semantic grammar;
7. expand lexical abbreviations with exact `abbr2words` replacements;
8. verbalize remaining generic numeric forms according to `NumberPolicy`;
9. normalize whitespace according to independently configurable controls;
10. restore protected text and compose stage offset maps.

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

The structured boundary is deliberately split by locale: `abbr2words` recognizes
numeric symbols and returns the exact span, numeric lexeme, category, and canonical
identity; `spokenform.structured` dispatches to locale-owned German or French
semantic grammar. No symbol or alias inventory is copied into spokenform. French
owns its dates, h/colon times, ordinals, decimal digit reading, quantities,
temperatures, and currency decomposition, while G2P typography and phonemes stay
downstream.

French is promoted to `NumberPolicy.STRUCTURED_AND_PLAIN` only after its parity
corpus and real downstream gate pass. Every locale replacement retains exact
source spans and composed source/output mapping, and partial caller protection
expands to a complete structured candidate before semantic matching.

`prepare_for_kokorog2p()` is a deterministic one-language adapter. Its profile
preserves run boundaries, honors protected spans fail-closed, and does not perform
language detection, tokenization, G2P, or model-punctuation rewriting.
