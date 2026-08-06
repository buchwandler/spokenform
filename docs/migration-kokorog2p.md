# kokorog2p migration boundary

spokenform can serve an experimental downstream adapter for one selected language
run. Call `prepare()`, preserve caller override spans with `ProtectedSpan`, use
`PreparedText.source_edits` and the public span helpers to remap boundaries, and
inspect `warnings` before passing the result to a G2P tokenizer.

The first parity target is German. Lexical abbreviations continue to come from
`abbr2words`; structured values are controlled by `expand_structured`; generic
numbers are controlled by `expand_numbers`. Do not delete a downstream normalizer
until both paths have been compared for text, token boundaries, phonemes, and
warnings.

## Ownership audit

| Language | Suitable for spokenform                                       | Keep downstream                                               | Status                                          |
| -------- | ------------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------- |
| cs       | dates, numbers, currencies, locale decimal/grouping semantics | G2P and lexicon behavior                                      | parser hardening covered; parity corpus pending |
| en       | dates, currencies, ordinary written numbers                   | phoneme-sensitive years, digit-by-digit and suffix heuristics | ownership documented; parity corpus pending     |
| es       | dates, numbers, currencies, units                             | G2P/tokenizer typography                                      | parser hardening covered; parity corpus pending |
| fr       | dates, numbers, currencies, units                             | G2P/tokenizer typography                                      | parser hardening covered; parity corpus pending |
| it       | dates, numbers, currencies, units                             | G2P/tokenizer typography                                      | parser hardening covered; parity corpus pending |
| pt       | dates, numbers, currencies, units                             | G2P/tokenizer typography                                      | parser hardening covered; parity corpus pending |

This audit intentionally does not port language detection, markup parsing, mixed
language orchestration, lexicon lookup, phoneme suffix rules, token IDs, or model
specific quote/dash behavior into spokenform.
