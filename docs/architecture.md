# Architecture

`spokenform.prepare()` applies explicit stages in this order:

1. validate the selected language and protected ranges;
2. discover caller-protected ranges and auto-detected literals such as URLs,
   email addresses, and (when not claimed semantically) semantic versions;
   `normalize_literals=True` opts high-confidence URL, e-mail, version, and
   contextual Roman rendering into structured ownership while caller spans
   remain absolute;
3. obtain or validate optional lexical annotations;
4. replace protected ranges with internal sentinels and remap annotation offsets;
5. normalize Unicode independently when enabled;
6. recognize complete high-confidence structured sequences, then ask `abbr2words`
   for source-aligned structured quantity identities and realize them with the
   selected locale's semantic grammar;
7. expand lexical abbreviations with exact `abbr2words` replacements;
8. verbalize remaining generic numeric forms according to `NumberPolicy`;
9. normalize whitespace according to independently configurable controls;
10. restore protected text and compose stage offset maps.

Each stage records its input, output, edits, and mapped edits. Structured and
abbreviation stages emit exact replacements; temporary text-only stages retain
deterministic diff edits only at stage scope. The final
`PreparedText.offset_map` composes all stage maps from `clean_text` coordinates to
`spoken_text` coordinates. `PreparedText.source_edits` contains composed
`SourceReplacement` records in original-source/final-output coordinates; it must
not be confused with stage-local `mapped_edits`.

All public source offsets refer to the original string passed to `prepare()`.
Final offsets refer to `PreparedText.spoken_text`. Boundary APIs expose explicit
left/right bias for insertions, deletions, and generated replacement text.

## Ownership boundary

`spokenform` owns plain-text normalization, protection, provenance, and coordinate
mapping. Callers own language selection, markup parsing, and mixed-language
segmentation. Downstream G2P systems own tokenization for phoneme generation,
lexicons, pronunciations, and vocabulary IDs.

spokenform owns semantic spacing and punctuation consumed by a structured or
lexical expression. Downstream G2P owns quote style, dash canonicalization,
apostrophe variants, and punctuation choices required only by a model tokenizer.

The structured boundary is deliberately split by locale: `abbr2words` recognizes
numeric symbols and returns the exact span, numeric lexeme, category, and canonical
identity; `spokenform.structured` dispatches to locale-owned English, German, French,
Spanish, Italian, Portuguese, or Czech semantic grammar. No symbol or alias inventory is copied
into spokenform. French owns its dates, h/colon times, ordinals, decimal digit
reading, quantities, temperatures, and currency decomposition. Spanish owns
reviewed dates, quantities, temperatures, currencies, and ordinary numbers;
Spanish colon times remain caller-managed. Italian owns reviewed dates,
quantities, temperatures, currencies, and ordinary numbers; Italian colon times
remain caller-managed. Portuguese owns reviewed dates, quantities, temperatures,
currencies, and ordinary numbers; Portuguese colon times remain caller-managed.
Czech owns reviewed dates, quantities, temperatures, currencies, ordinary numbers,
and canonical extended units; Czech colon times remain caller-managed. English
owns reviewed dates, validated clock times, canonical quantities and currencies,
a conservative ordinary-number pass, and reviewed contextual single-dot release
labels such as `bot 2.0`. That label rule uses `point oh` only in the reviewed
version context; ordinary decimals retain digit-wise zero wording. English
deliberately leaves years, suffix ordinals, Roman numerals, phone/ID sequences,
arbitrary multi-dot versions/IDs, numeric suffixes, and phoneme-sensitive helpers
downstream. G2P typography and phonemes stay downstream.

French is promoted to `NumberPolicy.STRUCTURED_AND_PLAIN` only after its parity
corpus and real downstream gate pass. Every locale replacement retains exact
source spans and composed source/output mapping, and partial caller protection
expands to a complete structured candidate before semantic matching.

Spanish is promoted to the same policy only after its parity corpus and real
`kokorog2p` `es`/`la` gate pass. Its plain-number stage protects reviewed dates,
time candidates, URLs, e-mail addresses, and semantic versions so policy
promotion cannot silently claim an unreviewed category.

Italian is promoted to the same policy after its parity corpus and real
`kokorog2p` Italian gate pass. Its plain-number stage protects valid and invalid
date candidates, colon-time candidates, URLs, e-mail addresses, and semantic
versions. Portuguese is promoted to the same policy after its parity corpus and
real `kokorog2p` Portuguese gate pass; its plain-number stage protects reviewed
dates, time candidates, URLs, e-mail addresses, and semantic versions. Czech is
promoted to the same policy with a structured-safe plain-number stage that
protects date/time candidates, URLs, e-mail addresses, semantic versions, and
canonical structured values; Czech colon times remain caller-managed. English is
promoted to the same policy after its parity corpus and real `kokorog2p` English
gate pass; its plain-number stage protects reviewed date/time candidates, URLs,
e-mail addresses, semantic versions, canonical unit candidates, and ambiguous
long digit strings. Its structured single-dot release-label rule is contextual
and yields to recognized quantity spans. All reviewed quantity and currency
symbols continue to come from `abbr2words`.

`prepare_for_kokorog2p()` is a deterministic one-language adapter. Its profile
preserves run boundaries, honors protected spans fail-closed, and does not perform
language detection, tokenization, G2P, or model-punctuation rewriting.

The downstream migration set currently includes `cs`, `de`, `fr`, `es`, `it`,
`pt`, and `en`. English is active on the kokorog2p spokenform adapter for
reviewed structured semantics, contextual single-dot release labels, and safe
ordinary-number categories. Years, suffix ordinals, Roman numerals, phone/ID and
arbitrary multi-dot sequences, numeric suffixes, and G2P decisions remain
downstream-owned.

## Structured precedence

Caller protection is absolute. Auto-detected literals are a fallback reservation
against partial generic rewrites; a complete semantic recognizer may claim an
auto-literal before it is reserved. Candidate conflict resolution gives priority
to canonical identifiers, then coordinates and formulas, contextual legal,
sports, and address forms, dates and times, contextual sequences,
quantities/currencies/temperatures, specialist music/math forms, and generic
acronym/product candidates. Fractions and date/phone ambiguity are resolved by
semantic candidate priority rather than regex iteration order.
Unclaimed or ambiguous forms remain opaque. Every selected candidate is still an
exact `Replacement`, so precedence does not weaken source/output mapping or
protected-span behavior.
