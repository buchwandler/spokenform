---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0001
release_version: v0.4.1
kind: changed
summary: Improved locale-aware numeric, currency, identifier, emergency-number, and
  German reference normalization
status: accepted
audience: null
scopes: []
source_refs:
- git:75510e391bdc768c99e75242c70f625a82f8d14b
paths:
- benchmarks/failure_reporting.py
- benchmarks/polynorm_eval.py
- spokenform/locales/de.py
- spokenform/locales/it.py
- spokenform/recognizers/sequences.py
- tests/test_numeralform_migration_regressions.py
- tests/test_polynorm_eval.py
issues: []
prs: []
sources:
- git:75510e391bdc768c99e75242c70f625a82f8d14b
contributors: []
breaking: false
internal: false
order: 1
---
