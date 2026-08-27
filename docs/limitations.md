# Limitations

- Each `prepare()` call processes one selected language.
- Language detection and mixed-language segmentation are external.
- SSMD and other markup must be parsed before calling `spokenform`.
- Date, time, currency, ordinal, and locale grammar is intentionally conservative.
- Invalid calendar dates and times remain literal; ambiguous standalone versions,
  phone-like strings without context, and generic serials remain protected or
  downstream-owned rather than being partially rewritten.
- Protected spans use allocated private-use sentinels that are checked against the
  current input, so existing private-use characters are preserved literally.
- `abbr2words` accepts POS annotations, but its bundled registries do not
  necessarily require POS labels. spaCy therefore does not necessarily alter
  default output.
- German quantity recognition depends on the released `abbr2words` structured
  match API. spokenform owns the semantic grammar, not the symbol inventory.
- English, German, French, Spanish, Italian, Portuguese, Czech, Japanese, Korean, Russian, Swedish, Vietnamese, and Chinese have explicit runtime structured policies. Japanese, Korean, Russian, Swedish, Vietnamese, and Chinese runtime support is covered by focused regression tests, but it does not imply kokorog2p or PolyNorm parity.
- Japanese and Korean use released `num2words`; Chinese uses released `cn2an`. Generic `zh` is conservative, while Mainland reviewed terminology and RMB live under exact `zh_CN`. `zh_TW` and `zh_HK` are not claimed.
- Swedish uses comma decimals, space/NBSP/NNBSP grouping, reviewed quantities, temperatures, and SEK currency grammar. Numeric dates and digital times are caller-managed but protected from generic rewriting; arbitrary initialisms and unreviewed specialist domains fail closed instead of borrowing English vocabulary.
- Vietnamese runtime support covers reviewed plain-number punctuation, exact decimal precision, canonical quantities, temperatures, VND/₫ amounts, and dependency-backed guarded abbreviations. Vietnamese dates, digital times, ordinals, arbitrary initialisms, and unreviewed specialist semantic domains remain caller-managed or fail closed.
- Russian runtime support covers ordinary cardinals, comma decimals, reviewed canonical quantities and temperatures, and nominative numeral-government forms. It does not infer arbitrary surrounding grammatical case. Numeric dates, digital times, year abbreviations, currency including RUB, phone-number speech, arbitrary initialisms, and unreviewed specialist semantic domains remain caller-managed or fail closed. Unknown future Russian `abbr2words` canonical unit IDs are preserved until a Spokenform grammar entry is reviewed.
- `jp` and `cn` are compatibility aliases for `ja` and `zh_CN`; `kr` is intentionally rejected. Unknown CJK-adjacent Latin identifiers remain unchanged, and ambiguous date formats remain unclaimed.
- CJK date/time and semantic renderers use reviewed native forms. Unsupported phone, ISBN, reference, legal, music, biology, geography, sports, chemistry, and math constructions decline rather than borrowing English words.
  Spanish explicit AM/PM forms use a 12-hour conversational branch, while
  unqualified 24-hour forms retain their written hour/minute values in speech.
  English owns a conservative contextual single-dot release-label
  rule (`bot 2.0` -> `bot two point oh`) in addition to ordinary decimals. It
  does not apply `oh` globally: ordinary decimal zeros remain digit-wise,
  quantities take precedence, and years, suffix ordinals, Roman numerals,
  phone/ID sequences, arbitrary multi-dot versions, numeric suffixes, and
  phoneme-sensitive helpers remain reserved for kokorog2p.
- French decimal money is decomposed deterministically into major and minor
  units; reviewed fixtures define spelling and preserve written fractional
  precision rather than delegating to a third-party currency string.
- Spanish decimal quantities and money are decomposed deterministically from
  written fractional digits; reviewed fixtures define major/minor wording and
  Spanish one-ending agreement rather than delegating grammar to `num2words`.

High-confidence structured sequences include slash and Unicode fractions,
coordinates, ISBNs, UUIDs, IPv4, MAC addresses, IBANs, locale-grouped phones,
versions, hashtags, mentions, conservative chemical formulas, explicit acronym
policies, labeled serial/VIN/product codes, legal references, sports scores,
address components, operator-shaped math, music-context tokens, and controlled
genus/species names. URL, e-mail, version, and contextual Roman promotion is
opt-in through `normalize_literals`; caller protection remains absolute. Broad
natural-language address, legal, mathematical, musical, and biological parsing
remains outside the core contract. Unlabeled ambiguous alphanumeric strings
remain unchanged rather than being memorized as product codes.

Benchmark profiles do not change that boundary: `default` is the release-safe
contract, `extended` is an opt-in diagnostic profile, and an aggressive caller
experiment is not a release gate. Compare only compatible report identities;
questionable upstream targets remain quarantined and visible rather than being
used to justify a normalization rule. See
[benchmarks/OWNERSHIP.md](https://github.com/buchwandler/spokenform/blob/main/benchmarks/OWNERSHIP.md).

# Limitations and readiness gates

spokenform is a one-language written-to-spoken layer. Callers own language
selection, mixed-language segmentation, markup/SSML, tokenization, lexicons,
phonemization, and model-specific punctuation.

German was the first kokorog2p parity target. English has a direct spokenform API
parity contract; French, Spanish, Italian, and Portuguese now
have text, source mapping, downstream token/phoneme, protection, and
released-stack fixtures. Portuguese and Czech time remain caller-managed.
Czech and English semantic number categories are owned by
spokenform, and English is active on the kokorog2p spokenform adapter for
reviewed structured semantics, contextual single-dot release labels, and safe
ordinary-number categories. English phoneme-sensitive years, suffix ordinals,
Roman numerals, phone/ID and arbitrary multi-dot sequences, numeric suffixes, and
G2P decisions remain downstream-owned. Unsupported
language categories use an explicit
`NumberPolicy.NONE` warning rather than a generic `num2words` fallback.

Use `PreparationConfig.for_kokorog2p(language)` for a profile that keeps all run
boundary whitespace caller-owned, enables exact protection/mapping, and makes
number ownership visible. `model_punctuation` only records that punctuation stays
downstream; spokenform does not rewrite model punctuation. Do not remove a
downstream normalizer until a dual-run comparison covers text, source offsets,
token boundaries, phonemes, protected overrides, and warnings.

## Recognition modes and specialist domains

`contextual` remains the default compatibility mode. `surface` is intentionally fail-closed and context-independent, not a promise to spell every unknown token; genuinely ambiguous strings may be preserved. `disabled_domains` can suppress specialist families independently, with `chemistry` covering the current chemical-formula recognizer. Domain suppression can reduce speechability by design and is not a rendering fallback. Legacy `context` still controls abbreviation context only. An orthographic fallback for conservative sequence-shaped residual spans is opt-in through `sequence_fallback_mode="spell"`; it does not spell ordinary lexical prose. The default remains `sequence_fallback_mode="preserve"`.

Explicit `allowed_domains` is fail-closed for candidates without recognized domain metadata. It is intended for callers that need a stable semantic permitlist across future Spokenform releases.
