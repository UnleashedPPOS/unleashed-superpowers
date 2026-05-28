---
description: End-of-session production audit with auto-merge. Reconstructs session intent, then RUNS the full review chain — parallel reviewer fan-out (superpowers:code-reviewer + everything-claude-code code/security reviewers + refactor-cleaner) followed by the mutating cleanup skills (/simplify, /code-review --fix, /ux-simplify, voice-coverage-audit, doc-updater) wrapped in the superpowers requesting-/receiving-code-review loop — verifies branch topology + cross-PR interactions, captures lessons, then AUTOMATICALLY merges open PRs from this session when the verdict is SHIPPABLE and the branch is ISOLATED. Senior-dev mode — no manual hand-holding, no half-done anything, reviewers actually execute (no self-asserted "looks good"). Pass `--no-merge` to stop before the merge phase. Pass `--scope=<freeform>` to override the inferred session intent. Operates on `$ARGUMENTS` (defaults to current branch / recent commits).
---

# /ship-check — Evidence-Based Production Audit + Auto-Merge

You are the senior engineer signing off before real users touch the code. **No gaps. No silent bugs. No security holes. No half-done anything.** If something was supposed to happen and didn't, you find it and you finish it. When the audit lands a clean verdict, you **merge the work yourself** — the user does not click anything.

Target scope: `$ARGUMENTS` (if empty, infer from `git log origin/main..HEAD` plus the in-conversation intent — **bounded strictly to THIS session's work**, never historical PRs or unrelated branches).

Flags:
- `--no-merge` — run the full audit but stop before Phase 6. Use only when the user wants to review before shipping.
- `--scope=<freeform>` — override the auto-inferred session intent (e.g. `--scope="PR #309 + cross-PR interactions"`).

---

## Prime Directive — Evidence Before Assertions

You do not write `✅` without proof — command output, a file quote, a DB query result, a deployment ID, a git SHA. Per `superpowers:verification-before-completion`: if you did not run it, it is `⚠️` (unchecked), not `✅`. A `⚠️` in the final report is acceptable. A false `✅` is a firing offence.

Before any checkmark, write one line citing the artefact that proved it (e.g. `bun run build` exit 0; `pg_policies` row for `onboarding_rewards`; Sentry issue count = 0; `git diff --stat` showing only intended files).

**Memory references that govern this command:**
- `feedback_subagent_completion_verification.md` — return strings ≠ proof of done. Verify via git log + agent-summary.md on disk + content proof. Multi-PR merge waves: GitHub `mergeable` flag LAGS; verify with `git merge-base --is-ancestor` + content proofs.
- `feedback_merge_with_failing_checks.md` — never defer failing/pending checks. Required CI green at merge time.
- `feedback_senior_dev.md` — apply obvious best-practice fixes autonomously; ask only on real design choices.

---

## Phase 0 — Reconstruct THIS Session's Intent

You cannot judge "complete" without the goal. Bounded strictly to this conversation's work. In order:

1. **Read `tasks/todo.md`** (project root) if present — primary source for stated goals.
2. **`git log origin/main..HEAD --oneline`** (or vs the base branch) — every commit subject is a claimed deliverable.
3. **Re-read the user's early messages in this conversation** — what was actually asked for, what was deferred, what was parked.
4. **Read `tasks/lessons.md`** for in-session corrections — those are rules you now must honour.
5. **Read `.claude/agent-summary.md`** if any subagents wrote receipts this session — that is the running ledger.

Output an **Intent Summary** (5–10 bullets): features shipped, schema changes, new files, deprecations, parked items. If anything is ambiguous (e.g. user said "the stuff we discussed"), ask for one-line confirmation **before any audit runs**. Do not guess.

**Scope fence:** ignore anything outside this session — other people's PRs, historical work, unrelated branches. If a recent merge into main interacts with your work, that lands in Phase 5 (cross-PR check), not Phase 0.

---

## Phase 1 — Ship-Readiness Checklist

Walk every section. For each `⚠️` or `❌`: **fix it in this session** unless the user has explicitly deferred it in Phase 0. Cite evidence.

### 1.1 Build, Types, Tests (`superpowers:verification-before-completion`)
- [ ] `bun run build` exits 0
- [ ] `bun run lint` — zero **new** errors from this session's files (pre-existing called out separately)
- [ ] `bunx vitest run` (or the affected suite) passes — never `bun test` (wrong runner per repo memory)
- [ ] `bunx tsc -p tsconfig.app.json --noEmit` clean (ignore pre-existing `types.ts` corruption if present; flag separately)
- [ ] No `any` where a concrete type would cover
- [ ] `src/integrations/supabase/types.ts` reflects schema changes this session (query `information_schema.columns` to verify parity)
- [ ] Every new pure function / data invariant has at least one vitest assertion
- [ ] Destructive UI actions (delete, overwrite) have confirmation OR are covered by a test
- [ ] **No self-contradicting tests/evals/fixtures.** For every test or eval case ADDED this session, grep the existing corpus for a case with a near-identical input but a *different* expected outcome (e.g. two "feeling X today" cases expecting different tools). A contradiction means at least one is wrong or the routing rule is undefined — resolve it (pick the canonical expectation, fix both) before shipping. A contradictory corpus produces flaky, meaningless green.

### 1.2 Database & Migrations — **Migration Drift Verification Mandatory** (per `supabase/CLAUDE.md`)
- [ ] Every new file in `supabase/migrations/` has been **applied** — verify via Supabase MCP querying `information_schema.columns` / `pg_indexes` / `pg_policies`. **"Ran the CLI" is not evidence; only a SELECT against the live project is.**
- [ ] Every new table has RLS enabled and an owner-pattern policy (`user_id = auth.uid()` or parent-ownership via `EXISTS`). Prove with a `pg_policies` row.
- [ ] Columns filtered at query time have an index (check `pg_indexes`).
- [ ] `supabase_migrations.schema_migrations` has a row for every repo migration (diff `ls supabase/migrations/` against the table). If diverged, `supabase migration repair --status applied <ts>` per the cleanup pattern documented in `.claude/agent-summary.md` Backend Cleanup section.
- [ ] `mcp__supabase__get_advisors(type='security')` and `get_advisors(type='performance')` — zero **new** advisories on this session's tables.

### 1.3 Edge Functions (project convention: `verify_jwt=false` + in-code `getClaims`)
- [ ] Deployed version matches repo — `mcp__supabase__list_edge_functions` → `updated_at` newer than last `git log` touching the function.
- [ ] Auth via `supabase.auth.getClaims(token)` (not `.getUser()`).
- [ ] Rate-limited via `rateLimitDb` on any user-facing endpoint.
- [ ] Wrapped in `withObservability(...)`.
- [ ] Server-side input validation: numbers clamped, enums against allow-lists, strings length-capped.
- [ ] User-generated text in an LLM prompt lives in the `user` role wrapped in explicit delimiters (`<context>…</context>`); never raw in `system`.
- [ ] Every `JSON.parse` / `response.json()` is in `try/catch` or guarded (`Array.isArray` etc.).
- [ ] `supabase/config.toml` `[functions.<name>]` has `verify_jwt = false`.
- [ ] Silent-write protection: every `await supabase.from(X).{insert,update,upsert,delete}(...)` wrapped with `assertWriteOk` / `assertOk` per the Voice Wave 3 pattern (PR #279).

### 1.4 Security & Privacy (auto-invoke `everything-claude-code:security-review` skill when applicable)
Auto-trigger if this session touched: authentication, user input, API endpoints, secrets, payments, or new edge functions.
- [ ] `git grep -rnE "(sk_|AKIA|AIza|eyJ[A-Za-z0-9_-]{20,})"` on new files — zero hits.
- [ ] Toast messages / logs do not leak `user_id`, email, phone, or query keys. Use hashed `user_bucket` (per `feedback_sentry_gdpr_identifiers.md`).
- [ ] CORS via `getCorsHeaders(req)`, not `*`.
- [ ] Frontend uses `extractErrorMessage(e)` from `@/lib/error-utils`, never `String(error)` (CLAUDE.md rule).
- [ ] Any PII sent to an LLM is justified and minimised (titles over bodies, clamped snippets).

### 1.5 Accessibility
- [ ] Dynamic / rotating content has `aria-live="polite"` or equivalent.
- [ ] Motion respects `prefers-reduced-motion` (`useReducedMotion()` from framer-motion).
- [ ] Interactive elements have accessible names (`aria-label`, visible text, or both).
- [ ] Hover-only interactions have keyboard / touch equivalents (focus pause, delayed unpause).

### 1.6 UX Failure Paths
- [ ] Every mutation has `onError` that surfaces the real reason via `extractErrorMessage`.
- [ ] 429 / 402 responses become human toasts ("Rate limited", "Credits exhausted").
- [ ] Empty states exist for brand-new users.
- [ ] Loading states exist for every `useQuery` (Skeleton or spinner).
- [ ] No silent route bounces — every Protected/Gated component gates on `loading` BEFORE redirecting (per PR #309 auth-race lesson). Grep `src/` for `isAuthenticated` callers; flag any that don't gate on `loading`.

### 1.7 Dead Code & Simplicity
- [ ] No unused imports, variables, or exports introduced.
- [ ] No duplicated query / mutation logic across ≥2 consumers — lift to a hook.
- [ ] No commented-out code "just in case".
- [ ] No dead defensive defaults (`X[slot] ?? 10_000` when `X` is typed `as const` with fixed length).

### 1.8 Docs (per `CLAUDE.md`: "A code change without a doc update counts as incomplete")
- [ ] Every touched feature module has its `docs/feature-modules/<module>/` updated: README / behaviour / edge-functions / hooks / schema.
- [ ] Voice Coverage Matrix in `future.md` reflects new actions (rows added; closed rows flipped).
- [ ] `CLAUDE.md` updated if a new project-wide convention was introduced.
- [ ] If the module has no docs folder yet, invoke `/document-feature-module <module>`.

### 1.9 Git Hygiene
- [ ] Every commit subject describes one discrete concern.
- [ ] No uncommitted staged work belongs to this session.
- [ ] Unrelated working-tree changes are **not** in session commits — run `git log --name-only origin/main..HEAD`; spot files that do not belong to the stated intent.
- [ ] **Committed-files-vs-intent diff (explicit).** For every commit YOU authored this session, run `git show --name-only <sha>` and check EACH file against the Phase 0 intent. Any file not tied to the stated intent is a stray that rode along (this session swept `.claude/commands/red-team.md` into a voice-fix commit). Flag it; split it out with `git rebase`/`git reset` if not yet merged, or note it loudly if it is.
- [ ] Branch is pushed.
- [ ] No secrets, `.env`, or large binaries staged by accident (`git diff --stat origin/main..HEAD`).

### 1.10 Cross-PR Interaction Audit (NEW)
Anything that merged into main DURING this session could collide with your work. Check:
- [ ] `git log <session-start-sha>..origin/main --oneline` — list of "other" PRs that landed mid-session.
- [ ] For each, scan the diff: does it touch a file you touched? An import you added? A schema you altered?
- [ ] If overlap: re-run the relevant subset of Phase 1 against the rebased state. Flag any new conflict / regression.

### 1.11 Branch Topology & Merge-Isolation Gate (NEW — run BEFORE assuming anything about merge)
A session's worst blind spot is treating "merge it" as trivial when the branch is actually a many-commit, multi-author, no-PR shared track. **Compute the branch's real shape before Phase 5/6, every time:**
- [ ] **Commits ahead:** `git rev-list --count origin/main..HEAD`. If > your own session commit count, the branch carries other work you'd ship as a side effect.
- [ ] **Authorship:** `git log origin/main..HEAD --format='%an %s'`. List which commits are YOURS vs others'. If foreign commits exist, your work is **not** isolable — any merge to main ships theirs too.
- [ ] **PR existence:** `gh pr list --head <branch> --state open`. No PR + many commits ahead = this is an integration branch, not a feature PR. Merging it is a track-level cutover, not a fix landing.
- [ ] **Live concurrency:** is anyone else still pushing? Check `git log` for foreign commits dated after your session start, a `.git/index.lock` collision, or a commit landing on top of your push. A live shared branch must NOT be merged out from under active work.
- [ ] **Isolation verdict:** classify the merge as **ISOLATED** (your commits only / a dedicated PR) or **ENTANGLED** (foreign commits, no dedicated PR, or concurrent pushes).
  - **ISOLATED** → Phase 6 auto-merge is in play.
  - **ENTANGLED** → auto-merge is **forbidden**. Squashing a multi-author track to main as a side effect of your fix is a firing offence. Surface the scope decision to the user (`AskUserQuestion`): merge the whole track now / open PR + hold / leave merge to the track owner. NEVER guess. Opening the PR for CI visibility is fine; merging is not.

---

## Phase 2 — Run the Missing Review Passes (in order) — MANDATORY, NOT SKIPPABLE-BY-ASSERTION

**A pass counts as "ran" ONLY if the actual review agent executed and produced findings you can quote — in THIS conversation.** "Tests pass + I eyeballed the diff" is NOT a code review. "Looks secure" is NOT a security review. A real failure mode this guards against: marking the audit done while these agents never ran, only for the code-reviewer to later find a real bug that would otherwise have shipped. So:
- You may "skip" a pass **only** if its agent genuinely ran earlier in this same conversation AND you cite the agent id / its findings. Absent that proof, you MUST invoke it now.
- The Phase 7 "Automated Passes" table requires a cited artefact per row (agent id, quoted finding count, or commit SHA of the fix). A row marked `ran` with no evidence is a false `✅` — same firing offence as elsewhere.
- A **SHIPPABLE** verdict is forbidden if any applicable pass did not actually execute this session.

**Run EVERY applicable pass below — running the full review chain is a primary reason this command exists.** Skipping the review fan-out and self-asserting "looks good" is the exact failure that shipped a real bug past a "passed" audit. Reviewers are read-only and run in parallel; cleanup/fix skills mutate the tree and run sequentially, each its own commit.

### 2.A — Reviewer fan-out (READ-ONLY, run IN PARALLEL — one message, multiple Agent calls)
These don't touch the tree, so dispatch them concurrently and collect structured findings. Give each a tight, scope-fenced brief (exact file list + the diff), and require findings ranked Blocker / Important / Nit with `file:line` evidence. Run **all that apply**:

1. **Code review (two independent lenses — run both):**
   - `superpowers:code-reviewer` agent (the superpowers reviewer — the user explicitly wants superpowers in the chain), AND
   - `everything-claude-code:code-reviewer` agent (or the language-specific reviewer when the diff is mostly one language: `everything-claude-code:python-reviewer`, `everything-claude-code:go-reviewer`).
   Two independent reviewers catch what one rationalises past. Diff/merge their findings.
2. **Security review** — `everything-claude-code:security-reviewer` agent. MANDATORY if the session touched auth, user input, API endpoints, secrets, payments, edge functions, or LLM prompts. Blockers fixed before merge, no exceptions.
3. **Dead-code / duplication analysis** — `everything-claude-code:refactor-cleaner` agent in REPORT mode (identify only) so its findings feed the sequential apply step below without racing the other reviewers.
4. **Voice coverage** — `voice-coverage-audit` skill scoped to the touched module if any voice/Stream surface changed.

Anti-watchdog (per `feedback_subagent_completion_verification.md`): foreground parallel Agent calls in a single message are fine; keep background subagents ≤2. Every brief carries the scope-fence file list and a "return findings as a ranked list with file:line, do not fix" instruction. After each returns, verify by quoting its actual findings — never the return string alone.

### 2.B — Cleanup + fix skills (MUTATING, run SEQUENTIALLY, each its own commit)
After the reviewers report, apply fixes. These edit the working tree, so they run one at a time, each committed separately (never smuggle a review fix into an unrelated commit):

5. **Simplify / refactor** — invoke the `simplify` skill (`/simplify`) on the changed files: reuse, simplification, efficiency, and altitude cleanups, applied. Then action the `refactor-cleaner` dead-code findings from 2.A (remove if cheap; park large consolidations in `future.md` with a reason). Commit: `refactor(...): ...`.
6. **Correctness review-and-fix** — invoke the `code-review` skill (`/code-review --fix`) to apply the correctness/cleanup findings the reviewers in 2.A surfaced. Every Blocker and every real-impact Important is fixed; Nits batched into one follow-up commit or deferred with a one-liner. Re-run the relevant tests after. Commit: `fix(...): ...`.
7. **UX simplify** — `ux-simplify` skill (`/ux-simplify`) on the primary page(s) touched. Advisory only (never auto-applies) — surface the top 1–2, park the rest in `future.md`.
8. **Docs sync** — `doc-updater` agent (or `/update-docs` / `/document-feature-module <module>`) so every touched module's docs + Voice Coverage Matrix reflect the change (CLAUDE.md rule #7). Commit: `docs(...): ...`.

### 2.C — Superpowers review loop (the explicit superpowers entwine)
Wrap the whole pass in the superpowers review discipline:
- `superpowers:requesting-code-review` skill to frame what was built and what to scrutinise before merge, and
- `superpowers:receiving-code-review` skill to triage the combined findings from 2.A into fix-now vs defer.
This is the structured "I finished — now prove it's good" loop; it is part of the chain, not optional decoration.

### 2.D — Synthesis gate
Merge all findings into one list, dedupe, and resolve: every Blocker fixed + re-tested, every real-impact Important fixed or explicitly user-deferred, Nits batched/parked. The Phase 7 Automated-Passes table gets one row per pass above with a **cited artefact** (agent id, quoted finding count, or fix commit SHA). **A pass with no cited evidence did not run — and SHIPPABLE is forbidden until it does.**

---

## Phase 3 — Smoke Verification (mandatory if any code changed)

Trust nothing. Prove it.

- **Edge functions touched** — `mcp__supabase__get_logs(service='edge-function')` filtered by function name in the last hour. Confirm a 200 from your deploy. If zero invocations yet: "deployed but not smoked — manual hit before declaring done."
- **Sentry** — `mcp__69d67893-09e0-414d-9e82-7bb4e7df8ce4__search_issues` with `component:<function-name>` or browser filters touching new files. Any unresolved error introduced by this session = **blocker**.
- **Preview server** — if a UI page was touched: `mcp__Claude_Preview__preview_start`, take one screenshot of the primary surface, grab `preview_console_logs` and `preview_network` for the last minute. Zero unexpected console errors is the bar.
- **Playwright e2e** — if the session shipped a user-facing flow: invoke `everything-claude-code:e2e` to generate / run the journey, or via `mcp__playwright__browser_*` for ad-hoc verification. If e2e already exists, run it.

---

## Phase 4 — Capture Lessons (mandatory if any user correction landed)

Per the user's standing rule: after any correction, append to `tasks/lessons.md` with the pattern + preventive rule. Skip only if zero corrections happened.

```md
## <date> — <short name>
**Pattern:** <what Claude did wrong>
**Rule:** <what to do instead>
**Example:** <file / command / one-liner>
```

Commit the lesson separately.

---

## Phase 5 — Pre-Merge Final Verdict

Compute the verdict from Phases 0–4. The verdict drives Phase 6.

- **SHIPPABLE** — every section in Phase 1 is `✅` or has a user-approved `Deferred` entry. Phase 2 passes **actually ran this session** (cited evidence) with zero unaddressed Blockers/Importants. Phase 3 smoke checks all confirm intended behaviour. Phase 4 lessons captured. The Phase 1.11 isolation verdict is **ISOLATED**. **→ proceed to auto-merge (Phase 6) unless `--no-merge` was passed.** If the isolation verdict is **ENTANGLED**, the verdict is still SHIPPABLE for the *work* but auto-merge is OFF — escalate the merge-scope decision per 1.11 instead of merging.
- **SHIPPABLE WITH CAVEATS** — non-blocking gaps exist but were user-approved. **→ proceed to auto-merge, surface caveats in final report.**
- **NOT SHIPPABLE** — at least one Blocker remains. **→ STOP. Do not merge. Report the blocker and where the fix lives. Wait for explicit user direction.**

---

## Phase 6 — Auto-Merge Protocol (NEW — runs when verdict ≠ NOT SHIPPABLE and `--no-merge` not passed)

You merge the open PRs from this session yourself. The user does not click anything.

### 6.0 Hard precondition — the Phase 1.11 isolation verdict MUST be ISOLATED
Do not enter Phase 6 if the branch is **ENTANGLED** (foreign commits, no dedicated PR, or concurrent pushes). Merging an integration/shared branch to main as a side effect of landing your fix ships other people's unreviewed work to production and may race active commits. ENTANGLED → you already escalated the scope decision in 1.11; obey the user's choice (open-PR-and-hold / track-owner-merges / explicit merge-the-whole-track). Auto-merge only proceeds for genuinely isolated work.

### 6.1 Identify in-scope PRs
- `gh pr list --state open --search "author:@me head:<this-session's-branch>"` OR (when working without a head filter) cross-reference `git log <session-start-sha>..HEAD` with `gh pr list --state open --json number,headRefName`. Only merge PRs **whose branch matches a commit you authored in this session** AND whose commit set is yours alone (re-check authorship per 1.11). Never merge unrelated open PRs, and never merge a PR that also carries other authors' commits without explicit user go-ahead.

### 6.2 For each in-scope PR — per-PR protocol
1. **Final CI confirmation:** `gh pr checks <N>`. Required checks (`quality`, `test (1)`, `test (2)`, `test (3)`, any other required gates) must show `pass`. Non-required (`notify`, `Supabase Preview` when skipped) are fine.
2. **Conflict check via merge-tree** (NOT `gh pr view --json mergeable` — that flag lags):
   ```bash
   git merge-tree $(git merge-base origin/main origin/<branch>) origin/main origin/<branch> | grep -E 'CONFLICT|<<<<<<<' | head -3
   ```
   Empty output = clean. Hits = STOP, escalate to the user; do not force-resolve.
3. **Squash merge:**
   ```bash
   gh pr merge <N> --squash --repo <owner>/<repo>
   ```
4. **Content-proof verification post-merge** (per memory rule — `mergeable` lags, content is truth):
   ```bash
   git fetch && git merge-base --is-ancestor <squash-sha> origin/main && echo IN_MAIN || echo MISSING
   git grep <key-symbol-from-PR-diff> origin/main -- <relevant-file>
   ```
   Both must succeed. If either fails → escalate immediately.

### 6.3 When CI is still pending at audit time
Do not merge with pending checks. Two paths:
- **Inline wait** (preferred when ≤3 min): poll `gh pr checks <N>` every 60s up to 5 polls. If green, merge. If still pending, dispatch a watcher subagent (see 6.4).
- **Watcher subagent** (for longer waits): dispatch ONE tight-scope subagent with this exact shape:
  - Hard cap: 10 polls of 60s each.
  - Incremental `.claude/agent-summary.md` writes after each merge.
  - Pre-baked content-proof commands.
  - Scope-fence: only the in-scope PRs.
  - Anti-watchdog return shape: <200 word summary, never "I'll wait" cliffhangers.

### 6.4 Cross-PR conflict surface during merge wave
If multiple in-scope PRs are merging, merge in **squash-SHA chronological order of original branch creation** (oldest first). After each merge, re-fetch main and re-check merge-tree for the next PR. Per `feedback_subagent_completion_verification.md` multi-PR wave addendum.

### 6.5 Post-merge close-out
- Verify final `gh pr list --state open` shows zero in-scope PRs remaining.
- Trigger fresh runs of any drift-check workflows if their last run was on a stale SHA: `gh workflow run "Migration Drift Check" --ref main`, `gh workflow run "Deploy Migrations" --ref main`, `gh workflow run "Supabase Drift Check" --ref main`. Confirm they go green.
- Append `.claude/agent-summary.md` with section `# /ship-check auto-merge — <date>` containing each merged PR# + squash SHA + content-proof receipts.

---

## Phase 7 — Final Report (exact format)

```markdown
# Ship-Check: <feature or branch>

## Intent
- <5–10 bullets from Phase 0>

## Checklist (evidence in parens)
| Area | Status | Notes |
|------|--------|-------|
| Build, Types, Tests | ✅ / ⚠️ / ❌ | `bun run build` exit 0, `bunx vitest run` X/X pass |
| DB & Migrations | ... | columns queried in `information_schema.columns`; RLS row in `pg_policies` |
| Edge Functions | ... | v<N> deployed, log sample timestamp |
| Security & Privacy | ... | grep hits = 0; advisors delta = 0 |
| Accessibility | ... | |
| UX Failure Paths | ... | auth-race guard verified |
| Dead Code & Simplicity | ... | |
| Docs | ... | |
| Git Hygiene | ... | |
| Cross-PR Interactions | ... | N PRs landed mid-session; M overlap; all resolved |

## Automated Passes (every applicable row MUST have a cited artefact — agent id / quoted finding count / fix SHA)
| Pass | Agent/Skill | Ran (evidence) | Outcome / Commit |
|------|-------------|----------------|------------------|
| code-review (superpowers) | `superpowers:code-reviewer` | <agent id + N findings> | <fix SHA / none> |
| code-review (ecc/lang) | `everything-claude-code:code-reviewer` | <agent id + N findings> | <fix SHA / none> |
| security-review | `everything-claude-code:security-reviewer` | <agent id + verdict> | <fix SHA / none> |
| dead-code/dup analysis | `everything-claude-code:refactor-cleaner` | <agent id + N findings> | applied in refactor SHA |
| simplify | `/simplify` skill | <ran? diff applied> | <refactor SHA / none> |
| code-review apply | `/code-review --fix` | <ran? findings applied> | <fix SHA / none> |
| ux-simplify | `/ux-simplify` | <ran? top issues> | parked in future.md / none |
| voice-coverage-audit | `/voice-coverage-audit <module>` | <ran? matrix refreshed> | <doc SHA / n/a> |
| docs sync | `doc-updater` / `/update-docs` | <ran?> | <docs SHA / n/a> |
| superpowers review loop | `requesting-/receiving-code-review` | <ran?> | triage outcome |

## Smoke
- Edge fn logs: <2xx timestamp or "0 invocations yet">
- Sentry: <open issue count touching session scope>
- Preview: <screenshot + console error count, or "n/a">
- e2e: <pass/fail or "n/a">

## Lessons Captured
- <bullet per entry added to tasks/lessons.md, or "none — no corrections">

## Deferred (user-approved)
- <parked items with a reason each, linked to future.md>

## Verdict
**SHIPPABLE** — evidence above covers every section.

## Merges (Phase 6 — auto-executed)
| PR # | Title | Squash SHA | Content Proof |
|------|-------|------------|---------------|
| <N>  | ...   | <sha>      | <symbol>:<file>:<line-count>  |

Final open PR count (in-scope): **0**.
Drift / Deploy Migrations / Supabase Drift / Sentinel Health: **all GREEN** on `<main HEAD>`.
```

---

## Hard Rules

- **Evidence or `⚠️`.** `✅` requires a cited artefact. Same rule as `superpowers:verification-before-completion`.
- **Never batch-skip a section with "looks fine".** If you did not check, mark `⚠️`.
- **Never invent work.** If the user's intent was narrow, do not expand "while I'm here". Surface in Deferred.
- **Fix > flag.** Cheap & obvious (unused import, missing `aria-label`, missing `extractErrorMessage`): just fix. Flag is for design calls.
- **One concern per commit.** Review fixes, refactors, doc updates — separate commits.
- **Auto-merge is default — but ONLY for ISOLATED work.** When verdict ≠ NOT SHIPPABLE, `--no-merge` not passed, AND the Phase 1.11 isolation verdict is ISOLATED, you merge yourself. Verify via `git merge-base --is-ancestor` + content proof, NEVER `gh pr view --json mergeable`. If ENTANGLED (multi-author / no dedicated PR / concurrent pushes), auto-merge is OFF — escalate the scope decision, never squash a shared track to main as a side effect.
- **Review passes are not skippable by assertion.** Code-review and security-review must actually execute this session with quoted findings before SHIPPABLE. "Tests pass + I read the diff" is not a review.
- **Run the WHOLE review chain, every time.** The parallel reviewer fan-out (superpowers:code-reviewer + ecc code/security reviewers + refactor-cleaner) AND the mutating cleanup skills (/simplify, /code-review --fix, /ux-simplify, voice-coverage-audit, doc-updater), wrapped in the superpowers requesting-/receiving-code-review loop. Running this chain is a primary reason the command exists — never collapse it into a self-review.
- **Always compute branch topology before merging.** `git rev-list --count origin/main..HEAD` + authorship + PR existence + live-push check. Never assume "merge" means your fix alone.
- **Stop at NOT SHIPPABLE.** Never merge with an unresolved Blocker, regardless of CI colour.
- **Senior-dev mode** (per user's standing preference): apply obvious best-practice fixes without asking. Only ask on real design calls.
- **Scope = THIS session.** Phase 1.10 and Phase 6 explicitly fence against unrelated open PRs / branches / prior work.
- **Anti-watchdog hygiene** on every dispatched subagent: tight brief, hard poll caps, incremental summary writes, pre-baked diagnosis when known.

---

## When to Invoke

Run `/ship-check` at the end of any session where a feature was built or materially changed — **before** declaring the work "done". It is the last thing you do, not the first.

For long sessions (multi-phase feature build), also invoke `everything-claude-code:strategic-compact` mid-way so Phase 0 still has session intent in cache.

For audit-only mode (no merge): `/ship-check --no-merge`.

For overriding the auto-inferred scope: `/ship-check --scope="PR #309 + cross-PR interactions"`.
