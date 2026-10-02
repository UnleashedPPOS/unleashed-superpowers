---
description: "Turn High-Level mode (end-state-only reporting) on or off for this and every future session. Usage: /high-level-mode on | off | status"
argument-hint: "on | off | status"
allowed-tools: Bash(mkdir:*), Bash(touch:*), Bash(rm:*), Bash(test:*)
---

Argument: `$ARGUMENTS` (empty means `on`).

High-Level mode is stored as one flag file, `~/.claude/high-level-mode`. While it exists, this plugin's SessionStart hook loads the rules into every new session.

1. **on** (or empty): run `mkdir -p ~/.claude && touch ~/.claude/high-level-mode`. Then invoke the `high-level` skill so the mode applies from your next reply in THIS session too. Reply with one line: "High-Level mode on, for this and every new session." If this plugin is not installed (no `hooks/high-level-session-start.sh` under an `unleashed-superpowers` plugin, e.g. a cloud session set up by `cloud-kit/install.sh`), reply instead: "High-Level mode on for this session. New sessions need the plugin's hook or the High-Level output style."
2. **off**: run `rm -f ~/.claude/high-level-mode`. Stop following the High-Level rules for the rest of this session. Reply with one line: "High-Level mode off."
3. **status**: run `test -f ~/.claude/high-level-mode && echo on || echo off` and reply with that one word.
4. **Anything else**: reply with the usage line `/high-level-mode on | off | status`.

Run the command; don't explain it.
