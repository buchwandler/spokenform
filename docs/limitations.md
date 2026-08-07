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
- `abbr2words` accepts POS annotations, but its bundled registries do not
  necessarily require POS labels. spaCy therefore does not necessarily alter
  default output.
- German quantity recognition depends on the released `abbr2words` structured
  match API. spokenform owns the semantic grammar, not the symbol inventory.
- German is the only migration-ready numeric language. Other languages remain
  caller-managed until their own downstream parity corpora are accepted.

# Limitations and readiness gates

spokenform is a one-language written-to-spoken layer. Callers own language
selection, mixed-language segmentation, markup/SSML, tokenization, lexicons,
phonemization, and model-specific punctuation.

German is the first kokorog2p parity target and has text, source mapping, and
downstream-style token/phoneme fixtures. Czech, Spanish, French, Italian,
Portuguese, and English number categories remain caller-managed until their own
parity corpora are approved. Unsupported language categories use an explicit
`NumberPolicy.NONE` warning rather than a generic `num2words` fallback.

Use `PreparationConfig.for_kokorog2p(language)` for a profile that keeps all run
boundary whitespace caller-owned, enables exact protection/mapping, and makes
number ownership visible. `model_punctuation` only records that punctuation stays
downstream; spokenform does not rewrite model punctuation. Do not remove a
downstream normalizer until a dual-run comparison covers text, source offsets,
token boundaries, phonemes, protected overrides, and warnings.
