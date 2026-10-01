# /red-team: Falsify "It's Done / All Good"

Someone (often you) just said "done / works / merged / all good". **Try to prove it false**: hidden failure modes, silent no-ops, proxy tests that never touched the real path. Then **fix what cracks**, prove the fix, and report only when clean.

Falsification, not a checklist. `/ship-check` (the broad audit + merge) auto-chains this as Phase 6.7. It also runs standalone on any high-cost claim.

Scope: `$ARGUMENTS`, else this session's claims + `git log origin/main..HEAD`. **Only THIS session's work.**

**Lessons:** `~/Developer/unleashed-superpowers/docs/reference/red-team-lessons.md` = the incident behind each `§`; read only for rationale.

## Prime Directive: a claim is false until a disconfirming test fails to break it
Ask: **"what is the cheapest experiment that would FAIL if this were secretly broken, and have I run it?"** Not run → `⚠️ UNTESTED`. Reading code, a green flag or a one-off demo is not a test. Cite the evidence (output, a real receipt, a SELECT, a content grep, a deploy log line).

### Governing rules (the failure modes this command exists to catch)
- **Close findings before reporting.** Fix, verify and merge everything MINE-TO-FIX. The only allowed returns: "Done + proof", OWNED-ELSEWHERE (linked + confirmed), "Blocked on genuine external input".
- **Real integration path, not a proxy.** Proving a component works doesn't prove the wired path (§ SES vs SMTP).
- **Silent empty-success is the worst failure.** 200 + `actions:[]`, an RLS-denied insert that didn't throw, a no-op that logs nothing. Assert on the *effect*, never on the absence of an error (§ silent empty-success).
- **Disk/content over status strings** (`mergeable` lags; a subagent's "completed" can be a cutoff): `merge-base --is-ancestor` + `git grep <symbol>`. "Done" proof: migration → `information_schema` SELECT (`db query --linked`); edge fn → `updated_at` advanced + a 2xx; test → exit code + count (§ proof).
- **Senior-dev autonomy:** apply clearly-correct fixes now. Ask only on design, business or credential calls.
- **Verification theater is a claim too.** For "reviewed / audited / security-checked": did the agent actually run? No citable findings → it didn't happen (§ arg-name mis-split).
- **Falsify "merged / ready to merge" against branch reality:** a dedicated PR? your commits alone (`git log origin/main..HEAD --format='%an'`)? anyone still pushing? An entangled, no-PR or live branch is a finding, not a green light.
- **New artefacts that contradict existing ones** (same input with a different expected outcome; a new default vs the documented one): grep the corpus and resolve.
- **A crack may already be OWNED by in-flight work.** Before fixing: `gh pr list --state open --search <area>`, `git worktree list`, last-commit recency. If it's covered → OWNED-ELSEWHERE: link it, confirm it covers the crack, mark it tracked (§ PR #368).
- **Never mutate another agent's in-flight work.** Run `git status --porcelain` + `git worktree list` before any switch, prune, stash or reset. Foreign WIP or a foreign worktree = hands off, flag it.
- **Never delegate the finish to a self-spawning orchestrator.** Fan reviewers out from the top session running `/red-team`, read their findings yourself, and do triage/fix/merge yourself. Never spawn a "resume" agent (kill the parked duplicate). Never nest `Agent` `isolation:"worktree"` from a non-git cwd; run `git worktree add` and pass the path (§ orchestrator).

## Model routing + token discipline
- **Subagents: pass `model: "sonnet"`** (parallel attack probes, reviewer fan-out). Use **`model: "opus"`** only for a safety-critical independent attack (auth, money, secrets, consent/compliance gates). Your own synthesis, triage and verdict stay in the top session (Opus).
- **Every subagent brief ends with:** "Return ≤300 words: claim, experiment run, raw evidence, verdict. No preamble."
- Brief with a file list or a plan's `file:line-range`, never a whole plan. Large output (git log, gh pr list, build/test, repo-wide grep, DB result sets) goes through `ctx_execute`.

## Phase 0: Build the Claim Ledger
Sources: (1) every "done / works / fixed / passing / merged / verified / configured / all good" in this conversation; (2) `git log origin/main..HEAD --oneline`, where each subject is a claim; (3) remote/config changes with no commit (DB config, DNS, dashboards, secrets). These are the *most* likely to be unverified. (4) Checked items in `tasks/todo.md`.

One row per claim, each with its **single disconfirming experiment**. A claim with no possible disconfirming test is itself a finding: add observability or an assertion until it can be tested. Older claims your work doesn't touch are out of scope (say so).

## Phase 1: Attack each claim (run the experiment)
- **Real path:** the stored credential, the deployed function, the live route + redirect allowlist, the env the user actually runs.
- **Effect:** the row was written, the email arrived, the state changed, the redirect lands on the right origin.
- **Cross-env/device:** the user's env (local port, prod domain), another browser/device for token flows (PKCE verifier locality), cold cache, logged out, brand-new user, expired link.
- **Second-order effects:** a global setting changed for A → grep consumers B and C. A new limit or flag → which existing flow now trips it?
- **Adversarial inputs** where it matters for security: auth, input, secrets, endpoints, money.
- **Any customer-facing URL about to be sent** (magic link, invite, receipt): curl-verify it first (`curl -sL <url> | grep -o '<title>[^<]*</title>'`) to confirm the right host, app and tenant (§ wrong host).
- **Live DB experiments run in a rollback wrapper** via `supabase db query --linked` through `ctx_execute` (bare CLI is hook-blocked in Bash): `BEGIN; SET LOCAL ROLE authenticated; SET LOCAL request.jwt.claims = '...'; SELECT public.some_rpc(...); ROLLBACK;`. Skip the wrapper only when proving a real write IS the point, and then clean up and verify with a fresh count.

High-stakes or multi-mode claims: parallel subagents (`model: "sonnet"`, ≤300 words), each with a tight scope, a pre-baked disconfirming test and a hard poll cap. ≤2 background at once. Verify by git/disk content, not the return string.

**Compose, don't reinvent:** for code-correctness/quality claims → `/ship-check`'s reviewer fan-out (superpowers + ecc code/security reviewers + refactor-cleaner, on sonnet), then attack its findings. High-stakes claim, cheap test passed, still not confident → `/code-review ultra` before calling it SURVIVED.

## Phase 2: Hidden-failure sweep (what nobody claimed)
- **Secrets:** `git grep -nE "(sk_|AKIA|AIza|eyJ[A-Za-z0-9_-]{20,})"` over what landed this session → 0, proven.
- **Leftovers:** orphaned worktrees, minted-but-unretired keys, temp files holding secrets, stray branches, dirty files, off-intent files swept into a commit (`git show --name-only <sha>` vs intent).
- **Branch reality:** `git rev-list --count origin/main..HEAD`, author spread, PR exists, concurrent foreign pushes. If "merged/ready" was claimed, prove it's isolated, PR-backed and quiescent.
- **Claimed reviews/audits:** an agent actually ran with findings on record, or it counts as not done.
- **Drift:** DNS/desired-state, `schema_migrations`, deployed-vs-repo edge fns. Trigger the drift/health workflow and confirm green on the real HEAD.
- **Observability gaps:** a path that can fail silently with no alert is a finding (add the breadcrumb or assert).
- **Docs vs reality:** a changed value (minimum, URL, default) still stated the old way in docs or copy.
- **"Not writable through X / admin-only" comments are claims.** Grep every RPC, edge fn and form that could write the field (§ stale comment).
- **Provider-pending states** (template `PENDING`, domain verifying, webhook unsubscribed) are a status to query, not a 200 to trust (§ provider-pending).

## Phase 3: Triage each crack, then fix + re-attack
Exactly ONE disposition per crack, decided before any fix:
1. **OWNED-ELSEWHERE**: an open PR or active worktree covers it (`gh pr list --state open --search "<area/symbol>"`, `git worktree list`, recency). Read its diff/plan to confirm, link it, mark *tracked, not failed*. Don't touch it.
2. **MINE TO FIX**: a real crack, no in-flight owner, no trade-off (or a clearly-correct senior call). Fix it.
3. **GENUINE EXTERNAL**: needs a credential, a business/design decision, or hits a platform limit. Report it as residual risk with a graceful-degradation note.

Before touching the tree: `git status --porcelain` + `git worktree list`. Foreign WIP → fresh worktree off `origin/main`. Never stash, switch or reset over it.

For MINE-TO-FIX: fix it, then **re-run the exact disconfirming experiment**. An untested fix is a new untested claim. One concern per commit, under the repo's merge discipline: isolate from unrelated WIP · required CI green (`gh pr checks`, never on pending) · conflicts via `git merge-tree`, not `mergeable` · squash-merge, then content proof (`git merge-base --is-ancestor <sha> origin/main` **and** `git grep <symbol> origin/main -- <file>`) · clean up branches, worktrees and temp secrets.

## Phase 4: Report (only when the surface is clean)
Every MINE-TO-FIX crack is already fixed, verified and merged. Only OWNED-ELSEWHERE and GENUINE-EXTERNAL may appear unresolved.

**Read `~/Developer/unleashed-superpowers/docs/reference/red-team-report-template.md` and fill it exactly (mandatory).** Sections: Claim Ledger (Claim · Disconfirming experiment · Evidence · Outcome; legend `✅ SURVIVED` = experiment ran and held, `🔬 INSPECTED` = read only + why not run, `🔴 CRACKED`) · Cracks → fixed → re-proven · Owned elsewhere (owner + how confirmed) · Hidden-failure sweep (secrets 0 + grep proof) · Honest residual risk (genuine externals only, not a backlog) · Verdict.

## Hard rules
- **Falsify, don't confirm:** no ✅ without an experiment that ran. Three dispositions, no fourth ("didn't bother" isn't one).
- **Attack the biggest claim first.** Rank by blast radius; the load-bearing "works end-to-end / shippable / done" claim comes before nitpicks (§ onboarding crash).
- **Someone else's fix is still a claim.** Re-run the experiment yourself. If you can't, mark it 🔬 INSPECTED/external. Never launder their prose into your ✅.
- **Inspection ≠ execution.** Read-but-not-run = `🔬 INSPECTED`, never `✅`. INSPECTED becomes SURVIVED only by citing a NEW experiment, never a re-read (§ uniqueness constraint).
- **Scope = this session's claims.** Interactions go in the ledger, not scope creep.
