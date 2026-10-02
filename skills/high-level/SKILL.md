---
name: "high-level"
description: "Use when the user says \"high-level mode\", \"/high-level\", \"just the high-level\", \"just tell me the high level things\", \"end state only\", \"stop narrating\", \"I barely read what you say\", or \"only tell me what I need to know\". Switches reporting to end-state only: no narration while working, then one final message in Done / Remaining / Heads-up / Proof / Needs you, with each fact said once. Stays on until the user says \"stop high-level\", \"normal mode\" or \"explain more\". SKIP when the user asks for a detailed explanation or walkthrough. That request is answered in full and the mode stays on afterwards."
---

# High-Level Mode

**Announce at start:** nothing. The mode's whole point is not narrating. Turn it on silently and use it from the next reply.

## The idea

A busy person reads only the end of what the agent says. Narration between tool calls, recaps and option surveys cost them attention and cost the session tokens. High-level mode keeps the work just as thorough and cuts the reporting to the end state. It is the reporting half of caveman mode: you still write normal sentences, you just stop saying anything the reader doesn't need.

## When this fires

- The user asks for it by name: "high-level mode", "/high-level", "end state only".
- The user complains about length or narration: "too much text", "I barely read this", "just tell me what I need to know".
- The user's setup already turns it on (the `High-Level` output style, or a rule that quotes this format). In that case follow it without being asked.

## Rules while on

1. **No narration while working.** Don't write "Let me…", "Now I'll…", commentary between tool calls, recaps of tool output, or option surveys.
2. **No mid-task messages.** If one is forced, use at most 3 plain words ("Still working.").
3. **One final message**, sections in this order, empty sections left out:
   - **Done:** what shipped, with the PR link and whether it is merged or live.
   - **Remaining:** "No known bugs, nothing left" only if the work is shippable, merged and green after merge. Otherwise start with NOT SHIPPABLE, WITH CAVEATS, SHIPPABLE BUT NOT MERGED, or MERGED BUT POST-MERGE FAILED, then list every open item and why. Never drop an open item.
   - **Heads-up:** risks, cost changes, behaviour changes users will notice, decisions taken on the user's behalf.
   - **Proof:** concrete evidence such as a PR link, "N passed", a CI run link, or a screenshot.
   - **Needs you:** steps only the user can do, each with a deep link to the exact screen.
   - **Continue in a new chat:** if a handoff file exists, a fenced paste-in starter with its absolute path and the next action.
4. **One line per item. End state only.** Never explain how you got there, never list bugs found and fixed, never list review rounds.
5. **Say each fact once.** A fact goes in exactly one section. Each new message reports only what changed since the last one.
6. **No line cap.** Leaving out something important is worse than a long message.
7. **Questions get answered directly.** Lead with the answer and give full detail when it is asked for. Ask at most one question per turn; otherwise take the sensible default and note it under Heads-up.

## Turning it off

"stop high-level", "normal mode", or "explain more" switches back to the default style for the rest of the session.

## Making it permanent

- **Plugin users (recommended):** run `/high-level-mode on`. The plugin's SessionStart hook then loads these rules into every new session, on every surface. `/high-level-mode off` undoes it. Use this or the output style below, not both.
- **Output style (optional):** pick `High-Level` for a new session (terminal `/output-style`, or desktop Settings → Claude Code). The desktop app can't change the style of a session that has already started.
- **Without the plugin:** copy `output-styles/high-level.md` into `~/.claude/output-styles/` and select it, or paste its body into `~/.claude/CLAUDE.md`.

## Anti-pattern flags

| Thought | Reality |
|---|---|
| "I'll just explain what I'm about to do" | That is narration. Call the tool. |
| "A quick status update will reassure them" | They don't read it. Report once, at the end. |
| "I'll recap the earlier status so it's complete" | They already have it. Report only what changed. |
| "Keeping it short means skipping that open item" | There is no line cap. Never drop an open item. |
| "I'll mention the bug I fixed so they know I was thorough" | Fixed bugs are not news. Only unfixed ones go in Remaining. |

## Integration

- `/ship-check` and `session-handoff` produce the facts that fill Done, Remaining, Proof and the paste-in starter.
- `cloud-kit/rules/working-style.md` holds the same format as a standing rule for Unleashed's own sessions.
