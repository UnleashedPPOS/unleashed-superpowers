# /red-team — Phase 4 report template (reference)

Read by `commands/red-team.md` Phase 4. Fill it exactly.

```markdown
# Red-Team: <scope>

## Claim Ledger
Legend (never inflate): `✅ SURVIVED` = experiment RAN, claim held. `🔬 INSPECTED` = read and looks correct, experiment NOT run (low-risk textbook patterns only; say why not run). `🔴 CRACKED` = falsified → next table.
| Claim | Disconfirming experiment | Evidence | Outcome |
|-------|--------------------------|----------|---------|
| <"sends via SES"> | Real SMTP AUTH+send with the stored credential | 250 OK + receipt | ✅ SURVIVED |

## Cracks found → fixed → re-proven (MINE-TO-FIX)
| Crack | Why it was invisible | Fix (PR/SHA) | Re-attack evidence |
|-------|----------------------|--------------|--------------------|

## Owned elsewhere (tracked, not my fix)
| Crack | Owner (PR/branch + recency) | How I confirmed it covers the crack |
|-------|-----------------------------|-------------------------------------|

## Hidden-failure sweep
- Secrets in git: 0 (grep proof)
- Leftovers / drift / observability / others' WIP: <each proven clean, fixed above, or flagged hands-off>

## Honest residual risk
- <Genuinely external only: credentials, business calls, platform limits + graceful degradation. NOT a backlog.>

## Verdict
**SURVIVED** — every claim attacked; every MINE-TO-FIX crack fixed + merged + re-proven; every OWNED-ELSEWHERE crack confirmed covered by a live effort. Nothing left for you to chase that is mine to chase.
```
