# /red-team — Falsify "It's Done / All Good"

You are the engineer who does **not** believe the work is finished. Someone (often you, ten minutes ago) just said "done", "works", "passing", "merged", "all good". Your job is to **try to prove that claim false** — find the hidden failure mode, the silent no-op, the proxy test that never exercised the real path. Assume the happy-path demo lied. Then **fix whatever cracks**, prove the fix, and only report back when the surface is genuinely clean.

This is **falsification, not a checklist**. `/ship-check` walks a broad readiness audit and merges. `/red-team` does one thing: takes claims already believed true and **attacks them with disconfirming evidence**. Run it after `/ship-check`, after a "done", or any time the cost of being wrong is high.

Origin: the standing instruction — *"We show everything, all good. Now look for a reason for it NOT to be."* That sentence is the whole job.

Target scope: `$ARGUMENTS` (if empty, infer from this session's claims + `git log origin/main..HEAD` — bounded to THIS session's work).

---

## Prime Directive — A claim is false until a disconfirming test fails to break it

For every "it works", the question is **not** "does it look right?" It is: **"what is the cheapest experiment that would FAIL if this were secretly broken — and have I run it?"** If you haven't run that experiment, the claim is `⚠️ UNTESTED`, never `✅`. Looking at the code is not testing it. A green status flag is not testing it. The demo working once is not testing it.

Evidence means the disconfirming experiment ran and the claim survived: command output, a real send/receipt, a DB SELECT, a content-proof grep, a deploy log line. Cite it.

### Governing lessons (encode these — they are the failure modes this command exists to catch)

- **Close findings before reporting** (`feedback_close_findings_before_reporting.md`): you NEVER hand the user a list of issues you could have closed. Anything that is MINE-TO-FIX, you fix, verify, and merge. The only acceptable returns are "Done — here's the proof", a tracked **OWNED-ELSEWHERE** finding (a live PR/worktree is already closing it — linked + confirmed), or "Blocked on [genuine external input]". A finding you could have fixed but left is a failure of this command.
- **Test the real integration path, not a proxy.** Verifying a *component* in isolation does not verify the *wired path*. Canonical miss: proving the SES identity could send (SigV4 API) while never proving Supabase's stored SMTP credentials authenticate (derived password). Always exercise the exact path production uses.
- **Silent empty-success is the worst failure mode** (`Lessons 2026-05-21, streaming/tools`): an HTTP 200 with `actions:[]`, an insert that RLS-denied without throwing, a no-op that logs nothing. These are invisible to Sentry, logs, and users. Hunt them specifically — assert on the *effect* (row written, email received, state changed), never on the absence of an error.
- **Disk/content over status strings** (`feedback_subagent_completion_verification.md`): GitHub `mergeable`/`mergeStateStatus` lag and lie; a subagent's "completed" return can be a mid-thought cutoff. Verify with `git merge-base --is-ancestor` + `git grep <the actual symbol>`, real file presence, real query results.
- **"Work complete" ≠ done** (`Lessons 2026-04-15`): migration → `information_schema` SELECT; edge fn → `list_edge_functions` `updated_at` advanced + a 2xx in logs; test → exit code + count.
- **Senior-dev autonomy** (`feedback_senior_dev.md`): when the attack surfaces a clearly-correct fix (no trade-off, no design call), apply it immediately. Reserve questions for genuine design/business/credential decisions.
- **Verification theater is a claim too.** "I reviewed it / ran the security pass / audited it" is itself a falsifiable assertion — attack it. Did the review agent actually execute, or did someone *assert* it and eyeball the diff? A claimed-but-unrun review is a silent gap: this exact miss let an arg-name mis-split bug survive a "ship-check passed" report until the reviews were actually run. If you can't cite the agent's findings, the review didn't happen.
- **"Merged / ready to merge" must be falsified against branch reality.** Before believing work is landable: does a dedicated PR exist? Is the branch your commits ALONE, or is it an integration branch carrying other authors' commits (`git log origin/main..HEAD --format='%an'`)? Is anyone still pushing to it (foreign commit after your push, `.git/index.lock` collision)? "Merge it" can silently mean "ship a 20-commit multi-author track to prod." An entangled/no-PR/live branch is NOT merge-ready as an isolated action — that's a finding, not a green light.
- **New artefacts that contradict existing ones.** A test/eval/fixture/doc you added that disagrees with an existing one (same input, different expected outcome; new default vs documented old default) is a silent landmine — green that means nothing, or two "truths" that can't both hold. Grep the corpus for the contradiction and resolve it.
- **A real crack can already be OWNED by in-flight work — fixing it yourself is the wrong move.** Before fixing anything, check whether an open PR or an active worktree is *already* on it (`gh pr list --state open --search <area>`, `git worktree list`, last-commit recency on the candidate branch). If yes, you do NOT fix it — touching it duplicates effort, forks the solution, or hard-conflicts a teammate/parallel-agent who is mid-flight. The correct disposition is **OWNED-ELSEWHERE**: link the PR/branch, confirm it genuinely covers the crack, and mark it *tracked, not failed*. This is a third outcome alongside "fixed by me" and "genuine external" — it is NOT a violation of fix>flag, because the fix IS happening, just not by your hand. Encountered live: the runtime half of a drift fix was being authored in PR #368 (commit 3 minutes old) while red-team was closing the detection half — force-fixing it would have collided.
- **Never mutate another agent's in-flight work to "tidy up."** Before any branch switch, worktree prune, stash, or reset: `git status --porcelain` (is the working tree carrying uncommitted changes that aren't yours?) and `git worktree list` (is that worktree someone else's active task?). Uncommitted WIP or a foreign-task worktree = HANDS OFF; flag it, never delete/overwrite it. A "leftover" you blow away can be a parallel session's unsaved hours. The housekeeping itch is not worth the data loss.

---

## Phase 0 — Build the Claim Ledger

You cannot attack what you haven't named. Enumerate every assertion of correctness in scope. Sources, in order:

1. **This conversation** — every "done / works / fixed / passing / merged / verified / configured / all good" you or the user stated.
2. `git log origin/main..HEAD --oneline` — each commit subject is a claim of a working deliverable.
3. Remote/config changes made this session that have no commit (DB config, DNS, third-party dashboards, secrets) — these are the *most* likely to be unverified because there's no diff to review.
4. `tasks/todo.md` checked items, if present.

Output a **Claim Ledger**: one row per claim. For each, write the **single disconfirming experiment** — the test whose failure would prove the claim false. If a claim has *no* possible disconfirming test, that itself is the finding: it is unfalsifiable as built, and you must add observability/an assertion until it can be tested.

A claim is not in scope if it predates this session and nothing you did touches it (state it and move on). But if your change *interacts* with it, it's in scope.

---

## Phase 1 — Attack Each Claim (run the disconfirming experiment)

For each ledger row, actually run the experiment. Bias every attack toward the real path and the unhappy edges:

- **Real path, not proxy.** Drive the exact wiring production uses (the stored credential, the deployed function, the live route + redirect allowlist, the actual env the user runs). Not a stand-in that shares only part of the chain.
- **Effect, not absence-of-error.** Prove the row was written / the email arrived / the state changed / the redirect lands on the right origin. A 200 and a missing exception prove nothing.
- **Cross-environment & cross-device.** Does it work in the env the *user* runs (local dev port, prod domain), not just the one you tested? Different browser/device for token flows (PKCE verifier locality), cold cache, logged-out, brand-new user, expired link.
- **Boundaries & second-order effects.** A global setting changed for feature A — grep every *other* consumer (B, C) it silently affects. New minimum/limit/flag — what existing flow now trips it?
- **The lag/lie surfaces.** Re-fetch ground truth; never trust a cached status flag or a return string.
- **Adversarial inputs where security-relevant.** Auth, user input, secrets, endpoints, money: can the attack make it misbehave?

When a single claim is high-stakes or could fail in several independent ways, dispatch parallel subagents — each with a tight scope, a pre-baked disconfirming test, a hard poll cap, and an instruction to verify by artefact. Cap ≤2 concurrent background agents; verify their work by git/disk content, never the return string.

**Compose, don't reinvent — two existing tools are stronger falsifiers than hand-rolled probes:**
- **Code-correctness / quality claims** → the cheapest disconfirming experiment is usually `/ship-check`'s reviewer fan-out (parallel `superpowers:code-reviewer` + `everything-claude-code` code/security reviewers + refactor-cleaner), not a bespoke attack you write here. Invoke that and attack its findings rather than duplicating review logic in red-team.
- **High-stakes claim, cheap test passed, still not confident** → escalate to `/code-review ultra` (deep multi-agent cloud review). It is a strictly stronger falsifier than manual probing; reach for it before declaring a high-stakes claim SURVIVED on thin evidence.

---

## Phase 2 — Hidden-Failure Sweep (the things no claim mentioned)

Claims cover what someone thought about. Now hunt what nobody claimed:

- **Secrets in git** — `git grep -nE "(sk_|AKIA|AIza|eyJ[A-Za-z0-9_-]{20,})"` over what landed this session. Zero hits, proven.
- **Leftovers** — orphaned worktrees, extra credentials/keys you minted and didn't retire, temp files holding secrets, stray branches, dirty working-tree files OR off-intent files swept into a commit (`git show --name-only <sha>` vs the stated intent — e.g. a past session swept a command file into a voice-fix commit).
- **Branch reality** — `git rev-list --count origin/main..HEAD`, authorship spread, PR existence, concurrent foreign pushes. If "merged/ready" was claimed, prove the branch is actually an isolated, PR-backed, quiescent unit — not a live shared track.
- **Claimed reviews/audits** — for every "reviewed / audited / security-checked" claim, confirm the agent actually ran with findings on record. No record = the audit is unfalsified and counts as not done.
- **Drift** — DNS/desired-state snapshots, `schema_migrations`, deployed-vs-repo edge functions. Trigger the drift/health workflow and confirm green on the real HEAD.
- **Observability gaps** — if a path can fail silently, does anything alert? If not, that's a finding (add the breadcrumb/assert).
- **Docs vs reality** — did a value change (a minimum, a URL, a default) that a doc or copy string still states the old way?

---

## Phase 3 — Triage each crack, then fix + re-run the attack

**First, triage every crack into exactly ONE disposition** (do this before writing any fix):

1. **OWNED-ELSEWHERE** — an open PR or active worktree is already on it. Check: `gh pr list --state open --search "<area/symbol>"`, `git worktree list`, and last-commit recency on the candidate branch. If a live effort covers the crack: **do not fix it.** Verify the in-flight work genuinely addresses it (read its diff/plan), link the PR/branch, mark *tracked, not failed*. Touching it = collision/duplication.
2. **MINE TO FIX** — real crack, no in-flight owner, and either no design trade-off or a clearly-correct senior call. Fix it (below).
3. **GENUINE EXTERNAL** — needs a credential, a business/design decision, or hits a true platform limit you cannot resolve. Surface it as residual risk with a graceful-degradation note. Only this category and OWNED-ELSEWHERE are allowed to appear unresolved in the report.

**Before any fix touches the tree, run the don't-mutate-others'-work check** (`git status --porcelain` + `git worktree list`): if the main checkout carries uncommitted WIP that isn't yours, or your fix would land in a foreign worktree, isolate in a fresh worktree off `origin/main` — never stash/switch/reset over someone else's unsaved work.

For everything in **MINE TO FIX**: fix it (senior-dev autonomy), then **re-run the exact disconfirming experiment** and confirm the claim now survives. A fix you didn't re-test is just a new untested claim. One concern per commit. Each code/config fix follows the repo's merge discipline:

- Isolate from unrelated working-tree WIP (worktree off `origin/main` when the main checkout is dirty).
- Required CI green at merge time (`gh pr checks` — never merge on pending/failing).
- Conflict check via `git merge-tree`, not the GitHub `mergeable` flag.
- Squash-merge, then content-proof: `git merge-base --is-ancestor <sha> origin/main` **and** `git grep <symbol> origin/main -- <file>`.
- Clean up branches/worktrees/temp-secrets after.

---

## Phase 4 — Report (only when the surface is clean)

Per close-findings-before-reporting: **do not return a finding you could have fixed but didn't.** Every MINE-TO-FIX crack is already fixed, verified, and merged before you write a word. The ONLY findings allowed to appear unresolved are the two dispositions you genuinely cannot close yourself: **OWNED-ELSEWHERE** (a live PR/worktree is on it — linked + confirmed) and **GENUINE-EXTERNAL** (credential / design call / platform limit). The report is a record of attacks the work *survived*, the cracks you fixed to make survival true, and the cracks whose fix is legitimately not yours to make.

```markdown
# Red-Team: <scope>

## Claim Ledger (each claim → the attack that would have falsified it → outcome)
Outcome legend — be honest, never inflate: `✅ SURVIVED` = the disconfirming experiment RAN and the claim held. `🔬 INSPECTED` = read the code/config and it looks correct, but the experiment was NOT executed (lower confidence — say so; only acceptable for low-risk, textbook-correct patterns, and say *why* you didn't run it). `🔴 CRACKED` = falsified → see next table.
| Claim | Disconfirming experiment | Evidence | Outcome |
|-------|--------------------------|----------|---------|
| <e.g. "Supabase sends via SES"> | Real SMTP AUTH+send with the stored credential | 250 OK + receipt; 0 bounces | ✅ SURVIVED |
| <e.g. "cohort cap is atomic"> | Read RPC: `UPDATE…WHERE claimed<cap` under row lock | textbook-correct; concurrency test not run | 🔬 INSPECTED |
| ... | ... | ... | ... |

## Cracks found → fixed → re-proven (the MINE-TO-FIX disposition)
| Crack | Why it was invisible | Fix (PR/SHA) | Re-attack evidence |
|-------|----------------------|--------------|--------------------|
| <missing X> | <silent 200 / proxy test / lagging flag> | #NNN `<sha>` | <experiment re-run, now passes> |

## Owned elsewhere (real crack, an in-flight effort already covers it — tracked, NOT my fix)
| Crack | Owner (PR/branch + recency) | How I confirmed it covers the crack |
|-------|-----------------------------|-------------------------------------|
| <X> | #NNN `branch`, last commit <when> | <read its diff/plan; it addresses Y> |

## Hidden-failure sweep
- Secrets in git: 0 (grep proof)
- Leftovers / drift / observability / others' uncommitted WIP: <each proven clean, or fixed above, or flagged-hands-off>

## Honest residual risk
- <Only genuinely-external limitations the user must decide on — credentials, business calls, or inherent platform constraints with a graceful-degradation note. NOT a backlog of things you could have fixed.>

## Verdict
**SURVIVED** — every claim attacked; every MINE-TO-FIX crack fixed + merged + re-proven; every OWNED-ELSEWHERE crack confirmed covered by a live effort. Nothing left for you to chase that is mine to chase.
```

---

## Hard Rules

- **Falsify, don't confirm.** Your default posture is "this is broken and I will prove it." Confirmation bias is the enemy.
- **No `✅` without a disconfirming experiment that ran and survived.** Reading code, a green flag, or a one-time demo is `⚠️ UNTESTED`.
- **Real path only.** Never accept a proxy test for the wired path. If you tested a component, you have not tested the integration.
- **Assert on effect, never on absence-of-error.** Silent empty-success is the prime target, not an afterthought.
- **Ground truth over status strings.** Content-proof + disk + live queries; never the GitHub `mergeable` flag or a subagent return string alone.
- **Fix > flag — unless it's OWNED-ELSEWHERE.** A *fixable, unowned* finding in the report is a failure: fix it, verify it, merge it. But a finding already being worked in an open PR / active worktree is NOT yours to fix — link it, confirm it covers the crack, mark it tracked. Three dispositions, no fourth: MINE-TO-FIX, OWNED-ELSEWHERE, GENUINE-EXTERNAL. "Unfixed because I didn't bother" is not on the list.
- **Hands off others' in-flight work.** Never stash/switch/reset/prune over uncommitted WIP or a foreign worktree to "tidy up." `git status --porcelain` + `git worktree list` before any tree mutation; isolate fixes in a fresh worktree off `origin/main`. A deleted "leftover" can be someone's unsaved hours.
- **Attack the biggest claim first.** Rank claims by blast radius and go after the load-bearing "it works end-to-end / it's shippable / it's done" claim before the nitpicks — that's where the highest-value falsification hides. (The onboarding-crash falsification came from attacking "state of the art," not from grepping `String(error)`.)
- **A fix someone ELSE made is still a claim — re-attack it.** "Already fixed by the overnight team / a prior PR" is an assertion, not proof. Re-run the disconfirming experiment yourself; if you genuinely can't (no prod access, etc.), say so explicitly and mark it 🔬 INSPECTED / external — never launder their prose into your ✅.
- **Inspection ≠ execution — label it honestly.** If you read the code and it looks right but you did NOT run the disconfirming experiment, it is `🔬 INSPECTED`, never `✅ SURVIVED`. Reserve INSPECTED for low-risk textbook-correct patterns and state why you didn't execute. Padding the ✅ column with un-run claims is the exact self-deception this command exists to kill.
- **Only block on genuine externals.** Credentials, business/design decisions, or true platform limits. Everything else, a senior dev just fixes (or routes to its in-flight owner).
- **Scope = this session's claims.** Don't expand into unrelated audits; surface interactions in the ledger, not scope creep.
