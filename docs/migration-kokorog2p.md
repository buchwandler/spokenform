# kokorog2p migration boundary

spokenform can serve a downstream adapter for one selected language run. Call
`prepare_for_kokorog2p()` (or pass `PreparationConfig.for_kokorog2p()`), preserve
caller override spans with `ProtectedSpan`, use `PreparedText.source_edits` and
the public span helpers to remap boundaries, and inspect `warnings` before passing
the result to a G2P tokenizer. The adapter projection is available through
`PreparedText.to_adapter_dict()`.

The German integration contract is tested at three boundaries: spoken text,
source replacement/offset provenance, and a downstream-style token/phoneme
fixture. spokenform does not own tokenization, lexicon lookup, phonemization,
quote/dash typography, or model punctuation. A downstream adapter should run a
dual comparison before removing its legacy normalizer.

The first parity target is German. Lexical abbreviations and numeric symbol
recognition come from `abbr2words`; spokenform supplies the German semantic
realization and exact source replacements. Do not delete a downstream normalizer
until both paths have been compared for prepared text, source replacements,
extended token positions, phonemes, warnings, and protected overrides. A real
downstream gate is provided in `tests/test_real_kokorog2p_integration.py` and is
run in CI with the released `kokorog2p[de]` stack.

## Ownership audit

| Language | Suitable for spokenform                                       | Keep downstream                                               | Status                                          |
| -------- | ------------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------- |
| cs       | dates, numbers, currencies, locale decimal/grouping semantics | G2P and lexicon behavior                                      | caller-managed; parity corpus pending           |
| en       | dates, currencies, ordinary written numbers                   | phoneme-sensitive years, digit-by-digit and suffix heuristics | ownership documented; parity corpus pending     |
| es       | dates, numbers, currencies, units                             | G2P/tokenizer typography                                      | parser hardening covered; parity corpus pending |
| fr       | dates, numbers, currencies, units                             | G2P/tokenizer typography                                      | parser hardening covered; parity corpus pending |
| it       | dates, numbers, currencies, units                             | G2P/tokenizer typography                                      | parser hardening covered; parity corpus pending |
| pt       | dates, numbers, currencies, units                             | G2P/tokenizer typography                                      | parser hardening covered; parity corpus pending |

This audit intentionally does not port language detection, markup parsing, mixed
language orchestration, lexicon lookup, phoneme suffix rules, token IDs, or model
specific quote/dash behavior into spokenform. The non-German number policies remain
caller-managed until each language has its own accepted downstream corpus.
