---
name: session-handoff
description: Use when the user says "session handoff", "wrap up session", "hand off", "handoff summary", or wants a structured end-of-session summary before clearing context. Produces a handoff (in chat + saved to ~/.claude/handoffs/, with a paste-in starter for the new chat) covering every not-done/deferred item (carried forward, never dropped), decisions, shipped changes, key files, running state, verification steps, lanes in flight, founder-only steps, and open questions so a fresh agent can continue seamlessly.
---

# Session Handoff

Produce a repeatable end-of-session summary so the user can `/clear` and start a fresh agent without losing continuity. The next agent should be able to pick up by reading this summary alone.

This is a **context-handoff artifact**, not a status report. The audience is a future instance of you, not a stakeholder.

## When to invoke

User says: "session handoff", "wrap up session", "hand off", "handoff summary", "let's wrap up", "summarize before I clear", or any near-equivalent. Also invoke proactively if the user says they're about to `/clear` or `/compact` without having run it yet, and when the whole job is done after the `[token-discipline]` compaction reminder has fired. Never hand off mid-job just because context is large.

## How to produce the summary

1. **Review the full conversation**, not just the last few turns. Handoffs miss things when they only summarize recent context.
2. **Pull state from these sources (in order):**
   - Plan files referenced this session (check `~/.claude/plans/` or `<repo>/.claude/plans/` if a plan was mentioned).
   - TodoWrite state — any in-progress or pending tasks.
   - Background processes you started with `run_in_background` — shell IDs are load-bearing for the next agent.
   - **Worktree context** — check your environment context right now: your "Primary working directory" and "Current branch" are in the system prompt. If the working directory contains `.claude/worktrees/` or the branch starts with `claude/`, you are in a worktree. Record the absolute path and branch. Do NOT write "none" without checking this first.
   - Files created or modified this session — you know what you touched; don't grep to re-discover.
   - Memory files written or updated (`~/.claude/projects/<project-slug>/memory/`).
   - Unresolved questions — things you asked the user that never got a clear answer, or things the user asked that got deflected.
   - **Every not-done item** — sweep ALL of these, not just the last task: anything the founder asked for that didn't happen; deferred or parked items (including founder-deferred); unfixed review / red-team findings; ship-check `Remaining` lines and DoD `NOT DONE` / `OWNER` rows; failing or pending CI; unmerged PRs; lanes not yet returned; `tasks/todo.md` unchecked boxes and TodoWrite pending items; and every not-done item in any earlier handoff this session continued from (carry it forward unless it's now done).
3. **Do NOT audit the filesystem.** This is synthesis of what happened in THIS session. No `git log`, no broad `Glob` sweeps. If you didn't touch it this session, it doesn't belong here. Exceptions, always allowed: worktree state from your environment context; this session's ship-check reports (`<repo>/.claude/ship-check-reports/`), `tasks/todo.md`, and the earlier handoff file this session continued from — read them to build the Not done list.
4. **Produce the output in chat AND save it** to `~/.claude/handoffs/<YYYY-MM-DD-HHMM>-<short-slug>.md` (Write tool) so the next chat can read it even if this one is gone. Do not update memory from this skill.
5. **End with a ready-to-paste starter** for the new chat (see template).

## Output template — use exactly this structure, every time

```
# Session Handoff — <one-line title of what this session was about>

## Where it started
<2-3 sentences: what the user asked for, key framing or constraints that emerged>

## Not done — carry ALL of these forward
- [ ] <item> — <state: not started / partial / blocked / founder-deferred / OWNER: who> — <why not done> — <next concrete step>
- ... (every item from the sweep in step 2; write "none" ONLY if truly nothing is unfinished)

## Decisions locked + what shipped
- <decision or change> — <why, and where it lives (absolute path if a file)>
- ...

## Key files for next session
- `<absolute path>` — <why the next agent should read this first>
- Plan file: `<path>` (if a plan drove the session)
- Memory files touched: `<paths>` (if any)

## Running state
- Background processes: <shell IDs + what they are + how to kill> — or "none"
- Dev servers / ports: <url + port> — or "none"
- Open worktrees / branches: <paths> — or "none"
- Lanes in flight: <sub-agents / cloud sessions / routines / PRs still running — id, what it does, where its result lands, the one watcher command (e.g. `~/.claude/bin/lanes-wait OWNER/REPO#N ...`)> — or "none"

## Only you can do (founder)
1. <store step / sign-in / design call — with deep link; never "merge PR" — merge it yourself> — or "none"

## Verification — how to confirm things still work
- `<command>` — <expected outcome>
- ...

## Open questions
- <question needing the user's input> — <context> — or "none"

## Pick up here
<1-2 sentences: the first action for a fresh agent — then work through every item in Not done>

## Paste into the new chat
> Continue from the handoff at `~/.claude/handoffs/<file>.md` — read it first. Then: <pick-up action>, then finish every item in its "Not done" list (founder-deferred and OWNER items stay listed, untouched, until done).
```

## Hard rules

0. **Your final reply MUST end with the paste-in starter in a fenced code block** — absolute path to the handoff file + the exact next action, so the new chat guesses nothing. Never end with just "I stopped because context is large". If state changes after you write the file (e.g. a reviewer returns), update the file before stopping — no stale lines; record results, don't say "see earlier chat".
1. **Chat + one handoff file** in `~/.claude/handoffs/` only. Never update memory from this skill (lasting lessons → `/learnings`).
2. **Never drop a not-done item.** Every unfinished, deferred, parked, blocked or OWNER item goes in "Not done", however small or old, including ones carried from an earlier handoff. A short handoff that loses an item is a failed handoff. Only remove an item when it is verifiably done (cite the PR/commit in "what shipped").
2a. **Never invent state.** If a section has nothing to report, write "none" — do not omit the section. Structure stability is the whole point.
3. **Absolute paths always.** The next agent may have a different working directory.
4. **If a plan file drove the session, name it first** in "Key files" so the next agent reads it before anything else.
5. **No emojis, no hype, no "great job" summaries.** Terse and concrete — paths, commands, shell IDs, decisions. Match the tone of a seasoned engineer handing off at end-of-shift.
6. **Background process IDs are critical.** If you started any `run_in_background` shells, their IDs must appear in "Running state" with the kill command — the next agent cannot find them otherwise.
7. **Worktree path is critical.** Check your environment context (system prompt) for "Primary working directory" and "Current branch" before writing "none" for worktrees. If the path contains `.claude/worktrees/` or the branch starts with `claude/`, you are in a worktree — record the absolute path and branch name. A worktree not named in the handoff will be auto-deleted by the runtime if no files were written.

## Anti-patterns — do not do these

- Summarizing the last 3 turns and calling it a handoff.
- Adding a "what went well / what went poorly" retrospective. This isn't a retro.
- Leaving deferred / not-done items out of the handoff, or burying them in prose. They go in "Not done", one checkbox each.
- Recommending next steps beyond the "Pick up here" line plus the Not done list. The next agent decides; you just hand off.
