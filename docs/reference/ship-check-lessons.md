# /ship-check — lessons & live examples (reference)

Read on demand only. `commands/ship-check.md` points at the section a phase needs. The rules are in the command; this file holds the *why* and the incidents behind them.

## Memory files that govern ship-check
- `feedback_subagent_completion_verification.md`: a return string is not proof of done. Check git log, `.claude/agent-summary.md` on disk and content proof. In multi-PR merge waves the GitHub `mergeable` flag LAGS, so verify with `git merge-base --is-ancestor` + content proofs. It also has the anti-watchdog limits (≤3 reviewers per wave, ≤2 background agents).
- `feedback_merge_with_failing_checks.md`: never defer failing or pending checks. Required CI must be green at merge time.
- `feedback_senior_dev.md`: apply obvious best-practice fixes without asking. Ask only on real design choices.
- `feedback-background-agents-park-on-phantom-monitors.md`: never hand review-fix-merge to an orchestrator that spawns its own agents. It parks forever (Phase 2.A).
- `merge-tree-modify-delete-blindspot.md`: a marker grep on merge-tree misses modify/delete conflicts. Trust the exit code (Phase 6.2).
- `two-dot-diff-stale-base-false-alarm.md`: a two-dot diff on a stale base shows phantom deletions. Use three-dot, or rebase first (Phase 1.10).
- `feedback-verify-git-truth-after-compaction.md`: after a compaction boundary, check ground truth before disputing a user's "already done" claim (Phase 0).
- `feedback-absolute-completion-no-demo.md`: "done" means deployed and exercised live once. Built-but-unwired is not done (Phase 6.6).

## Phase 0: compaction drops whole segments
Compaction can silently drop a whole completed segment of a session. If the user says something is already done and your reconstructed context disagrees, the context is the suspect. Check `gh pr list --search`, `git log --all` and live DB/deploy state before you redo landed work or tell the user they're wrong.

## 1.1: wrong test runner = false green
Running `bun test` against a `vitest` repo silently skips files and changes assertion semantics, which gives a false green. That is one instance of the rule. The rule itself: always use the runner the repo is configured for.

## 1.1: self-contradicting test corpus
If two near-identical inputs in a corpus expect different outcomes, at least one is wrong, or the routing rule is undefined. That corpus gives flaky, meaningless green.

## 1.2: migration drift
A common cause of a `schema_migrations` row going missing: the migration was applied with `db query --file` instead of `db push`. Fix with `supabase migration repair --status applied <ts>`. "Ran the CLI" is not evidence. Only a live SELECT is.

## 1.6: PR #309 auth race
A gated route redirected before its auth `loading` state resolved, so signed-in users got bounced. The guard: every gated caller checks loading/pending BEFORE it redirects.

## 1.10: two-dot vs three-dot diff
On a stale-base branch, `git diff origin/main..HEAD` shows every commit main gained (and you lack) as a deletion. A 5-file change can look like it deletes hundreds of unrelated lines, and a reviewer burns a finding on the false alarm. `git diff origin/main...HEAD` (three dots) or a rebase avoids this.

## 1.11: entangled branches
The worst blind spot: treating "merge it" as trivial when the branch is a many-commit, multi-author shared track with no PR. Squashing it to main as a side effect of your fix ships other people's unreviewed work to prod, and can race commits that are still landing. CI that triggers only `on: push: branches: [main]` makes `gh pr checks` legitimately empty. That means "CI never ran", not "green".

## 2.A: self-spawning orchestrator parks (live incident)
Handing "review + fix + merge" to one background orchestrator that spawns its own reviewer agents → it parks on "I'll act when their notifications land". A nudge only gets "standing by". Spawning a second agent to "resume" it duplicates work and can race a live merge. Completions from nested agents DO reach the top session, so read their findings and act yourself. Delegate the reviewing, never the acting.

## 2: why review is not skippable by assertion
Skipping the fan-out and self-asserting "looks good" (tests pass + eyeballed diff) once let a real bug through a "passed" audit: an arg-name mis-split. It was only caught when the reviewers actually ran.

## 6.2: merge-tree marker grep is blind
The legacy 3-arg `git merge-tree | grep '<<<<<<<'` pattern reports "clean" on a modify/delete conflict (one branch deletes a file the other modifies), because no markers are written. Use `git merge-tree --write-tree --name-only` and read the exit code.

## 6.6: merged ≠ shipped
A status page and a working page are not the same claim. A demo script hitting a stub is not proof that a long-running service works. Without a deploy-proof row, "merged" only means "the PR closed".

## Worktree isolation
Never nest an `Agent` call with `isolation: "worktree"` from a non-git working directory. The flag can't resolve an ambiguous cwd. Create the worktree yourself (`git worktree add`) and give the agent that path.
