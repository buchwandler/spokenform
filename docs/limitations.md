# Limitations

- Each `prepare()` call processes one selected language.
- Language detection and mixed-language segmentation are external.
- SSMD and other markup must be parsed before calling `spokenform`.
- Date, time, currency, ordinal, and locale grammar is intentionally conservative.
- Invalid calendar dates and times are recognized as protected structured
  candidates and remain literal; ambiguous two-digit years remain unchanged.
- Protected spans use internal private-use sentinels. Inputs containing the same
  private-use characters are an uncommon edge case that should be covered before a
  stability release.
- `abbr2words` 0.2.0 accepts POS annotations, but its bundled registries do not yet
  require POS labels. spaCy therefore does not necessarily alter default output.
- Structured stage edits retain exact rule metadata. Abbreviation and generic
  number edits may still be reconstructed from deterministic diffs because
  `abbr2words` currently returns final text rather than semantic replacement
  objects.

# Limitations and readiness gates

spokenform is a one-language written-to-spoken layer. Callers own language
selection, mixed-language segmentation, markup/SSML, tokenization, lexicons,
phonemization, and model-specific punctuation.

German is the first kokorog2p parity target and has text, source mapping, and
downstream-style token/phoneme fixtures. Czech, Spanish, French, Italian,
Portuguese, and English number categories remain caller-managed until their own
parity corpora are approved. Unsupported language categories use an explicit
`NumberPolicy.NONE` warning rather than a generic `num2words` fallback.

Use `PreparationConfig.for_kokorog2p(language)` for a profile that keeps outer
run whitespace caller-owned, enables exact protection/mapping, and makes number
ownership visible. Do not remove a downstream normalizer until a dual-run
comparison covers text, source offsets, token boundaries, phonemes, and warnings.
