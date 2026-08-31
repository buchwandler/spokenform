# kokorog2p migration boundary

spokenform can serve a downstream adapter for one selected language run. Call
`prepare_for_kokorog2p()` (or pass `PreparationConfig.for_kokorog2p()`), preserve
caller override spans with `ProtectedSpan`, use `PreparedText.source_edits` and
the public span helpers to remap boundaries, and inspect `warnings` before passing
the result to a G2P tokenizer. The adapter projection is available through
`PreparedText.to_adapter_dict()`.

The English, German, French, Spanish, Italian, Portuguese, and Czech downstream
migration contracts are tested at three boundaries: spoken text,
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
run in CI with released `kokorog2p[de,fr]` packages; SpanishG2P and ItalianG2P
are part of the base package and are exercised by the same gate.

## Ownership audit

| Language | Suitable for spokenform                                                                                                            | Keep downstream                                                                                                                       | Status                                                                    |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| cs       | reviewed dates, ordinary numbers, quantities, temperatures, currencies, canonical units                                            | G2P/lexicon behavior; colon times                                                                                                     | parity-gated; `STRUCTURED_AND_PLAIN`; time caller-managed                 |
| en       | dates, validated clock times, currencies, reviewed quantities, safe ordinary written numbers, contextual single-dot release labels | phoneme-sensitive years, suffix ordinals, Roman numerals, phone/ID and arbitrary multi-dot sequences, numeric suffixes, G2P decisions | active adapter / parity-gated; downstream-only categories remain explicit |
| es       | reviewed dates, ordinary numbers, currencies, units, temperatures                                                                  | G2P/tokenizer typography; time expressions                                                                                            | parity-gated; `STRUCTURED_AND_PLAIN`; time caller-managed                 |
| fr       | dates, times, numbers, ordinals, currencies, temperatures, units, exact maps                                                       | G2P/tokenizer typography, lexicon, phonemes                                                                                           | parity-gated; `STRUCTURED_AND_PLAIN`                                      |
| it       | reviewed dates, ordinary numbers, currencies, units, temperatures                                                                  | G2P/tokenizer typography; colon-time ownership                                                                                        | parity-gated; `STRUCTURED_AND_PLAIN`; colon times caller-managed          |
| pt       | reviewed dates, ordinary numbers, currencies, units, temperatures                                                                  | G2P/tokenizer typography; colon-time expressions                                                                                      | parity-gated; `STRUCTURED_AND_PLAIN`; time caller-managed                 |

English's safe plain-number pass intentionally handles only ordinary short or
grouped cardinals and exact decimal digits. A separate reviewed structured rule
handles contextual single-dot release labels such as `bot 2.0` and renders the
fractional zero as `oh`; it does not change ordinary decimal wording. Quantity
matches take precedence over that contextual rule. Four-digit and longer ungrouped
digit strings remain raw so years, identifiers, and sequence-like values reach
kokorog2p's `NumberConverter` and related heuristics. A structured candidate
with unsupported fractional currency precision also remains unchanged.

English is active on the kokorog2p spokenform adapter for reviewed structured
semantics, contextual single-dot release labels, and safe ordinary-number
categories. Phoneme-sensitive years, suffix ordinals, Roman numerals, phone/ID
and arbitrary multi-dot sequences, numeric suffixes, and G2P decisions remain
downstream in kokorog2p; the adapter does not claim those categories.

This audit intentionally does not port language detection, markup parsing, mixed
language orchestration, lexicon lookup, phoneme suffix rules, token IDs, or model
specific quote/dash behavior into spokenform. French, Spanish, Italian, and
Portuguese are
ready for downstream handoff only with the released `abbr2words>=0.2.12,<0.3.0`
prerequisite and their real parity gates; package publication remains the release
workflow boundary. Spanish, Italian, Portuguese, and Czech time ownership is
intentionally deferred until reviewed time corpora exist. English semantic
number categories are available in the direct spokenform API, while years,
ordinals, Roman numerals, phone/ID and dotted sequences, numeric suffixes, and
G2P decisions remain downstream-owned.

## Preferred adapter surface

Downstream integrations should depend on the stable high-level surface:
`PreparationConfig.for_kokorog2p(language)`, `prepare_for_kokorog2p()`,
`PreparedText.source_replacements`, `PreparedText.offset_map`, and
`NumberPolicy`. Low-level mapping and stage helpers remain exported for advanced
use but are not required for a normal kokorog2p adapter.

## Compatibility cleanup

KokoroG2P's historical Thai and Korean normalizer modules are compatibility adapters only. Their semantic number, counter, unit, currency, and time behavior delegates to Spokenform. Prepared-input G2P paths bypass these adapters and perform pronunciation, tokenization, and model sanitation only.

The semantic transfer manifest at `tests/data/kokorog2p_semantic_transfer_manifest.json` records the source test or fixture, its classification, and its permanent Spokenform destination. The refreshed KokoroG2P oracle baseline resolves product aliases before calling Spokenform.
