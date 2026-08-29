# Language support matrix

This page is the canonical runtime support matrix for `spokenform`. It describes
implemented capabilities, not full parity with PolyNorm, benchmarks, or
kokorog2p.

| Canonical code | Accepted aliases | Region forms      | Number backend | Abbreviation profile | Plain numbers | Decimals                                      | Quantities                            | Currencies     | Dates and times                                              | Shared specialist sequences                         |
| -------------- | ---------------- | ----------------- | -------------- | -------------------- | ------------- | --------------------------------------------- | ------------------------------------- | -------------- | ------------------------------------------------------------ | --------------------------------------------------- |
| `cs`           | none             | none              | `num2words`    | `cs`                 | yes           | comma                                         | yes                                   | CZK            | reviewed, conservative time                                  | reviewed, conservative                              |
| `de`           | none             | `de_DE`           | `num2words`    | `de`                 | yes           | comma                                         | yes                                   | EUR            | validated digital times and context-sensitive dates/ordinals | legal, phone, percent, and other reviewed sequences |
| `en`           | none             | `en_GB`, `en_US`  | `num2words`    | `en`                 | yes           | point                                         | yes                                   | reviewed       | reviewed                                                     | reviewed, conservative                              |
| `es`           | none             | `es_MX`           | `num2words`    | `es`, exact `es_MX`  | yes           | comma or point by locale                      | yes                                   | reviewed       | reviewed                                                     | reviewed, conservative                              |
| `fr`           | none             | `fr_FR`           | `num2words`    | `fr`                 | yes           | comma                                         | yes                                   | reviewed       | reviewed                                                     | reviewed, conservative                              |
| `it`           | none             | `it_IT`           | `num2words`    | `it`                 | yes           | comma                                         | yes                                   | reviewed       | reviewed                                                     | reviewed, conservative                              |
| `ja`           | `jp`             | `ja_JP`           | `num2words`    | `ja`                 | yes           | reviewed                                      | yes                                   | JPY            | reviewed                                                     | conservative                                        |
| `ko`           | none             | `ko_KR`           | `num2words`    | `ko`                 | yes           | reviewed                                      | yes                                   | KRW            | reviewed                                                     | conservative                                        |
| `pt`           | none             | `pt_BR`           | `num2words`    | `pt`, `pt_BR`        | yes           | comma                                         | yes                                   | EUR            | reviewed                                                     | reviewed, conservative                              |
| `sv`           | `swe`            | `sv_SE` / `sv-SE` | `num2words`    | `sv`                 | yes           | comma                                         | yes                                   | SEK / `kr`     | caller-managed dates and digital times                       | fail closed for unreviewed domains                  |
| `vi`           | none             | `vi_VN` / `vi-VN` | `num2words`    | `vi`                 | yes           | comma decimal; dot or space-family grouping   | reviewed                              | VND / `₫`      | caller-managed dates and digital times                       | fail closed for unreviewed domains                  |
| `th`           | none             | `th_TH` / `th-TH` | `num2words`    | `th`                 | yes           | point decimal; comma or space-family grouping | reviewed                              | THB / `฿`      | caller-managed dates, eras, and digital times                | fail closed for unreviewed domains                  |
| `ru`           | `rus`            | `ru_RU` / `ru-RU` | `num2words`    | `ru`                 | yes           | comma decimal; space/NBSP/NNBSP grouping      | reviewed, explicit numeral government | caller-managed | caller-managed dates and digital times                       | fail closed for unreviewed domains                  |
| `zh`           | none             | none              | `cn2an`        | `zh`                 | yes           | reviewed                                      | yes                                   | conservative   | reviewed                                                     | conservative                                        |

## German scope

German structured normalization validates Gregorian dates and digital times, including
complete-word handling for `Uhr`, and applies bounded contextual inflection to dates
and ordinals. Currency output preserves the established two-digit minor-unit style;
fractional precision beyond two digits is rendered as an exact decimal rather than
silently rounded or truncated. German `§` and conservative `§§` paragraph references,
percentages, and contextual phone sequences are owned by typed structured recognizers
and remain subject to precedence, protection, and recognition-domain policy. Ordinary
abbreviations remain owned by `abbr2words`; unsupported additions such as `gem.` and
`Abt.` are not duplicated in this locale.

## Swedish scope

Swedish uses comma decimal punctuation and space, NBSP, or NNBSP grouping.
Plain numbers, reviewed quantities, Celsius and Fahrenheit temperatures, and
Swedish krona amounts are supported. Swedish quantity grammar uses the reviewed
`abbr2words` canonical unit identities and explicit singular and plural forms.

`sv-SE` and `sv_SE` are normalized to the regional form and routed to the
Swedish base language. `swe` is accepted as a compatibility alias, and
`swe-SE` normalizes to `sv_SE`.

Swedish digital clock bodies and numeric dates remain caller-managed in this
release, although valid shapes are protected from generic number rewriting.
Arbitrary initialisms and unreviewed address, legal, phone, ISBN, music,
biology, chemistry, math, and range semantics fail closed. Supported languages
must not borrow English fallback vocabulary solely because a shared semantic
renderer lacks a locale entry.

## Vietnamese scope

Vietnamese uses comma decimal punctuation. Spokenform accepts CLDR-style dot grouping and regular, non-breaking, or narrow non-breaking space grouping; fractional digits are rendered digitwise to preserve written precision. Reviewed quantities, temperatures, and VND/₫ identities come from `abbr2words`, while Spokenform owns numeric realization and source mapping. `vi-VN` and `vi_VN` normalize to the regional form and resolve to the Vietnamese base dependency registries. Dates, digital times, ordinals, arbitrary initialisms, and unreviewed specialist sequence domains remain caller-managed or fail closed.

## Thai scope

Thai accepts `th`, `th_TH`, and `th-TH`; regional forms route to the base `num2words` and `abbr2words` registries. No `tha` alias is claimed. The CLDR-style point decimal marker and comma, regular-space, NBSP, or NNBSP grouping are supported, with Latin digits as the default and Thai digits also accepted.

Reviewed quantities, temperatures, and THB/`฿` identities come from `abbr2words`; Spokenform owns Thai numeric realization and source mapping. Reviewed titles, month and era abbreviations, and the `น.` clock marker may expand, but date and year bodies, digital times, numeric-only dates, and eras remain caller-managed. Thai ordinals, ranges, and unreviewed specialist sequences remain literal or fail closed, with no English semantic fallback.

## Russian scope

Russian accepts `ru`, `ru_RU`, and `ru-RU`; `rus`, `rus_RU`, and `rus-RU` are compatibility aliases. Regional forms route to the Russian `num2words` and `abbr2words` base registries.

Russian plain numbers use comma decimal punctuation, regular spaces, NBSP, or NNBSP grouping, with visible fractional digits spoken digitwise. Reviewed `abbr2words` canonical unit identities are rendered by Spokenform using explicit CLDR `one`, `few`, `many`, and `other` noun forms. Counted feminine units use gender-aware `одна` and `две` forms, and output is limited to nominative measurement phrases.

Dates, digital times, year abbreviations, phone-number speech, and specialist sequences remain caller-managed or fail closed. Currency is caller-managed, including `RUB`, until `abbr2words` provides a reviewed Russian ruble identity. Unknown future Russian canonical unit IDs are preserved until a matching Spokenform grammar entry is reviewed.

Spokenform does not use `vn` as a language alias.

## Identifier rules

Canonical documentation and new code use the canonical codes in the first
column. Hyphenated regional forms are normalized to underscore forms. `jp`,
`cn`, `swe`, and `rus` are compatibility aliases where shown. `kr` is not a language
alias. Unknown language identifiers are rejected by the runtime rather than
being guessed.

## Ownership and safety

`abbr2words` owns reviewed abbreviation, initialism, unit, currency identity,
and quantity-template recognition. `spokenform` owns locale semantic grammar,
numeric punctuation policies, source-aligned replacements, and protection. For
Russian specifically, `abbr2words` owns recognition and canonical unit identity,
while Spokenform owns numeral government and explicit noun morphology. Swedish,
Vietnamese, and Russian unsupported specialist sequence domains preserve source
text instead of emitting English connectors, nouns, or punctuation names.
Runtime support is covered by focused regression tests. It does not claim
benchmark parity, PolyNorm parity, or kokorog2p parity unless those gates are
listed separately for a language.
