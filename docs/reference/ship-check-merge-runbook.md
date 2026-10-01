# /ship-check — Phase 6 merge runbook 6.1–6.6 (reference)

Read by `commands/ship-check.md` Phase 6 before the first merge. Mandatory every time Phase 6 runs.

**6.1 In-scope PRs:** `gh pr list --state open --search "author:@me head:<branch>"`, or cross-reference `git log <session-start-sha>..HEAD` with `gh pr list --state open --json number,headRefName`. Merge only PRs whose commits are yours alone and from this session (re-check authorship). Unrelated PRs, or PRs carrying others' commits, need an explicit user go-ahead.

**6.2 Per PR:**
1. `gh pr checks <N>`: required checks (`quality`, `test (1..3)`, other required gates) show `pass`. Non-required ones (`notify`, a skipped `Supabase Preview`) are fine.
2. Conflicts: `git merge-tree --write-tree --name-only origin/main origin/<branch>; echo "exit: $?"`. Exit 0 = clean. Exit 1 = conflict → STOP and escalate; don't force-resolve. **Never** use `gh pr view --json mergeable` (it lags) or a `<<<<<<<` grep on the legacy 3-arg merge-tree (blind to modify/delete). (lessons § 6.2)
3. `gh pr merge <N> --squash --repo <owner>/<repo>`
4. Content proof. Both must pass, or escalate:
   ```bash
   git fetch && git merge-base --is-ancestor <squash-sha> origin/main && echo IN_MAIN || echo MISSING
   git grep <key-symbol-from-PR-diff> origin/main -- <relevant-file>
   ```

**6.3 CI pending:** never merge on pending. If the wait is ≤3 min, poll `gh pr checks` every 60s, max 5 polls. If longer, dispatch ONE watcher subagent (`model: "sonnet"`): hard cap of 10×60s polls, incremental `.claude/agent-summary.md` writes after each merge, pre-baked content-proof commands, scope-fenced to in-scope PRs, return <200 words, never an "I'll wait" cliffhanger.

**6.4 Merge waves:** merge oldest branch first. After each merge, re-fetch main and re-run merge-tree for the next PR.

**6.5 Close-out:** `gh pr list --state open` shows 0 in-scope PRs. Re-trigger drift workflows whose last run was on a stale SHA (`gh workflow run "Migration Drift Check" --ref main`, `"Deploy Migrations"`, `"Supabase Drift Check"`) and confirm green. Append `# /ship-check auto-merge — <date>` to `.claude/agent-summary.md` with PR#, squash SHA and content-proof receipts.

**6.6 Post-merge deploy proof (per deployable; "merged" ≠ "shipped"):**
- Vercel/Netlify: a deployment tied to the merge SHA + `curl` prod for the actual changed behaviour (not a status page).
- Supabase edge fn: `functions list` version/`updated_at` past the merge + one real smoke request.
- Long-running service (e.g. Netcup): the repo runbook, restart proven on new code (boot log/version), one REAL request through the live path (not a demo against a stub).
- Other (Worker/Lambda/mobile): the deploy manifest (`wrangler deployments list`, `aws lambda get-function`, EAS build id) matches the SHA, then exercise it once.
