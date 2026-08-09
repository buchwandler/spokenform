# kokorog2p migration boundary

spokenform can serve a downstream adapter for one selected language run. Call
`prepare_for_kokorog2p()` (or pass `PreparationConfig.for_kokorog2p()`), preserve
caller override spans with `ProtectedSpan`, use `PreparedText.source_edits` and
the public span helpers to remap boundaries, and inspect `warnings` before passing
the result to a G2P tokenizer. The adapter projection is available through
`PreparedText.to_adapter_dict()`.

The English, German, French, Spanish, Italian, and Portuguese integration contracts are tested at three boundaries: spoken text,
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

| Language | Suitable for spokenform                                                      | Keep downstream                                               | Status                                                    |
| -------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------------------- |
| cs       | reviewed dates, ordinary numbers, quantities, temperatures, currencies, canonical units | G2P/lexicon behavior; colon times | parity-gated; `STRUCTURED_AND_PLAIN`; time caller-managed |
| en       | dates, validated clock times, currencies, reviewed quantities, safe ordinary written numbers | phoneme-sensitive years, suffix ordinals, Roman numerals, phone/ID and dotted sequences, numeric suffixes, G2P decisions | parity-gated; `STRUCTURED_AND_PLAIN`; downstream-sensitive forms reserved |
| es       | reviewed dates, ordinary numbers, currencies, units, temperatures            | G2P/tokenizer typography; time expressions                    | parity-gated; `STRUCTURED_AND_PLAIN`; time caller-managed |
| fr       | dates, times, numbers, ordinals, currencies, temperatures, units, exact maps | G2P/tokenizer typography, lexicon, phonemes                   | parity-gated; `STRUCTURED_AND_PLAIN`                      |
| it       | reviewed dates, ordinary numbers, currencies, units, temperatures            | G2P/tokenizer typography; colon-time ownership                | parity-gated; `STRUCTURED_AND_PLAIN`; colon times caller-managed |
| pt       | reviewed dates, ordinary numbers, currencies, units, temperatures             | G2P/tokenizer typography; colon-time expressions               | parity-gated; `STRUCTURED_AND_PLAIN`; time caller-managed  |

English's safe plain-number pass intentionally handles only ordinary short or
grouped cardinals and exact decimal digits. Four-digit and longer ungrouped
digit strings remain raw so years, identifiers, and sequence-like values reach
kokorog2p's `NumberConverter` and related heuristics. A structured candidate
with unsupported fractional currency precision also remains unchanged.

This audit intentionally does not port language detection, markup parsing, mixed
language orchestration, lexicon lookup, phoneme suffix rules, token IDs, or model
specific quote/dash behavior into spokenform. French, Spanish, Italian, and
Portuguese are
ready for downstream handoff only with the released `abbr2words>=0.2.2`
prerequisite and their real parity gates; package publication remains the release
workflow boundary. Spanish, Italian, Portuguese, and Czech time ownership is
intentionally deferred until reviewed time corpora exist. English semantic
number categories are owned by spokenform, while its reserved downstream forms
remain under kokorog2p ownership.
