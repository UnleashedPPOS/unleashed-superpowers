---
name: heads-up-block
description: "Use when writing or templating any agent, lane, routine or sub-agent brief, and when a build report lists additions: put a four-line Heads-up (what's missing, what could go wrong, what already exists, what's newer or better) at the top of the brief, and give each addition a one-tap kept / not needed. Triggers: 'heads-up', 'brief', 'lane prompt', 'routine prompt', 'additions', 'what did you add'. SKIP for one-line lookups."
---

# Heads-up block

I'm using the heads-up-block skill to put the four-line Heads-up on this brief.

## Thesis
The prompt is a floor. The agent that reads it knows less than the writer about what is missing, what already exists and what has changed since. Four lines at the top, written before the Goal, close that gap cheaply. Whatever the agent adds beyond the prompt is reported as an addition the founder can keep or drop with one tap, so "is the extra work wanted?" becomes a number (Chief Health: additions kept) and not a feeling.

## When this fires
- Writing or re-templating any lane, routine, or sub-agent brief (shape: `where-work-runs`, brief catalogue).
- Ending a build report that contains things nobody asked for.

## Checklist
1. Write exactly four lines, at most one sentence each, above Goal:
   - **Missing:** what the prompt leaves out that the work needs.
   - **Could go wrong:** the likeliest way this fails or does harm (money, prod data, privacy, a user-visible regression).
   - **Already exists:** the code, page, skill or memory that already does part of this. Search before asserting.
   - **Newer or better:** a newer version, simpler approach or better tool than the one the prompt assumes.
2. A line with nothing real to say reads `none found`. Never pad.
3. In the report, list each addition under Heads-up as one line with a stable ref (PR number plus a short slug). The member-facing tap is "kept" or "not needed"; it writes `chief.addition_feedback` (owner only).
4. A measure with no feedback yet shows "not measured yet", never zero.

## Anti-patterns
- More than four lines, or a paragraph per line.
- Asserting "already exists" without a search.
- Reporting additions as Done: they are Heads-up.

## Integration
`where-work-runs` holds the brief template; this block sits above its Goal line. `high-level` owns the report format (Heads-up section).

## Red flags
| Thought | Reality |
|---|---|
| "The brief is clear enough" | The writer always thinks so; the four lines are for what they cannot see. |
| "Nothing could go wrong" | Write the likeliest failure anyway, or `none found` after looking. |
| "I'll skip the tap, it's obvious" | Unmeasured additions never get pruned. |
