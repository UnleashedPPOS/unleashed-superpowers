---
description: Fill the Unleashed Definition-of-Done ledger for the current feature/PR and print the verdict line first.
---

Load the `definition-of-done` skill from this plugin and produce the ledger for the feature named in `$ARGUMENTS` (or the current branch's diff if none). One row per checklist item, state in caps first (DONE · N/A (why) · OWNER (who, what) · NOT DONE). The first line is the verdict. Never write "deferred".
