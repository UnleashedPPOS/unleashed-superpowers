---
description: End-of-session production audit + auto-merge. Intent vs Definition of Done, full reviewer chain, branch-isolation gate, auto-merge when SHIPPABLE + ISOLATED, then /red-team. Flags --no-merge, --no-red-team, --scope=, --task.
---

# /ship-check: Evidence-Based Production Audit + Auto-Merge

Senior engineer signing off before real users touch it: no gaps, silent bugs, security holes or half-done work. Find what's missing and finish it. On a clean verdict, **merge it yourself**.

Scope: `$ARGUMENTS`, else `git log origin/main..HEAD` + this conversation's intent. **Only THIS session's work.**

Flags:
- `--no-merge`: full audit, stop before Phase 6. Also skips 6.7.
- `--no-red-team`: run 0–6 but skip 6.7. Rare: only for a trivial, zero-risk change, and only when the user explicitly waives it.
- `--scope=<freeform>`: overrides the inferred intent, e.g. `--scope="PR #309 + cross-PR interactions"`.
- `--task`: per-task gate along the way (see Fast Path). Skips 0, 2.B–2.D, 3–6.7. Never authorizes a merge.

**Lessons:** `~/Developer/unleashed-superpowers/docs/reference/ship-check-lessons.md` (incidents, rationale, governing memory files). Read the cited `§` only when a phase points there or a rule's intent is unclear.

## Definition of Done (Phase 5's bar)
1 **Built**: matches the Phase 0 intent, nothing silently descoped · 2 **Correct**: toolchain green (1.1) + both review lenses + security actually ran, 0 open Blockers (2) · 3 **Safe**: no secrets, no new security/RLS/CORS gap, no untested destructive action (1.2–1.4) · 4 **Usable**: a11y, error/empty/loading states, no dead ends (1.5–1.6) · 5 **Clean**: no dead code, docs updated, history matches intent (1.7–1.9) · 6 **Merged**: ISOLATED PR, CI green, squash, content proof (1.11, 6) · 7 **Deployed**: live artifact = merge SHA (6.6) · 8 **Exercised** once on the real path after deploy (3, 6.6) · 9 **Survived falsification** (6.7).
Any unmet item is a ⚠️/❌ you fix, or a user-approved Deferred entry. Never a silent gap.

## Prime Directive: Evidence Before Assertions
No ✅ without proof: command output, a file quote, a DB result, a deploy ID or a SHA. Didn't run it → ⚠️. A ⚠️ is acceptable; a false ✅ is a firing offence. Cite the proving artefact on one line before each checkmark.

## Model routing + token discipline
- **Reviewer/analysis subagents: pass `model: "sonnet"`** on every `Agent` call (fan-out, report-mode refactor-cleaner, watchers, doc-updater).
- **Opus only for:** (a) your own synthesis and final verdict (2.D, Phase 5, Phase 7), which stay in the top session; and (b) the security reviewer, which gets `model: "opus"` when the diff touches auth, payments/money, secrets, consent/compliance gates, RLS or other safety-critical paths. Otherwise sonnet.
- **Every reviewer brief ends with:** "Return ≤300 words: findings ranked Blocker/Important/Nit, each with `file:line` evidence. No preamble, no restating the diff."
- Brief with a file list + diff or a plan's `file:line-range`, never a whole plan. Large output (git log, build/test, repo-wide grep) goes through `ctx_execute`.

## Fast Path: `--task`
(1) 1.1 on the repo toolchain, with commands + exit codes cited. (2) ONE reviewer (`model: "sonnet"`, ≤300 words) on this task's diff, findings quoted. (3) Secrets grep on new files = 0. (4) Pass/fail in 3–4 lines. No Intent Summary, merge or Phase 7.

---

## Phase 0: Reconstruct THIS session's intent
1. `tasks/todo.md` if present (primary source).
2. `git log origin/main..HEAD --oneline` (or vs the base branch). Each subject is a claimed deliverable.
3. Re-read the user's early messages: what was asked for, what was deferred or parked.
4. `tasks/lessons.md`: in-session corrections are now rules.
5. `.claude/agent-summary.md` if subagents wrote receipts.
6. After a compaction/resume boundary: if the user says something is done and your context disagrees, check ground truth (`gh pr list --search`, `git log --all`, live DB/deploy) before redoing it or disputing them. (lessons § Phase 0)

Output an **Intent Summary** (5–10 bullets: features, schema changes, new files, deprecations, parked items). Anything ambiguous → ask for one-line confirmation **before any audit runs**. Don't guess. **Scope fence:** ignore other people's PRs and unrelated branches. Mid-session merges into main belong in 1.10.

## Phase 1: Ship-readiness checklist
Walk every section. Fix each ⚠️/❌ now unless the user deferred it in Phase 0. Cite evidence.

### 1.1 Build, types, tests (`superpowers:verification-before-completion`)
**Detect the toolchain first:** `Makefile` target → lockfile (`bun.lockb` bun · `pnpm-lock.yaml` pnpm · `package-lock.json`/`yarn.lock` npm/yarn · `uv.lock` uv · bare `pyproject.toml` pytest via the repo venv, never system python) → `package.json` script names.
- [ ] Build exits 0. Cite the command + what told you to use it.
- [ ] Lint: 0 **new** errors in session files (pre-existing ones listed separately).
- [ ] Affected tests pass **on the repo's configured runner** (lessons § 1.1 runner).
- [ ] Typecheck clean. Name pre-existing generated-file corruption separately.
- [ ] No `any`/untyped escape hatch where a concrete type fits.
- [ ] Generated type/schema files reflect this session's schema changes (regenerate, or check `information_schema.columns`).
- [ ] Each new pure function/invariant has ≥1 assertion. Destructive UI/CLI actions have a confirmation step or a test.
- [ ] **No self-contradicting tests/evals/fixtures:** grep the corpus for a near-identical input with a different expected outcome for each case you added, and resolve any hit.

### 1.2–1.8 Conditional checklists → **read `~/Developer/unleashed-superpowers/docs/reference/ship-check-checklists.md`** for each section the diff triggers (unsure → read it)
1.2 DB/migrations (live SELECT proof, RLS + policy, `schema_migrations` drift, advisories) · 1.3 edge/serverless (deployed ≥ last commit, auth, server-side validation, delimited LLM input, checked writes) · 1.4 security/privacy beyond the secrets grep (no PII in logs, sanitizer, CORS, LLM PII; auto-invoke `everything-claude-code:security-review`) · 1.5 a11y (any UI) · 1.6 UX failure paths + no auth-race bounces (any UI/mutation/routing) · 1.7 dead code (any code) · 1.8 docs (any code). Every section gets a Phase 7 row; untriggered = `n/a — <why>`.
- [ ] **Always, every diff:** `git grep -rnE "(sk_|AKIA|AIza|eyJ[A-Za-z0-9_-]{20,})"` on new files → 0 · no `user_id`/email/phone/query keys in toasts or logs · user-facing errors go through the repo's sanitizer, never raw `String(error)`/stack.
- [ ] **1.2 drift check is MANDATORY** whenever this session changed the DB by any route (migration file, ORM/codegen schema, SQL run out-of-band, RLS/policy/function edit).

### 1.9 Git hygiene
- [ ] One concern per commit · nothing from this session left uncommitted · branch pushed · no secrets, `.env` or large binaries (`git diff --stat origin/main..HEAD`).
- [ ] **Committed-files-vs-intent:** run `git show --name-only <sha>` on each of YOUR commits and check every file against the Phase 0 intent (plus `git log --name-only origin/main..HEAD` for unrelated working-tree changes). Strays: split them out if unmerged, flag loudly if merged.

### 1.10 Cross-PR interactions
- [ ] `git log <session-start-sha>..origin/main --oneline`. For each PR that landed mid-session: does it touch your files, imports or schema? On overlap, re-run the relevant Phase 1 subset on the rebased state.
- [ ] Use the **three-dot** diff (`origin/main...HEAD`) or rebase first. Two-dot on a stale base shows phantom deletions (lessons § 1.10).

### 1.11 Branch topology & merge-isolation gate (always, before 5/6)
- [ ] `git rev-list --count origin/main..HEAD` vs your commit count · authorship (`git log origin/main..HEAD --format='%an %s'`) · PR exists (`gh pr list --head <branch> --state open`; no PR + many commits = integration branch) · CI `on:` triggers (PRs excluded → empty `gh pr checks` = "never ran", say so) · live concurrency (foreign commits after session start, `.git/index.lock`, a commit on top of your push).
- [ ] **ISOLATED** (your commits only / a dedicated PR) → Phase 6 may proceed. **ENTANGLED** (foreign commits, no dedicated PR, or live pushes) → auto-merge **forbidden**. `AskUserQuestion`: merge the whole track / open PR + hold / leave it to the track owner. Never guess. A PR opened for CI visibility is fine (lessons § 1.11).

---

## Phase 2: Review passes (MANDATORY, not skippable by assertion)
A pass counts **only** if its agent ran **in this conversation** and you quote its findings (a run earlier in this conversation counts if you cite its agent id + findings). "Tests pass + I eyeballed the diff" is not a review. **SHIPPABLE is forbidden** until every applicable pass has run (lessons § 2). Reviewers are read-only and run in parallel. Fix skills mutate the tree, so they run sequentially, one commit each.

### 2.A Reviewer fan-out (read-only, parallel: one message, multiple `Agent` calls, from THIS top-level session)
**Never** delegate review+fix+merge to a background orchestrator that spawns its own reviewers (it parks forever), and never spawn a second agent to "resume" one. Delegate the reviewing, never the acting (lessons § 2.A). Every call: `model: "sonnet"` (security: see Model routing), a scope-fenced brief, and the ≤300-word return clause. Quote findings back after each returns. Run **all that apply**:
1. **Code review, two independent lenses:** `superpowers:code-reviewer` AND `everything-claude-code:code-reviewer` (or a language reviewer for a single-language diff: `python-reviewer`, `go-reviewer`). Diff/merge their findings.
2. **Security:** `everything-claude-code:security-reviewer`. MANDATORY if the session touched auth, input, endpoints, secrets, payments, edge functions or LLM prompts. Blockers get fixed before merge.
3. **Dead code / duplication:** `everything-claude-code:refactor-cleaner` in REPORT mode (identify only).
4. **Repo-specific coverage audit** (e.g. `voice-coverage-audit`), scoped to the touched module, if the repo defines one.

Anti-watchdog: **≤3 reviewers per wave** (4+ trips the watchdog), or two waves. ≤2 background subagents.

### 2.B Cleanup + fix (mutating, sequential, separate commits; never smuggle a fix into an unrelated commit)
5. **Simplify:** the `/simplify` skill on changed files, then action refactor-cleaner's findings (remove if cheap; park large consolidations in the repo's tracking doc, e.g. `future.md`, with a reason). Commit `refactor(...)`.
6. **Correctness fix:** `/code-review --fix` to apply the 2.A findings. Fix every Blocker + real-impact Important. Nits: one batched commit or deferred with a one-liner. Re-run tests. Commit `fix(...)`.
7. **UX friction:** the repo's UX-simplify skill (advisory) on the primary pages touched, or a manual pass that surfaces the top 1–2 issues. Park the rest in the tracking doc.
8. **Docs sync:** `doc-updater` agent (`model: "sonnet"`), `/update-docs` or `/document-feature-module <module>`, covering module docs + any tracking doc (e.g. the Voice Coverage Matrix). Commit `docs(...)`.

### 2.C Superpowers review loop (part of the chain, not decoration)
`superpowers:requesting-code-review` frames what was built and what to scrutinise. `superpowers:receiving-code-review` triages the combined 2.A findings into fix-now vs defer.

### 2.D Synthesis gate (Opus, top session)
Merge + dedupe all findings. Every Blocker is fixed + re-tested. Every real-impact Important is fixed or user-deferred. Nits are batched or parked. Phase 7's Automated Passes table gets one row per pass with a **cited artefact** (agent id, quoted finding count or fix SHA). No evidence = didn't run = no SHIPPABLE.

---

## Phase 3: Smoke verification (mandatory if any code changed)
- **Edge/serverless touched:** `supabase functions logs <name>` (via `ctx_execute`) or `wrangler tail`/`vercel logs`/CloudWatch, last hour. Confirm a 2xx from your deploy. 0 invocations → "deployed, not smoked": hit it before declaring done.
- **Error tracker** (Sentry etc.; find its MCP via ToolSearch), filtered to session files. Any unresolved error this session introduced = **blocker**.
- **Preview** (UI touched): `preview_start`, screenshot the primary surface, console + network for the last minute: 0 unexpected console errors.
- **e2e** (user-facing flow shipped): `everything-claude-code:e2e` or `mcp__playwright__browser_*`. Run existing e2e.

## Phase 4: Capture lessons (mandatory if any user correction landed)
Append to `tasks/lessons.md`, commit separately:
```md
## <date> — <short name>
**Pattern:** <what Claude did wrong>
**Rule:** <what to do instead>
**Example:** <file / command / one-liner>
```

## Phase 5: Pre-merge verdict
- **SHIPPABLE**: all Phase 1 ✅ or user-Deferred; Phase 2 passes **actually ran** (cited), 0 unaddressed Blockers/Importants; Phase 3 confirms behaviour; Phase 4 done. 1.11 = ISOLATED → Phase 6 (unless `--no-merge`). If ENTANGLED, the work is SHIPPABLE but auto-merge is OFF; escalate per 1.11.
- **SHIPPABLE WITH CAVEATS**: non-blocking gaps the user approved → merge and surface the caveats.
- **NOT SHIPPABLE**: any Blocker remains → STOP. Don't merge. Report the blocker and where its fix lives, then wait for the user.

## Phase 6: Auto-merge (verdict ≠ NOT SHIPPABLE, no `--no-merge`)
**6.0 Precondition:** 1.11 = ISOLATED. If ENTANGLED, follow the user's 1.11 choice. **6.1–6.6 → read `~/Developer/unleashed-superpowers/docs/reference/ship-check-merge-runbook.md` before the first merge (mandatory).** Summary: merge only your-commits-only session PRs · required checks `pass`, never pending (≤5×60s polls, else ONE sonnet watcher, 10-poll cap) · conflicts via `merge-tree --write-tree` exit code, never `mergeable` · `--squash` · content proof (`merge-base --is-ancestor` + `git grep` symbol on origin/main) · oldest first, re-merge-tree after each · close-out: 0 in-scope open PRs, drift workflows green, receipts to `.claude/agent-summary.md` · 6.6 deploy proof per deployable tied to the merge SHA + one real request.

## Phase 6.7: Adversarial verification (`/red-team`, auto-chained)
Runs on SHIPPABLE / WITH CAVEATS unless `--no-merge` or `--no-red-team`. Auditing your own output is not independent verification.
- Invoke `red-team` **scoped to this session's work** (same fence as 0/1.10), not as a fresh repo-wide audit.
- Triage 🔴 CRACKED per red-team's dispositions (MINE-TO-FIX / OWNED-ELSEWHERE / GENUINE-EXTERNAL). MINE-TO-FIX gets fixed + re-proven + re-merged before this verdict stands.
- Fold its Claim Ledger verdict into the Phase 7 report, not a separate one. `/red-team` stays independently invocable.

---

## Phase 7: Final report (exact format, mandatory read)
**Read `~/Developer/unleashed-superpowers/docs/reference/ship-check-report-template.md` and fill it exactly.** Sections: Intent · Checklist table (one row per 1.1–1.10 area, evidence in parens) · Automated Passes table (one row per 2.A–2.C pass incl. model, each with a cited agent id / finding count / fix SHA) · Smoke · Lessons Captured · Deferred (user-approved) · Verdict · Merges (PR#, squash SHA, content proof) · Post-Merge Deploy Proof (6.6) · Adversarial Verification (6.7 counts + verdict) · final in-scope open PR count = 0 · drift/health workflows GREEN on `<main HEAD>`.

---

## Hard rules (each is enforced in the phase cited)
Evidence or ⚠️; never batch-skip with "looks fine" (Prime) · never invent work, extras go to Deferred · fix > flag for cheap/obvious items, ask only on design calls (senior-dev) · one concern per commit · whole review chain every time, never self-review (2) · reviewers on sonnet with ≤300-word returns, Opus for synthesis/verdict + safety-critical security (Model routing) · fan out from the top session, never a self-spawning orchestrator (2.A) · never nest `Agent` `isolation:"worktree"` from a non-git cwd: `git worktree add` yourself and pass the path · topology before merge, auto-merge only if ISOLATED (1.11) · empty checks ≠ green (1.11) · merge-tree exit code + ancestor + content grep, never `mergeable` (6.2) · stop at NOT SHIPPABLE whatever colour CI is (5) · scope = THIS session · merged ≠ shipped (6.6) · anti-watchdog on every subagent: tight brief, hard poll caps, incremental summary writes, pre-baked diagnosis.

## When to invoke
At the end of any session that built or materially changed a feature, **before** declaring it done. Long sessions: `everything-claude-code:strategic-compact` mid-way so Phase 0 keeps the intent. `--task` is a mid-session checkpoint, never a substitute.
