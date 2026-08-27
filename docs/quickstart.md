# Quickstart

```python
from spokenform import prepare

result = prepare(
    "Prof. Klein bringt am 14.05.2026 um 18:20 Uhr 2 kg mit.",
    language="de",
)

print(result.spoken_text)
print(result.render_changes())
```

## Japanese, Korean, and Chinese

````python
assert prepare("㈱東京は 20°C で 5 km 進む。", language="ja").spoken_text == (
    "株式会社東京は 摂氏 二十 度 で 五 キロメートル 進む。"
)
assert prepare("AI 시스템은 20°C 에서 5 km 이동한다.", language="ko").spoken_text == (
    "에이아이 시스템은 섭씨 이십도 에서 오 킬로미터 이동한다."
)
assert prepare("AI系统在 20°C 下运行，距离 5 km。", language="zh_CN").spoken_text == (
    "人工智能系统在 二十 摄氏度 下运行，距离 五 公里。"
)

## Swedish

```python
from spokenform import prepare

assert prepare("Vi har t.ex. 2 kg och temperaturen är 5 °C.", language="sv").spoken_text == (
    "Vi har till exempel två kilogram och temperaturen är fem grader Celsius."
)
````

Swedish uses comma decimals and reviewed quantities, temperatures, and Swedish krona amounts. Dates, digital times, arbitrary initialisms, and unreviewed specialist sequence domains remain caller-managed or fail closed.

## Vietnamese

```python
assert prepare(
    "TP. Hà Nội có 2 kg hàng với giá 1000 VND.",
    language="vi",
).spoken_text == (
    "thành phố Hà Nội có hai kilôgam hàng với giá một nghìn đồng Việt Nam."
)
```

Vietnamese uses comma decimals with exact fractional precision, dot or space-family grouping, reviewed quantities and VND/₫ amounts, and guarded dependency abbreviations. Dates, digital times, ordinals, arbitrary initialisms, and unreviewed specialist domains remain caller-managed or fail closed.

## Thai

```python
assert prepare("ระยะ 5 กม.", language="th").spoken_text == "ระยะ ห้า กิโลเมตร"
```

Thai accepts Latin and Thai digits, point decimals, comma or space-family grouping, reviewed quantities, temperatures, and THB amounts. Dates, times, ordinals, ranges, and unreviewed specialist sequences remain caller-managed or fail closed.
Use canonical `ja`, `ko`, and `zh_CN` identifiers. The compatibility aliases are `jp` and `cn`.

The output is a `PreparedText` object. Its main fields are:

- `source_text`: input exactly as supplied;
- `clean_text`: plain text entering the pipeline;
- `spoken_text`: normalized text intended for a speech system;
- `stages`: ordered before/after records;
- `mapped_edits`: edits with source and output coordinates;
- `offset_map`: composed source/output boundary map;
- `warnings`: recoverable protection or spaCy issues.

## Configuration object

```python
from spokenform import PreparationConfig, prepare

config = PreparationConfig(
    language="en",
    expand_abbreviations=True,
    expand_numbers=True,
    normalize_whitespace=True,
    context=True,
)

result = prepare("The board is 2 in. wide.", config=config)
```

When `config` is supplied, it is authoritative for pipeline options.

For Czech downstream preparation, use the same adapter with an explicit language:

```python
from spokenform import prepare_for_kokorog2p

result = prepare_for_kokorog2p("1°C, 12,80 Kč, 18:20", language="cs")
assert result.spoken_text == "jeden stupeň Celsia, dvanáct korun a osmdesát haléřů, 18:20"
```

Czech semantic numbers and quantities are owned by spokenform; colon times stay
caller-managed.
