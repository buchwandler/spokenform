# kokorog2p migration boundary

spokenform can serve a downstream adapter for one selected language run. Call
`prepare_for_kokorog2p()` (or pass `PreparationConfig.for_kokorog2p()`), preserve
caller override spans with `ProtectedSpan`, use `PreparedText.source_edits` and
the public span helpers to remap boundaries, and inspect `warnings` before passing
the result to a G2P tokenizer. The adapter projection is available through
`PreparedText.to_adapter_dict()`.

The German and French integration contracts are tested at three boundaries: spoken text,
source replacement/offset provenance, and a downstream-style token/phoneme
fixture. spokenform does not own tokenization, lexicon lookup, phonemization,
quote/dash typography, or model punctuation. A downstream adapter should run a
dual comparison before removing its legacy normalizer.

Lexical abbreviations and numeric symbol recognition come from `abbr2words`; spokenform
supplies locale-owned semantic realization and exact source replacements. Do not
delete a downstream normalizer
until both paths have been compared for prepared text, source replacements,
extended token positions, phonemes, warnings, and protected overrides. A real
downstream gate is provided in `tests/test_real_kokorog2p_integration.py` and is
run in CI with released `kokorog2p[de,fr]` packages.

## Ownership audit

| Language | Suitable for spokenform                                                      | Keep downstream                                               | Status                                          |
| -------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------- | ----------------------------------------------- |
| cs       | dates, numbers, currencies, locale decimal/grouping semantics                | G2P and lexicon behavior                                      | caller-managed; parity corpus pending           |
| en       | dates, currencies, ordinary written numbers                                  | phoneme-sensitive years, digit-by-digit and suffix heuristics | ownership documented; parity corpus pending     |
| es       | dates, numbers, currencies, units                                            | G2P/tokenizer typography                                      | parser hardening covered; parity corpus pending |
| fr       | dates, times, numbers, ordinals, currencies, temperatures, units, exact maps | G2P/tokenizer typography, lexicon, phonemes                   | parity-gated; `STRUCTURED_AND_PLAIN`            |
| it       | dates, numbers, currencies, units                                            | G2P/tokenizer typography                                      | parser hardening covered; parity corpus pending |
| pt       | dates, numbers, currencies, units                                            | G2P/tokenizer typography                                      | parser hardening covered; parity corpus pending |

This audit intentionally does not port language detection, markup parsing, mixed
language orchestration, lexicon lookup, phoneme suffix rules, token IDs, or model
specific quote/dash behavior into spokenform. French is ready for downstream
handoff with the released `abbr2words>=0.2.2` prerequisite and the real French
parity gate; package publication remains the release workflow boundary.
