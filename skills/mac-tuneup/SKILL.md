---
name: mac-tuneup
description: "Diagnoses and fixes a slow, hot or full MacBook Air (8 GB RAM, 228 GB disk): memory pressure, swap, CPU hogs, orphaned tool processes, failing background jobs, storage hogs and reclaimable caches. Use when the founder says the laptop is slow, laggy, freezing, out of storage or memory, or asks to optimise / tune up / clean up the Mac, its storage or performance."
---

# Mac tune-up

Read-only first, then fix only what the numbers point at. Never guess.
The script lives in this skill's `scripts/` folder (`~/.claude/skills/mac-tuneup` is a symlink to `unleashed-superpowers/skills/mac-tuneup`).

## Quick start

```bash
python3 ~/.claude/skills/mac-tuneup/scripts/diagnose.py          # full (~1 min, includes update check)
python3 ~/.claude/skills/mac-tuneup/scripts/diagnose.py --fast   # skip folder sizes + update check
```

Healthy floor: memory free >= 30%, swap < 4 GB, disk free > 25 GB, 0 orphans.

## Workflow

1. Run `diagnose.py` (use `--fast` if the complaint is only "slow").
2. Slow / laggy → work down the memory and CPU sections:
   - 0 orphans expected; if any, check `~/Library/Logs/memory-guard.log` and that `com.elliotkelly.memory-guard` is loaded (`launchctl list | grep memory-guard`).
   - A process pinned > 50% CPU for minutes: identify it (`ps -p <pid> -o args=`), find its owner (LaunchAgent, repo, app) and fix the cause (loop, retry storm, stuck child), not just kill it.
   - Claude Code sessions > 3 or Chrome very large → tell the founder which to close; never quit their apps.
   - Failing background jobs: check the job's log before acting. See the known-OK list in REFERENCE.md.
3. Full disk → work down "Biggest folders":
   - `~/bin/disk-maintenance.sh report` for code (worktrees, node_modules, idle repos); `--dry-run` before a real run.
   - Clear the "safe" caches yourself (never `~/Library/Caches` as a whole). Move anything else to the Trash (never `rm -rf` user data) and say how much the Trash holds, since space only comes back once the founder empties it.
   - Anything marked KEEP or "ask" in the script: ask first.
4. Re-run `diagnose.py --fast` and report before/after numbers.
5. Update the laptop status page (Artifact `8tXBQHWEkfeNMcjwPLPuYr`, read it first) with the end state.

## Rules

- Founder does: emptying the Trash, sudo commands, System Settings changes, uninstalling apps. Give them the exact command or settings path.
- Never touch Docker, the Hermes/Atlas bridge, trading (ump) jobs or memory jobs without asking.
- Stay inside the existing tools; don't add new LaunchAgents unless the cause needs one.

## Reference

Everything learned so far (what each job does, what's safe, past fixes, settings already applied): [REFERENCE.md](REFERENCE.md).
