# Token discipline (HARD RULE; condensed 2026-10-17)

Why: every turn re-reads the whole chat, so cost ~ turns x context size. Week of 2026-10-14: 93% of usage was cache read/write on fat contexts, 81% Opus, 41% sub-agents (opus-thinker 24%); typed output only ~5%. Levers: fewer turns, smaller context, cheaper model. Idle > cache TTL = full rewrite at 2x.

## Tool-call loops (biggest lever; each serial call re-reads the full context)
- Batch: independent reads/greps/commands go in ONE message (parallel tool calls) or one `ctx_batch_execute` / one script.
- Read a file region once, in a generous chunk (or `tilth_read` with `sections`/`paths`, `tilth_search` with several symbols), never many `sed -n` slices. Don't re-grep what you already have.
- Investigating: one broad gather (search + read + git log together), then act; not grep -> read -> grep -> read.
- Several edits to a file go in one message. Don't re-read just-edited files or re-verify what the tool already confirmed.

## Waiting / polling
- Never send "still waiting / checking again" turns. Nothing changed -> end the turn silently.
- One consolidated check for ALL lanes/PRs/routines in a single command, at most every 30+ min. Prefer ONE blocking watcher: `~/.claude/bin/lanes-wait OWNER/REPO#N ...` in the background (exit 0 any change, 2 timeout, 1 gh failed); `--once` = one snapshot; `--comments '^R[0-9]+ (review|follow-up)'` also wakes on review verdicts; missing PRs skipped.
- Waiting > 5 min: end the turn, write state to a handoff file, resume via notification or ScheduleWakeup (1200s+). Never sleep inside a big session; don't re-poll CI/routines by hand.
- Blocked on CI or the founder: say "waiting on X" ONCE, then back off to every few hours or stop.
- A watcher must also exit on stall (no PR/CI/issue change in ~60 min); 2026-10-01 one sat 9h on a frozen CI box.
- Cloud lanes never wait on self-hosted CI; they make PRs ready and a local merger merges (`~/.claude/bin/pr-auto-merge`). >10 PRs queued -> one merge-train PR per repo labelled `ci:priority` immediately (memory `merge-train-playbook`).

## Session size
- Token discipline is HOW work is done, never WHETHER. Context size is never a reason to defer, descope, skip or label work "follow-up". Big session -> delegate to sub-agents or hand off the complete remaining list as mandatory work. Never tell the founder you're "keeping the session small".
- NO cap on concurrent chats (founder 2026-10-17). Keep each chat lean instead.
- Unattended work runs to completion through auto-compactions; never stop or ask for a new chat just because context is big.
- Start the NEXT job in a fresh chat (handoff + paste-in starter) once the current one is done or blocked only on the founder; no 26-43h marathon chats. The hook after 4 auto-compactions (then every 2) is a "fresh chat for the next job" reminder, not a stop signal.
- autoCompactWindow is 250000; don't raise it. A repo's committed `.claude/settings.json` overrides the user value, so never commit a different number.

## Model + delegation
- Main chats default to Sonnet; go Opus only for a genuinely hard stretch, then back. Main chat not on Opus stays orchestrator + straightforward edits; hard thinking goes to `opus-thinker`.
- Use the agent files (`subagent_type` sets model + effort):

  | Agent | Model | Use for |
  |---|---|---|
  | `haiku-worker` | haiku | Clear, fully specified work: sweeps, CI/PR watching, merging, plumbing, renames, boilerplate, exact plan steps, tests to spec, doc fixes, summaries |
  | `sonnet-builder` | sonnet | **Default.** Features, known-cause fixes, refactors, routine reviews, research, write-ups |
  | `opus-thinker` | opus | Genuinely hard/high-stakes only: design, non-obvious root causes, audits/red-team, risky decisions. Never for routine review fan-out |

- Unsure between Sonnet and Opus -> Sonnet; escalate one tier only when the result is weak or the agent says it's unsure. Haiku briefs must be self-contained (files, change, how to verify); vague -> Sonnet. Big jobs: Opus plans, Haiku mechanical slices, Sonnet judgement slices, Opus reviews.
- Effort medium by default; `high` per call only when hard (unclear root cause, security/money/prod data); `xhigh` for the hardest only. Never raise by habit.
- Sub-agents work silently and return ONE short result (<300 words: outcome, evidence, open items). Each costs ~40k to start; don't spawn one for a lookup you can do in 1-3 calls.
- Fork (`subagent_type: "fork"`) runs on my model with this whole context: only when the task needs what this chat knows AND context < ~60k. Otherwise a fresh Haiku/Sonnet agent with a self-contained brief. Ad-hoc agents must pass `model:`.
- Cloud first: anything that can run in the cloud runs as a one-shot cloud routine (RemoteTrigger, model per table), not a local Agent (`Agent isolation:"remote"` silently runs LOCALLY). Stay local only for vault secrets, DB/deploy CLIs, ssh to the build box, the built-in browser, or repos without a remote. At most ONE local sub-agent at a time (8GB laptop).

## Disk hygiene (228GB laptop)
- Remove your worktree the moment its PR merges (`git worktree remove <path>`). No `bun install` / `uv sync` / `npm i` in a throwaway worktree unless the task runs code there. Don't clone a repo just to read it (`gh api` / `gh repo view` / cloud routine). `~/bin/disk-maintenance.sh` runs daily (`restore <repo>` brings back an offloaded repo).

## Routines (RemoteTrigger)
- `list` returns 300KB+, `list_runs`/`get_run_log` ~10KB each: never poll in a loop; use `get` on one id or save to a file and summarise. No per-PR "re-check CI" routines; one watcher for all. Give routines an explicit model (Haiku watchers/status, Sonnet builds, Opus safety-critical review).
- Booked routines are prompt SNAPSHOTS: when /red-team, /ship-check or a rule changes, re-template the pending ones in a small session.

## Keep context lean
- No whole-file Reads of large files (ranges/grep); filter big output (head/jq/ctx_execute) and print only the answer; never re-read a file already in context.
- Don't load connectors/plugins you don't need (Vercel, Everygen, Higgsfield, playwright off by default; use vercel/gh/supabase CLIs). Keep MEMORY.md + rules short; detail goes in memory files.
