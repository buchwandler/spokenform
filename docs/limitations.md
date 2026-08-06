# Limitations

- Each `prepare()` call processes one selected language.
- Language detection and mixed-language segmentation are external.
- SSMD and other markup must be parsed before calling `spokenform`.
- Date, time, currency, ordinal, and locale grammar is intentionally conservative.
- Invalid calendar dates may match the current numeric date pattern; callers that
  require calendar validation should validate dates before normalization.
- Protected spans use internal private-use sentinels. Inputs containing the same
  private-use characters are an uncommon edge case that should be covered before a
  stability release.
- `abbr2words` 0.2.0 accepts POS annotations, but its bundled registries do not yet
  require POS labels. spaCy therefore does not necessarily alter default output.
- Stage edits are reconstructed from deterministic text diffs because `abbr2words`
  currently returns final text rather than semantic replacement objects.
