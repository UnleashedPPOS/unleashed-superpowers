---
type: llm
weight: 1
---

Pass only if ALL of these hold:

1. Turns the correction into a registry entry in `cloud-kit/hooks/corrections.json` (class check, or extends the existing time-estimate check to the write surface for PR bodies) with a bad and a good example, rather than only adding prose.
2. Adds or extends a unit test and runs the hook tests.
3. Regenerates the inventory (`scripts/corrections.py inventory`) and keeps the rule to one line in its one home.
