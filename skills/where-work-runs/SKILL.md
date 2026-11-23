---
name: where-work-runs
description: "Where each kind of work runs (cloud sandbox, Netcup server, laptop), what to do when one is at its limit, CI waiting and merge trains, routines (RemoteTrigger) and disk hygiene. Use before heavy work (test suites, installs, builds, Docker, deno), when waiting on CI or PR checks, when scheduling or re-templating routines, when the laptop or server is slow or full, or when the words Netcup, cloud routine, RemoteTrigger, lanes-wait, merge train, load, swap or disk space come up. SKIP for a quick edit or lookup."
---

# Where work runs

**Announce at start:** "I'm using the where-work-runs skill to place this work."

## Thesis
Three places, each with hard limits measured 2026-11-12 (memory `reference-where-work-runs`). Put work where it fits, check the gauge once before heavy work, and never fix overload by deleting things that serve users.

## When this fires
- Before a test suite, install, build, Docker build or deno test.
- Waiting on CI, merging a queue, or scheduling a routine.
- A machine looks slow, full or rate-limited.

## Mandatory checklist

### Pass 1: place the work
1. **Cloud sandbox** (per run: 4 vCPU, 15 GB RAM, 30 GB disk, Postgres 16, Redis, Playwright Chromium, sudo, apt). Unit tests, typecheck, lint, web builds, e2e against a local server, review. unleashedos there: install 4s, typecheck 33s, lint 15s, 5,293 unit tests 3m19s, build 22s. Cannot: Docker, deno, supabase/vercel/aws CLIs, vault secrets, ssh to Netcup, or reach Groq, OpenRouter, Expo, Apple, Google, YouTube. Start Postgres as a non-root user.
2. **Netcup** (4 vCPU, 7.8 GB RAM, swap in use, load above core count). Always-on services, Docker builds, deno tests, deploys only. CI finishes ~12 jobs an hour, one at a time; PR checks wait 2h+. Never add test load, never raise CI parallelism. Its `/tmp` is 3.9 GB of RAM: build in `/opt/ci-workdirs` or `/var/tmp`; `/usr/local/sbin/tmp-hygiene.sh` runs hourly.
3. **Laptop.** Vault secrets, deploy CLIs, the built-in browser, phone builds. No test suites or installs while more than 3 chats are open.
4. Cloud first: anything that can run in the cloud runs as a one-shot cloud routine with an explicit model (`Agent isolation:"remote"` silently runs LOCALLY).

### Pass 2: check the gauge once (never a loop)
1. Laptop: `memory_pressure | tail -1; sysctl vm.swapusage; uptime; df -h / | tail -1`.
2. Server: `ssh netcup-render 'uptime; free -m | sed -n 2p; df -h /tmp / | tail -2'`.
3. Cloud has no gauge: it is full when a run 429s, times out or the probe fails.

### Pass 3: act on limits (founder 2026-11-14)
1. **Laptop over** (free memory under 30%, swap over 4 GB, load over 8, disk under 25 GB, or more than 3 chats): no local sub-agent, install or suite; move work to the cloud; vault/deploy work runs alone. Run `/mac-tuneup`, name chats to close, never quit the founder's apps. Disk under 25 GB: stop builds and downloads.
2. **Server over** (load above 4, swap over 10 GB, `/tmp` over 80%, ENOSPC): add nothing; Docker builds and deno tests queue; PR checks go through cloud CI. `/tmp` over 80%: run the hygiene script first. Never raise parallelism, restart the runner or cancel queued jobs.
3. **Cloud over** (429, usage limit, timeout, blocked host): run 1-2 at a time. A PR check just waits for the server fallback. Ad hoc runs go to the laptop only if it is under its limits; else queue and say "waiting on cloud" once.
4. **All three full:** production fixes, then merges, then everything else waits. Report once what is parked and why.
5. Never fix overload by deleting volumes, rollback-tagged images or stopped product containers, or by touching Arena.

## Catalogue: CI and merging
- One blocking watcher: `~/.claude/bin/lanes-wait OWNER/REPO#N ...` in the background (exit 0 any change, 2 timeout, 1 gh failed); `--once` = one snapshot; `--comments '^R[0-9]+ (review|follow-up)'` also wakes on review verdicts. It must exit on a ~60 min stall (2026-10-01 one sat 9h on a frozen box).
- One consolidated check for all lanes at most every 30+ min.
- Cloud lanes never wait on self-hosted CI: they make PRs ready and a local merger merges (`~/.claude/bin/pr-auto-merge`). More than 10 PRs queued → one merge-train PR per repo labelled `ci:priority` (memory `merge-train-playbook`).

## Catalogue: briefs (lanes, routines, sub-agents; council audit 2026-11-16)
A brief states the outcome and the bar, not the steps. The agent picks the steps, because a step list goes stale as soon as the code turns out different from what its writer pictured. Use four parts under a four-line Heads-up (skill `heads-up-block`):
```text
Heads-up: missing <...> | could go wrong <...> | already exists <...> | newer or better <...> (`none found` where nothing real).
Goal: <the outcome, in the founder's words, and why it matters>.
Constraints: money <spend cap; OpenRouter only in the OS app>; safety <prod data, merge or not, secrets, destructive git>; model policy <model; sub-agent budget: at most N, Sonnet build, Haiku mechanical, Opus review, never Fable>.
Done when: <the check that proves it: a command and its expected result, an eval score, a PR state, a screenshot>.
Report: <where the result goes (PR body, status page link), under 300 words>. Context: <repo, files, links, what is ruled out>.
```
- Give steps only where the order is itself a constraint (migration before deploy), or for mechanical Haiku jobs, which name the exact files and change.
- If you can't write a check that proves success, you don't understand the task well enough to hand it off. Work out the check first.
- Routine prompts use the same shape, and model-guard checks their model and cap. Examples: the migration routine in `llm-provider-chain` and `docs/learning/monthly-prune.md`.

## Catalogue: routines (RemoteTrigger)
- `list` returns 300KB+, `list_runs`/`get_run_log` ~10KB each: never poll in a loop; `get` one id or save to a file and summarise.
- No per-PR "re-check CI" routines; one watcher for all.
- Explicit model per routine: Haiku watchers/status, Sonnet builds, Opus planning, review and safety-critical work; never Fable.
- Booked routines are prompt snapshots: when /red-team, /ship-check or a rule changes, re-template the pending ones in a small session.

## Catalogue: disk hygiene (228 GB laptop)
- Remove your worktree the moment its PR merges (`git worktree remove <path>`).
- No `bun install` / `uv sync` / `npm i` in a throwaway worktree unless the task runs code there.
- Don't clone a repo just to read it (`gh api`, `gh repo view`, a cloud routine). `~/bin/disk-maintenance.sh` runs daily (`restore <repo>` brings an offloaded repo back).

## Anti-pattern flags
- "I'll just run the suite locally" with 4 chats open → cloud.
- "CI looks stuck, push again" → blocked by the correction check; check other PRs' recent results first.
- "Raise the runner's parallelism" → never.

## Integration with other skills
- `mac-tuneup` when the laptop is over its limit.
- `session-handoff` when waiting more than 5 minutes.

## Red flags
| Thought | Reality |
|---|---|
| "The server can take one more job" | It is already over its core count; add nothing. |
| "I'll poll the routine list" | 300KB per call. One `get` or one watcher. |
| "Delete old images to free space" | Rollback images serve users. Run hygiene scripts instead. |

## Reference
- Memory `reference-where-work-runs`, `merge-train-playbook`.
