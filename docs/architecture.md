# Architecture

`spokenform.prepare()` applies explicit stages in this order:

1. validate the selected language and protected ranges;
2. discover literal ranges such as URLs, email addresses, and semantic versions;
3. obtain or validate optional lexical annotations;
4. replace protected ranges with internal sentinels and remap annotation offsets;
5. parse complete structured values with the selected locale;
6. expand lexical abbreviations with `abbr2words`;
7. verbalize remaining generic numeric forms with `num2words`;
8. normalize Unicode and whitespace;
9. restore protected text and compose stage offset maps.

Each stage records its input, output, edits, and mapped edits. Structured stages
emit one exact semantic `Replacement` per consumed expression; generic and
third-party text-only stages retain deterministic diff edits. The final
`PreparedText.offset_map` composes all stage maps from `clean_text` coordinates to
`spoken_text` coordinates, while `PreparedText.source_edits` and its span helpers
are the migration-facing source/output surface.

## Ownership boundary

`spokenform` owns plain-text normalization, protection, provenance, and coordinate
mapping. Callers own language selection, markup parsing, and mixed-language
segmentation. Downstream G2P systems own tokenization for phoneme generation,
lexicons, pronunciations, and vocabulary IDs.

spokenform owns semantic spacing and punctuation consumed by a structured or
lexical expression. Downstream G2P owns quote style, dash canonicalization,
apostrophe variants, and punctuation choices required only by a model tokenizer.
