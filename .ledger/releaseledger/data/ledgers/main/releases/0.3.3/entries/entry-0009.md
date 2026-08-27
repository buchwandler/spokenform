---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0009
release_version: 0.3.3
kind: quality
summary:
  Added Thai regression coverage for decimal precision, Thai digits, quantities,
  THB, calendar protection, mapping, and sequence safety
status: accepted
audience: null
scopes: []
source_refs: []
paths:
  - tests/test_th_structured.py
  - tests/test_th_sequences.py
  - tests/test_language.py
  - tests/test_number_words.py
  - tests/test_dependency_contract.py
issues: []
prs: []
sources:
  - tl:task-0062
contributors: []
breaking: false
internal: false
order: 9
---
