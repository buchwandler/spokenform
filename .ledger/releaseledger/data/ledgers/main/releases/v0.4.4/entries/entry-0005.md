---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 2
entry_id: entry-0005
release_version: v0.4.4
kind: fixed
summary:
  Fixed malformed locale-mismatched currency amounts being rewritten while
  preserving valid currency normalization
status: accepted
audience: null
scopes: []
source_refs:
  - git:f7308020137f5041241b6edd0d5aa9fe32bfd02c
paths:
  - spokenform/recognizers/sequences.py
  - tests/test_currency_regressions.py
issues: []
prs: []
sources:
  - git:f7308020137f5041241b6edd0d5aa9fe32bfd02c
contributors: []
breaking: false
internal: false
order: 5
---
