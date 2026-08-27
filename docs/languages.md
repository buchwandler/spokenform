# Language support matrix

This page is the canonical runtime support matrix for `spokenform`. It describes
implemented capabilities, not full parity with PolyNorm, benchmarks, or
kokorog2p.

| Canonical code | Accepted aliases | Region forms      | Number backend | Abbreviation profile | Plain numbers | Decimals                                    | Quantities | Currencies   | Dates and times                        | Shared specialist sequences        |
| -------------- | ---------------- | ----------------- | -------------- | -------------------- | ------------- | ------------------------------------------- | ---------- | ------------ | -------------------------------------- | ---------------------------------- |
| `cs`           | none             | none              | `num2words`    | `cs`                 | yes           | comma                                       | yes        | CZK          | reviewed, conservative time            | reviewed, conservative             |
| `de`           | none             | `de_DE`           | `num2words`    | `de`                 | yes           | comma                                       | yes        | EUR          | reviewed                               | reviewed, conservative             |
| `en`           | none             | `en_GB`, `en_US`  | `num2words`    | `en`                 | yes           | point                                       | yes        | reviewed     | reviewed                               | reviewed, conservative             |
| `es`           | none             | `es_MX`           | `num2words`    | `es`, exact `es_MX`  | yes           | comma or point by locale                    | yes        | reviewed     | reviewed                               | reviewed, conservative             |
| `fr`           | none             | `fr_FR`           | `num2words`    | `fr`                 | yes           | comma                                       | yes        | reviewed     | reviewed                               | reviewed, conservative             |
| `it`           | none             | `it_IT`           | `num2words`    | `it`                 | yes           | comma                                       | yes        | reviewed     | reviewed                               | reviewed, conservative             |
| `ja`           | `jp`             | `ja_JP`           | `num2words`    | `ja`                 | yes           | reviewed                                    | yes        | JPY          | reviewed                               | conservative                       |
| `ko`           | none             | `ko_KR`           | `num2words`    | `ko`                 | yes           | reviewed                                    | yes        | KRW          | reviewed                               | conservative                       |
| `pt`           | none             | `pt_BR`           | `num2words`    | `pt`, `pt_BR`        | yes           | comma                                       | yes        | EUR          | reviewed                               | reviewed, conservative             |
| `sv`           | `swe`            | `sv_SE` / `sv-SE` | `num2words`    | `sv`                 | yes           | comma                                       | yes        | SEK / `kr`   | caller-managed dates and digital times | fail closed for unreviewed domains |
| `vi`           | none             | `vi_VN` / `vi-VN` | `num2words`    | `vi`                 | yes           | comma decimal; dot or space-family grouping | reviewed   | VND / `₫`    | caller-managed dates and digital times | fail closed for unreviewed domains |
| `zh`           | none             | none              | `cn2an`        | `zh`                 | yes           | reviewed                                    | yes        | conservative | reviewed                               | conservative                       |

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

Spokenform does not use `vn` as a language alias.

## Identifier rules

Canonical documentation and new code use the canonical codes in the first
column. Hyphenated regional forms are normalized to underscore forms. `jp`,
`cn`, and `swe` are compatibility aliases where shown. `kr` is not a language
alias. Unknown language identifiers are rejected by the runtime rather than
being guessed.

## Ownership and safety

`abbr2words` owns reviewed abbreviation, initialism, unit, currency identity,
and quantity-template recognition. `spokenform` owns locale semantic grammar,
numeric punctuation policies, source-aligned replacements, and protection.
`num2words` owns generic Swedish number words. Unsupported Swedish specialist
sequence domains preserve source text instead of emitting English connectors,
nouns, or punctuation names.

Runtime support is covered by focused regression tests. It does not claim
benchmark parity, PolyNorm parity, or kokorog2p parity unless those gates are
listed separately for a language.
