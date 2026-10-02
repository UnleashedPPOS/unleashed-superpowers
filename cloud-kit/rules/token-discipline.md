# Token discipline — no polling chatter (HARD RULE, 2026-10-01)

Why: every turn re-reads the whole chat (~230k tokens in long sessions); idle >cache TTL = full
rewrite at 2x. A "still working" turn costs 25-35k (500k after cache expiry). Overnight polling in
two giant Opus orchestrators burned ~25% of the weekly limit in 16h.

## Waiting / polling
- **Never** send "still waiting / checking again" turns. Nothing changed → end the turn silently.
- **One consolidated check** for ALL lanes/PRs/routines in a single command, at most every 30+ min.
- Prefer ONE blocking watcher → chat wakes once. For PRs/CI use
  `~/.claude/bin/lanes-wait OWNER/REPO#N OWNER/REPO#N ...` in the background (exits 0 on any
  change, 2 timeout, 1 if gh fails); `--once` = one consolidated status snapshot;
  `--comments '^R[0-9]+ (review|follow-up)'` also wakes on review verdicts; missing PR numbers are skipped.
- Waiting >5 min: end the turn, write state to a handoff file, resume via notification or
  ScheduleWakeup (1200s+). Never sleep inside a big session. Don't re-poll CI/routines by hand.
- Everything blocked on CI or the founder's click → say "waiting on X" ONCE, then back off to
  every few hours (or stop entirely and let the founder ping). No-change check-ins are pure burn.
- A watcher must also exit on **stall** (no PR/CI/issue change in ~60 min), not only on success.
  2026-10-01: a "wait for 8 done-issues" watcher sat 9h while the CI box was frozen.
- Cloud lanes never wait on self-hosted CI (sessions end first). They make PRs ready; a local
  merger merges (`~/.claude/bin/pr-auto-merge`). >10 PRs queued → one merge-train PR per repo
  labelled `ci:priority` immediately, not after hours (see memory `merge-train-playbook`).

## Session size
- **Token discipline is about HOW work is done, never WHETHER.** Context size is never a reason to
  defer, descope, skip or label work "follow-up". Big session → delegate to Sonnet sub-agents or hand off
  the complete remaining list as mandatory work. Never tell the founder you're "keeping the session small".
- Unattended work runs to completion: keep going through auto-compactions until the whole job is
  done. Never stop, pause or ask the founder to open a new chat just because context is big.
- Start the NEXT job in a fresh chat (handoff + paste-in starter) once the current one is done or
  blocked only on the founder. A hook reminds after 4 auto-compactions (then every 2) — it is a
  "fresh chat for the next job" reminder, never a stop signal.
- autoCompactWindow is 250000 (was 200000) — don't raise it further. A repo's committed
  `.claude/settings.json` overrides the user value, so never commit a different number there.

## Model + delegation
- Opus only for design/review/hard debugging. Mechanical work (CI watching, merging, ssh/gh
  plumbing, status) → Sonnet (pass `model:`). An Opus orchestrator should delegate, not execute.
- Fork (`subagent_type: "fork"`) vs fresh sub-agent: fork = copy of this chat, reuses its cache, but runs on MY model
  (Opus) and carries the whole context. Fork only when the task needs what this chat already knows AND context is
  under ~60k. Otherwise a fresh Sonnet sub-agent with a self-contained brief (cheaper per token, small context).
- Sub-agents default to Sonnet (`CLAUDE_CODE_SUBAGENT_MODEL`). Pass `model: "opus"` only for
  safety-critical/independent review. Each sub-agent costs ~40k just to start — don't spawn one for
  a lookup you can do in 1-3 calls. They return a SHORT result (<300 words).
- **Cloud first.** Anything that can run in the cloud runs in the cloud: spawn it as a one-shot cloud
  routine (RemoteTrigger, Sonnet), not a local Agent. `Agent isolation:"remote"` silently runs LOCALLY
  in the desktop app — it is not a cloud agent. Stay local only when the job needs this Mac: vault
  secrets, DB/deploy CLIs, ssh to the build box, the built-in browser, or a repo with no remote.
  At most ONE local sub-agent at a time (8GB laptop); long-running local-only jobs go on the server.

## Disk hygiene (laptop is 228GB and keeps filling)
- Remove your worktree the moment its PR merges (`git worktree remove <path>`); never leave one behind.
- No `bun install` / `uv sync` / `npm i` in a throwaway worktree unless the task needs to run code there.
- Don't clone a repo locally just to read it — use `gh api` / `gh repo view` or a cloud routine.
- A daily maintenance job (`~/bin/disk-maintenance.sh`) prunes caches, merged worktrees, pushed
  branches, idle deps, and offloads repos idle 30+ days (`restore <repo>` brings one back).

## Routines (RemoteTrigger)
- `list` returns 300KB+ and `list_runs`/`get_run_log` ~10KB each — never poll them in a loop. Use `get`
  on one id, or save to a file and summarise with python. Don't create "re-check CI" routines per PR;
  one watcher for all. Give routines an explicit Sonnet model unless they review safety-critical work.
- Booked routines are prompt SNAPSHOTS: when /red-team, /ship-check or a rule changes, re-template the
  pending ones (2026-10-01: 4 rebuilt by hand). Do it in a small session — each update echoes ~9k tokens.

## Keep context lean
- Don't Read whole large files — use ranges/grep; don't dump big command output (filter with
  head/jq/ctx_execute and print only the answer). Never re-read a file already in context.
- Batch independent tool calls in one turn. Don't re-verify just-edited files.
- Don't load connectors/plugins you don't need (Vercel 244 tools + Higgsfield are off by default;
  use the vercel/gh/supabase CLIs). Keep MEMORY.md + rules short; push detail into memory files.
