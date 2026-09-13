---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: v0.4.2
kind: added
summary: Added locale-aware currency and exchange-rate speech rendering for English,
  German, and Spanish
status: accepted
audience: null
scopes: []
source_refs:
- git:8922f28f22cd0d9093b97e51ee2a16d256aac796
paths:
- README.md
- benchmarks/polynorm_eval.py
- docs/migration-kokorog2p.md
- docs/profiles.md
- docs/release-checklist.md
- pyproject.toml
- spokenform/casing.py
- spokenform/currency.py
- spokenform/locales/de.py
- spokenform/locales/en.py
- spokenform/locales/es.py
- spokenform/number_words.py
- spokenform/precedence.py
- spokenform/recognizers/sequences.py
- tests/test_currency_regressions.py
- tests/test_packaging.py
- tests/test_polynorm_currency_regressions.py
- tests/test_polynorm_eval.py
issues: []
prs: []
sources:
- git:8922f28f22cd0d9093b97e51ee2a16d256aac796
contributors: []
breaking: false
internal: false
order: 1
---
