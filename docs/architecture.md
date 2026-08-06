# Architecture

`spokenform.prepare()` applies explicit stages in this order:

1. validate the selected language and protected ranges;
2. discover literal ranges such as URLs, email addresses, and semantic versions;
3. obtain or validate optional lexical annotations;
4. replace protected ranges with internal sentinels and remap annotation offsets;
5. expand abbreviations and numeric units with `abbr2words`;
6. verbalize supported numeric forms with `num2words`;
7. normalize Unicode and whitespace;
8. restore protected text and compose stage offset maps.

Each stage records its input, output, edits, and mapped edits. The final
`PreparedText.offset_map` composes all stage maps from `clean_text` coordinates to
`spoken_text` coordinates.

## Ownership boundary

`spokenform` owns plain-text normalization, protection, provenance, and coordinate
mapping. Callers own language selection, markup parsing, and mixed-language
segmentation. Downstream G2P systems own tokenization for phoneme generation,
lexicons, pronunciations, and vocabulary IDs.
