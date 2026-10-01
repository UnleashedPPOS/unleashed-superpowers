---
description: Falsify "it's done / all good" claims from this session — the adversarial pass. Attacks every claim of correctness with a disconfirming experiment, fixes what cracks, and only reports when the surface is genuinely clean. Also runs as Stage 2 of /ship-check — this command and that stage both invoke the `red-team` skill, so there is one source of truth; edit `skills/red-team/SKILL.md`, never this file's body.
---

Load the `red-team` skill (`skills/red-team/SKILL.md`) from this plugin and run it in full — Phase 0 Claim Ledger through Phase 4 Report, including the AI-native-coverage and voice-coverage attack lanes in Phase 2 — against the scope named in `$ARGUMENTS` (or this session's claims + `git log origin/main..HEAD` if empty).

Do not restate or re-derive the skill's methodology here — this file exists only to bind `/red-team` to that skill so standalone invocations and `/ship-check` Stage 2 never drift out of sync. If you find yourself writing falsification logic in this file instead of the skill, stop and put it in the skill instead.

Print the skill's Phase 4 report verbatim, verdict line last as the skill specifies (**SURVIVED** / **NOT SURVIVED**).
