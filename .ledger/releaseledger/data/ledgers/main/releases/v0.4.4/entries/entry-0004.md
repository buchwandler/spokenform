---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0004
release_version: v0.4.4
kind: fixed
summary:
  Fixed URL-like literals being treated as math and made unsupported math locales
  fail closed
status: accepted
audience: null
scopes: []
source_refs:
  - git:8626e5e47e9db43a3bdaf18a08e83d44b904fd98
paths:
  - spokenform/recognizers/sequences.py
  - tests/test_de_gold_failure_regressions.py
  - tests/test_literal_promotion.py
  - tests/test_pt_structured.py
  - tests/test_specialists.py
issues: []
prs: []
sources:
  - git:8626e5e47e9db43a3bdaf18a08e83d44b904fd98
contributors: []
breaking: false
internal: false
order: 4
---
