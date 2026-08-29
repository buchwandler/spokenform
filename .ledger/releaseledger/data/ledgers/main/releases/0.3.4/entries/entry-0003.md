---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0003
release_version: 0.3.4
kind: changed
summary:
  Improved currency speech to preserve excess fractional precision instead
  of silently rounding or truncating
status: accepted
audience: null
scopes: []
source_refs: []
paths:
  - spokenform/locales/_cjk.py
  - spokenform/locales/cs.py
  - spokenform/locales/de.py
  - spokenform/locales/fr.py
  - spokenform/locales/it.py
  - spokenform/locales/pt.py
  - spokenform/locales/sv.py
  - spokenform/numeric_lexeme.py
  - spokenform/recognizers/sequences.py
  - tests/test_de_misaki_regressions.py
issues: []
prs: []
sources:
  - git:6fafaa1c9e69cfc4d25b5f3bbe19c710a0d3e72f
contributors: []
breaking: false
internal: false
order: 3
---
