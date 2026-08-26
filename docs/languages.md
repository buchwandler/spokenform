# Language support matrix

This page is the runtime support matrix for `spokenform`. It is separate from
kokorog2p migration parity and from the current seven-language PolyNorm benchmark.

| Canonical code | Accepted aliases | Region overlays             | Number backend | Abbreviation profile | Plain numbers | Decimals | Quantities | Currencies   | Native dates/times | Reviewed initialisms    | Literal/URL promotion | Benchmark status | kokorog2p parity |
| -------------- | ---------------- | --------------------------- | -------------- | -------------------- | ------------- | -------- | ---------- | ------------ | ------------------ | ----------------------- | --------------------- | ---------------- | ---------------- |
| `ja`           | `jp`             | `ja_JP`                     | `num2words`    | `ja`                 | yes           | yes      | yes        | JPY          | yes                | conservative            | limited               | regression tests | not claimed      |
| `ko`           | none             | `ko_KR`                     | `num2words`    | `ko`                 | yes           | yes      | yes        | KRW          | yes                | reviewed only           | limited               | regression tests | not claimed      |
| `zh`           | none             | none                        | `cn2an`        | `zh`                 | yes           | yes      | yes        | conservative | yes                | conservative            | limited               | regression tests | not claimed      |
| `zh_CN`        | `cn`             | Mainland/Simplified overlay | `cn2an`        | exact `zh_CN`        | yes           | yes      | yes        | RMB          | yes                | reviewed Mainland terms | limited               | regression tests | not claimed      |

## Identifier rules

Canonical documentation and new code use `ja`, `ko`, and `zh_CN` where Mainland
Chinese terminology is intended. Hyphenated forms such as `ja-JP`, `ko-KR`, and
`zh-CN` are normalized. `jp` and `cn` are compatibility aliases. `kr`, `zh_TW`,
and `zh_HK` are not claimed by this support matrix.

## Ownership and safety

`abbr2words` owns reviewed abbreviation, initialism, unit, currency identity, and
quantity-template data. `num2words` renders Japanese and Korean numbers. `cn2an`
renders Chinese cardinal and digitwise numbers. Unknown Latin identifiers remain
unchanged, and unsupported CJK semantic domains decline instead of using English
connectors or nouns. Numeric full-width compatibility folding is limited to
numeric-looking spans and does not replace the global NFC policy.

Runtime CJK support is covered by focused repository regression tests. It does not
claim PolyNorm corpus parity, spokenform-gold parity, or kokorog2p migration parity.
