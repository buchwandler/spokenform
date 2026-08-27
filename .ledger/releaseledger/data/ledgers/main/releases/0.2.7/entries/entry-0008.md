---
schema_version: 2
object_type: release_entry
versioning:
  schema_version: 1
  revision: 1
entry_id: entry-0008
release_version: 0.2.7
kind: added
summary:
  Added Russian runtime support for locale-aware numbers and reviewed measurement
  quantities
status: accepted
audience: null
scopes: []
source_refs:
  - tl:task-0061
paths:
  - spokenform/locales/ru.py
  - spokenform/numbers.py
issues: []
prs: []
sources: []
contributors: []
breaking: false
internal: false
order: 8
---

Russian comma decimals, space-family grouping, reviewed temperatures, and explicit one/few/many/other numeral-government forms are supported through canonical dependency identities.
