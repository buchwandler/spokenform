---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0004
release_version: 0.2.7
kind: quality
summary:
  Added explicit coverage, documentation, artifact, wheel, and downstream release
  gates
status: accepted
audience: null
scopes: []
source_refs: []
paths:
  - .github/workflows/tests.yml
  - .github/workflows/python-publish.yml
  - tests/test_docs_consistency.py
  - tests/test_packaging.py
issues: []
prs: []
sources:
  - tl:task-0041
contributors: []
breaking: false
internal: false
order: 4
---
