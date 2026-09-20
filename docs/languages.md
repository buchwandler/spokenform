# Languages

## Complete runtime registry

The generated capability matrix is maintained in [`language-coverage.md`](language-coverage.md). The public registry accepts these base families:

| Canonical code |
| -------------- |
| `am`           |
| `ar`           |
| `az`           |
| `be`           |
| `bg`           |
| `bn`           |
| `ca`           |
| `ce`           |
| `cs`           |
| `cy`           |
| `da`           |
| `de`           |
| `el`           |
| `en`           |
| `eo`           |
| `es`           |
| `et`           |
| `eu`           |
| `fa`           |
| `fi`           |
| `fr`           |
| `he`           |
| `hi`           |
| `hu`           |
| `hy`           |
| `id`           |
| `is`           |
| `it`           |
| `ja`           |
| `kk`           |
| `kn`           |
| `ko`           |
| `ka`           |
| `lt`           |
| `ku`           |
| `lv`           |
| `lb`           |
| `mn`           |
| `ml`           |
| `mr`           |
| `nl`           |
| `ne`           |
| `no`           |
| `pl`           |
| `pt`           |
| `ro`           |
| `ru`           |
| `sk`           |
| `sl`           |
| `sq`           |
| `sr`           |
| `sv`           |
| `sw`           |
| `te`           |
| `tet`          |
| `tg`           |
| `th`           |
| `tr`           |
| `uk`           |
| `ur`           |
| `vi`           |
| `zh`           |

The 18 exact overlays are `en_GB`, `en_IN`, `en_NG`, `en_US`, `es_CO`, `es_CR`, `es_GT`, `es_MX`, `es_NI`, `es_VE`, `fr_BE`, `fr_CH`, `fr_DZ`, `pt_BR`, `pt_PT`, `zh_CN`, `zh_HK`, and `zh_TW`.

The 13 foundation families `bg`, `el`, `et`, `eu`, `ka`, `ku`, `lb`, `ml`, `mr`, `ne`, `sq`, `sw`, and `ur` provide reviewed plain-number rendering and safe Abbr2words registration. Foundation registration does not imply a bundled abbreviation lexicon or structured-number support.

# Language support matrix

| `ar` | `ara` | `ar_MSA` | `numeralform` | `ar` | yes | reviewed | conservative | reviewed | caller-managed | fail closed for unreviewed domains |
| `he` | `heb` | `he_IL` | `numeralform` | `he` | yes | reviewed | conservative | reviewed | caller-managed | fail closed for unreviewed domains |
| `kk` | `kaz` | `kk_KZ` | `numeralform` | `kk` | yes | conservative | conservative | reviewed | caller-managed | fail closed for unreviewed domains |

This page is the canonical runtime support matrix for `spokenform`. It describes
implemented capabilities, not full parity with PolyNorm, benchmarks, or
kokorog2p.

| Canonical code | Accepted aliases | Region forms      | Number renderer | Abbreviation profile                     | Plain numbers | Decimals                                      | Quantities                            | Currencies     | Dates and times                                              | Shared specialist sequences                         |
| -------------- | ---------------- | ----------------- | --------------- | ---------------------------------------- | ------------- | --------------------------------------------- | ------------------------------------- | -------------- | ------------------------------------------------------------ | --------------------------------------------------- |
| `cs`           | none             | none              | `numeralform`   | `cs`                                     | yes           | comma                                         | yes                                   | CZK            | reviewed, conservative time                                  | reviewed, conservative                              |
| `de`           | none             | `de_DE`           | `numeralform`   | `de`                                     | yes           | comma                                         | yes                                   | EUR            | validated digital times and context-sensitive dates/ordinals | legal, phone, percent, and other reviewed sequences |
| `en`           | none             | `en_GB`, `en_US`  | `numeralform`   | `en`                                     | yes           | point                                         | yes                                   | reviewed       | reviewed                                                     | reviewed, conservative                              |
| `es`           | none             | `es_MX`           | `numeralform`   | `es`, exact `es_MX`                      | yes           | comma or point by locale                      | yes                                   | reviewed       | reviewed                                                     | reviewed, conservative                              |
| `fr`           | none             | `fr_FR`           | `numeralform`   | `fr`                                     | yes           | comma                                         | yes                                   | reviewed       | reviewed                                                     | reviewed, conservative                              |
| `it`           | none             | `it_IT`           | `numeralform`   | `it`                                     | yes           | comma                                         | yes                                   | reviewed       | reviewed                                                     | reviewed, conservative                              |
| `ja`           | `jp`             | `ja_JP`           | `numeralform`   | `ja`                                     | yes           | reviewed                                      | yes                                   | JPY            | reviewed                                                     | conservative                                        |
| `ko`           | none             | `ko_KR`           | `numeralform`   | `ko`                                     | yes           | reviewed                                      | yes                                   | KRW            | reviewed                                                     | conservative                                        |
| `pt`           | none             | `pt_BR` / `pt_PT` | `numeralform`   | `pt`, `pt_BR`, base fallback for `pt_PT` | yes           | comma                                         | yes                                   | EUR            | reviewed                                                     | reviewed, conservative                              |
| `sv`           | `swe`            | `sv_SE` / `sv-SE` | `numeralform`   | `sv`                                     | yes           | comma                                         | yes                                   | SEK / `kr`     | caller-managed dates and digital times                       | fail closed for unreviewed domains                  |
| `vi`           | none             | `vi_VN` / `vi-VN` | `numeralform`   | `vi`                                     | yes           | comma decimal; dot or space-family grouping   | reviewed                              | VND / `₫`      | caller-managed dates and digital times                       | fail closed for unreviewed domains                  |
| `th`           | none             | `th_TH` / `th-TH` | `numeralform`   | `th`                                     | yes           | point decimal; comma or space-family grouping | reviewed                              | THB / `฿`      | caller-managed dates, eras, and digital times                | fail closed for unreviewed domains                  |
| `ru`           | `rus`            | `ru_RU` / `ru-RU` | `numeralform`   | `ru`                                     | yes           | comma decimal; space/NBSP/NNBSP grouping      | reviewed, explicit numeral government | caller-managed | caller-managed dates and digital times                       | fail closed for unreviewed domains                  |
| `zh`           | none             | none              | `cn2an`         | `zh`                                     | yes           | reviewed                                      | yes                                   | conservative   | reviewed                                                     | conservative                                        |

## German scope

German structured normalization validates Gregorian dates and digital times, including
complete-word handling for `Uhr`, and applies bounded contextual inflection to dates
and ordinals. German owns conservative contextual year speech through the shared
`render_year()` policy, reviewed Euro major/minor realization with explicit Cent
labels, and exact excess-fraction preservation. Date, text-date, hyphen-date, and
time candidates validate full lexical boundaries and reject identifier adjacency.
German `§` and conservative `§§` paragraph references, percentages, and contextual
phone sequences are owned by typed structured recognizers and remain subject to
precedence, protection, and recognition-domain policy. Ordinary abbreviations,
including the reviewed `vgl.`, `i.d.R.`, `o.ä.`, and `u.U.` forms, remain owned by
`abbr2words`; they are not duplicated in this locale. Currencies without reviewed
minor-unit grammar use a safe exact decimal fallback or fail closed.

German also recognizes reviewed source-letter technical labels such as `IP`, `IBAN`, and `LTS` through `abbr2words`. With `normalize_literals=True`, German URL, e-mail, and FTP promotion uses localized `Doppelpunkt`, `Schrägstrich`, and `Punkt` words, lexical hostname and path labels, and the reviewed `de`, `org`, `net`, and `com` TLD policy. Contextual Roman year and monarch forms, redundant century notation, explicit hour-minute durations, and semantic versions with preserved leading-zero components are handled by Spokenform's structured recognizers.

## Swedish scope

Swedish uses comma decimal punctuation and space, NBSP, or NNBSP grouping.
Plain numbers, reviewed quantities, Celsius and Fahrenheit temperatures, and
Swedish krona amounts are supported. Swedish quantity grammar uses the reviewed
`abbr2words` canonical unit identities and explicit singular and plural forms.

`sv-SE` and `sv_SE` normalize to the registered base key `sv`. `swe` is accepted as a compatibility alias, and
`swe-SE` also normalizes to `sv`.

Swedish digital clock bodies and numeric dates remain caller-managed in this
release, although valid shapes are protected from generic number rewriting.
Arbitrary initialisms and unreviewed address, legal, phone, ISBN, music,
biology, chemistry, math, and range semantics fail closed. Supported languages
must not borrow English fallback vocabulary solely because a shared semantic
renderer lacks a locale entry.

## Vietnamese scope

Vietnamese uses comma decimal punctuation. Spokenform accepts CLDR-style dot grouping and regular, non-breaking, or narrow non-breaking space grouping; fractional digits are rendered digitwise to preserve written precision. Reviewed quantities, temperatures, and VND/₫ identities come from `abbr2words`, while Numeralform owns non-Chinese numeric realization and Spokenform owns source mapping. `vi-VN` and `vi_VN` normalize to the regional form and resolve to the Vietnamese Numeralform base locale. Dates, digital times, ordinals, arbitrary initialisms, and unreviewed specialist sequence domains remain caller-managed or fail closed.

## Thai scope

Thai accepts `th`, `th_TH`, and `th-TH`; regional forms route to Numeralform and `abbr2words`. No `tha` alias is claimed. The CLDR-style point decimal marker and comma, regular-space, NBSP, or NNBSP grouping are supported, with Latin digits as the default and Thai digits also accepted.

Reviewed quantities, temperatures, and THB/`฿` identities come from `abbr2words`; Spokenform owns Thai numeric realization and source mapping. Reviewed titles, month and era abbreviations, and the `น.` clock marker may expand, but date and year bodies, digital times, numeric-only dates, and eras remain caller-managed. Thai ordinals, ranges, and unreviewed specialist sequences remain literal or fail closed, with no English semantic fallback.

## Russian scope

Russian accepts `ru`, `ru_RU`, and `ru-RU`; `rus`, `rus_RU`, and `rus-RU` are compatibility aliases. Regional forms route to the Russian Numeralform and `abbr2words` locales.

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
