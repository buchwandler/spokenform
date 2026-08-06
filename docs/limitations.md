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
