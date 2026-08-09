# Limitations

- Each `prepare()` call processes one selected language.
- Language detection and mixed-language segmentation are external.
- SSMD and other markup must be parsed before calling `spokenform`.
- Date, time, currency, ordinal, and locale grammar is intentionally conservative.
- Invalid calendar dates and times are recognized as protected structured
  candidates and remain literal; ambiguous two-digit years remain unchanged.
- Protected spans use allocated private-use sentinels that are checked against the
  current input, so existing private-use characters are preserved literally.
- `abbr2words` accepts POS annotations, but its bundled registries do not
  necessarily require POS labels. spaCy therefore does not necessarily alter
  default output.
- German quantity recognition depends on the released `abbr2words` structured
  match API. spokenform owns the semantic grammar, not the symbol inventory.
- English, German, French, Spanish, Italian, Portuguese, and Czech have parity-gated
  structured ownership. Spanish, Italian, Portuguese, and Czech time
  expressions remain caller-managed because no reviewed time ownership contract
  is included. English intentionally reserves years, suffix ordinals, Roman
  numerals, phone/ID sequences, dotted versions, numeric suffixes, and
  phoneme-sensitive helpers for kokorog2p.
- French decimal money is decomposed deterministically into major and minor
  units; reviewed fixtures define spelling and preserve written fractional
  precision rather than delegating to a third-party currency string.
- Spanish decimal quantities and money are decomposed deterministically from
  written fractional digits; reviewed fixtures define major/minor wording and
  Spanish one-ending agreement rather than delegating grammar to `num2words`.

# Limitations and readiness gates

spokenform is a one-language written-to-spoken layer. Callers own language
selection, mixed-language segmentation, markup/SSML, tokenization, lexicons,
phonemization, and model-specific punctuation.

German was the first kokorog2p parity target. English has a direct spokenform API
parity contract; French, Spanish, Italian, and Portuguese now
have text, source mapping, downstream token/phoneme, protection, and
released-stack fixtures. Spanish, Italian, Portuguese, and Czech time remain
caller-managed. Czech and English semantic number categories are owned by
spokenform. The current kokorog2p semantic migration set excludes English, so
its downstream adapter retains context-sensitive numeric categories. Unsupported
language categories use an explicit
`NumberPolicy.NONE` warning rather than a generic `num2words` fallback.

Use `PreparationConfig.for_kokorog2p(language)` for a profile that keeps all run
boundary whitespace caller-owned, enables exact protection/mapping, and makes
number ownership visible. `model_punctuation` only records that punctuation stays
downstream; spokenform does not rewrite model punctuation. Do not remove a
downstream normalizer until a dual-run comparison covers text, source offsets,
token boundaries, phonemes, protected overrides, and warnings.
