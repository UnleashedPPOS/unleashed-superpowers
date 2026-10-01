# /ship-check — Phase 7 report template (exact format)

Use verbatim structure. Every applicable Automated Passes row MUST cite agent id / finding count / fix SHA.

```markdown
# Ship-Check: <feature or branch>

## Intent
- <5–10 bullets from Phase 0>

## Checklist (evidence in parens)
| Area | Status | Notes |
|------|--------|-------|
| Build, Types, Tests | ✅ / ⚠️ / ❌ | `<build cmd>` exit 0, `<test cmd>` X/X pass |
| DB & Migrations | ... | `information_schema.columns` queried; RLS row in `pg_policies` |
| Edge Functions | ... | v<N> deployed, log sample timestamp |
| Security & Privacy | ... | grep hits = 0; advisors delta = 0 |
| Accessibility | ... | |
| UX Failure Paths | ... | auth-race guard verified |
| Dead Code & Simplicity | ... | |
| Docs | ... | |
| Git Hygiene | ... | |
| Cross-PR Interactions | ... | N landed mid-session; M overlap; all resolved |

## Automated Passes (every applicable row MUST cite agent id / finding count / fix SHA)
| Pass | Agent/Skill (model) | Ran (evidence) | Outcome / Commit |
|------|---------------------|----------------|------------------|
| code-review (superpowers) | `superpowers:code-reviewer` (sonnet) | <agent id + N findings> | <SHA / none> |
| code-review (ecc/lang) | `everything-claude-code:code-reviewer` (sonnet) | <agent id + N findings> | <SHA / none> |
| security-review | `everything-claude-code:security-reviewer` (sonnet/opus) | <agent id + verdict> | <SHA / none> |
| dead-code/dup | `everything-claude-code:refactor-cleaner` (sonnet) | <agent id + N findings> | refactor SHA |
| simplify | `/simplify` | <diff applied?> | <SHA / none> |
| code-review apply | `/code-review --fix` | <findings applied?> | <SHA / none> |
| UX friction | repo UX skill / manual | <top issues> | parked / none |
| repo coverage audit | e.g. `voice-coverage-audit` (if defined) | <matrix refreshed?> | <SHA / n/a> |
| docs sync | `doc-updater` / `/update-docs` | <ran?> | <SHA / n/a> |
| superpowers review loop | requesting-/receiving-code-review | <ran?> | triage outcome |

## Smoke
- Edge fn logs: <2xx timestamp or "0 invocations yet">
- Sentry: <open issues in session scope>
- Preview: <screenshot + console error count, or "n/a">
- e2e: <pass/fail or "n/a">

## Lessons Captured
- <one per tasks/lessons.md entry, or "none — no corrections">

## Deferred (user-approved)
- <item + reason, linked to the tracking doc>

## Verdict
**SHIPPABLE** — evidence above covers every section.

## Merges (Phase 6)
| PR # | Title | Squash SHA | Content Proof |
|------|-------|------------|---------------|
| <N> | ... | <sha> | <symbol>:<file>:<line-count> |

## Post-Merge Deploy Proof (6.6)
| Deployable | Proof |
|------------|-------|
| <Vercel prod / edge fn / Netcup service> | <version tied to merge SHA + real request showing the change live> |

## Adversarial Verification (6.7 — /red-team)
- Claims attacked: <N> | Cracked → fixed: <N> | Owned-elsewhere: <N> | Genuine-external: <N>
- Verdict: **SURVIVED** / <link to separate report>

Final open PR count (in-scope): **0**.
Drift / Deploy Migrations / Supabase Drift / Sentinel Health: **all GREEN** on `<main HEAD>`.
```
