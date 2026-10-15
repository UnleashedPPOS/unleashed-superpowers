---
description: Harvest learnings from this chat (or pasted notes), check what's already covered, and implement the rest
argument-hint: "[optional: pasted learnings / file path / focus area]"
---

# /learnings — harvest, dedupe, implement

Source: $ARGUMENTS if given (pasted text or a file path), otherwise THIS chat — including
corrections from the founder, things that went wrong, workarounds, and anything that wasted tokens or time.

Cloud session (no `~/.claude/projects/.../memory`, nothing persists in the VM): route rules/commands/hooks to a PR on UnleashedPPOS/unleashed-superpowers (`cloud-kit/`), repo conventions to that repo's CLAUDE.md, and memory-type facts into the PR body for the Mac to file.

## 1. Extract (be strict)
List candidate lessons, one line each. Keep only those that will change future behaviour:
- founder corrections / preferences ("don't do X", "always Y") → highest value
- process mistakes and what should have happened instead
- non-obvious technical gotchas (root cause + fix), infra/topology facts not in the repo
- recurring manual steps that a script, hook or command could do
Drop: one-off outages, trivial fixes, things already in code/git history, restated generic advice.

## 2. Check what already exists (cheap — grep, don't read everything)
For each lesson, grep 2-3 keywords across:
`~/.claude/rules/ ~/.claude/CLAUDE.md ~/.claude/projects/-Users-elliotkelly-Developer/memory/ ~/.claude/commands/ ~/.claude/hooks/`
plus the current repo's CLAUDE.md/AGENTS.md. Read only the matching lines/sections.
Classify each as: **covered** (cite file) · **partly covered** (extend that file) · **new**.

## 3. Route each new/partial lesson to the right home
| Kind | Home |
|---|---|
| applies to every session, behavioural | edit an existing `~/.claude/rules/*.md` (prefer extending over new files; keep rules terse) |
| fact / gotcha / project state | memory file (frontmatter format) + one-line pointer in MEMORY.md; update an existing note rather than duplicating |
| repo-specific convention | that repo's CLAUDE.md (commit it per git-workflow rules) |
| automatable check or repeated step | hook or script in `~/.claude/hooks` / `~/.claude/bin` — build + test it if <30 min, else propose a session |
| larger change (refactor a command, fix a codebase) | `start_session` proposal with a self-contained prompt |

## 4. Implement
Do it — don't ask per item (founder intent is explicit when they run this). Exceptions that still need
a yes: deleting/retiring memories (back up first), changing settings.json permissions, anything outward-facing.
Keep rules files short: they load into every session. Converge duplicates instead of adding.

## 5. Report (short, plain English)
- **Already covered** — lesson → where
- **Added now** — lesson → file (link)
- **Spawned / needs you** — chips created, anything only the founder can do
- One line of opinion: which lessons matter most and anything you disagree with.
