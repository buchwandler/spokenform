---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0003
release_version: 0.3.2
kind: added
summary:
  Added Japanese, Korean, and Chinese runtime support with locale-aware numbers
  and conservative sequences
status: accepted
audience: null
scopes: []
source_refs:
  - git:2a3be9cc5cc78b23ac066562b0a3e97d15761337
paths:
  - .github/workflows/tests.yml
  - README.md
  - docs/api.md
  - docs/architecture.md
  - docs/benchmarks.md
  - docs/changelog.md
  - docs/cli.md
  - docs/index.md
  - docs/languages.md
  - docs/limitations.md
  - docs/migration-kokorog2p.md
  - docs/polynorm.md
  - docs/quickstart.md
  - docs/release-checklist.md
  - pyproject.toml
  - spokenform/__init__.py
  - spokenform/api.py
  - spokenform/config.py
  - spokenform/dates.py
  - spokenform/language.py
  - spokenform/locales/_cjk.py
  - spokenform/locales/cs.py
  - spokenform/locales/de.py
  - spokenform/locales/en.py
  - spokenform/locales/es.py
  - spokenform/locales/fr.py
  - spokenform/locales/it.py
  - spokenform/locales/ja.py
  - spokenform/locales/ko.py
  - spokenform/locales/pt.py
  - spokenform/locales/zh.py
  - spokenform/number_words.py
  - spokenform/numbers.py
  - spokenform/numeric_lexeme.py
  - spokenform/recognizers/biology.py
  - spokenform/recognizers/ranges.py
  - spokenform/recognizers/references.py
  - spokenform/recognizers/sequences.py
  - spokenform/recognizers/temporal.py
  - spokenform/sequences.py
  - spokenform/structured.py
  - tests/test_cjk_architecture.py
  - tests/test_cjk_fullwidth_numbers.py
  - tests/test_cjk_no_english_fallback.py
  - tests/test_dependency_contract.py
  - tests/test_ja.py
  - tests/test_ko.py
  - tests/test_language.py
  - tests/test_number_words.py
  - tests/test_packaging.py
  - tests/test_sequence_fallback.py
  - tests/test_sequences.py
  - tests/test_zh_cn.py
issues: []
prs: []
sources:
  - git:2a3be9cc5cc78b23ac066562b0a3e97d15761337
contributors: []
breaking: false
internal: false
order: 3
---
