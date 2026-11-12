---
name: python-bugfix-playbook
description: Checklists for common Python library bug patterns (argument handling, None/default handling, typing/pydantic validation, async/sync parity, encoding and header handling, rendering/width). Load a resource when the root cause is unclear.
---

# Python bug-fix playbook

Load one resource that matches the issue, then return to editing:

- `resources/patterns.md` - root-cause checklists by symptom (wrong default, None handling, missing kwarg, async/sync divergence, type coercion, unicode/bytes, off-by-one in rendering).
- `resources/verification.md` - how to verify quickly and keep the diff clean.
