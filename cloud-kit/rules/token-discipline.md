# Token discipline (HARD RULE; rewritten 2026-11-16)

Why: every turn re-reads the whole chat, so cost ~ turns x context size. Levers: fewer turns, smaller context, cheaper model. Where work runs (cloud, Netcup, laptop), overload fallbacks, routines, merge trains and disk hygiene: skill `where-work-runs`, loaded before heavy work, CI waits or routines.

## Tool calls (biggest lever)
- Batch: independent reads/greps/commands go in ONE message (parallel calls) or one script. The `serial-call-nudge.py` hook warns after 8 single calls in a row.
- Read a file region once, in a generous chunk; never many `sed -n` slices; don't re-grep what you have. Investigate with one broad gather, then act.
- Several edits to a file go in one message. Don't re-read just-edited files or re-verify what a tool already confirmed.

## Waiting
- Never send "still waiting" turns; nothing changed -> end the turn silently. Blocked on CI or the founder: say it ONCE, then back off to every few hours.
- Waiting > 5 min: end the turn, write state to a handoff file, resume via notification or ScheduleWakeup (1200s+). One watcher for all PRs (`~/.claude/bin/lanes-wait`), never a poll loop and never a sleep inside a big session; it must exit on a ~60 min stall.

## Session size
- Token discipline is HOW work is done, never WHETHER: context size is never a reason to defer, descope or skip. Never tell the founder you're "keeping the session small" ✓.
- No cap on concurrent chats; keep each lean. Unattended work runs through auto-compactions; never stop or ask for a new chat because context is big (the 4-compaction hook means "fresh chat for the next job", not stop). Start the NEXT job in a fresh chat (handoff + paste-in starter) once this one is done or blocked on the founder.
- autoCompactWindow is 250000; don't raise it, and never commit a different number in a repo's `.claude/settings.json` ✓.

## Models and delegation (the one model table)
- **Model policy (founder HARD RULE 2026-11-16, newest; supersedes memory "Build in Fable"): plan in Opus -> build in Sonnet (Haiku for fully specified mechanical work) -> review + ship-check in Opus. NEVER Fable (`claude-fable-5-2`) for lanes, routines or sub-agents** ✓ (two lanes died on the weekly Fable limit). Every build routine gets a matching Opus review routine booked at the same time. Enforced by `hooks/model-guard.py` (PreToolUse): Fable, a routine with no model, a non-Opus review routine, or a routine prompt with no sub-agent cap is denied.
- **Sub-agent budget ("you be the CFO"):** each sub-agent is a fresh context start (~40k). A lane or chat does its own build; at most 3 sub-agents per lane/chat unless the work truly splits into independent slices; reuse one via SendMessage for follow-up rounds. Every lane prompt states its cap.

| Agent | Model | Use for |
|---|---|---|
| `sonnet-builder` | sonnet | **Default build**: features, known-cause fixes, refactors, routine reviews, research, write-ups |
| `haiku-worker` | haiku | Fully specified work: sweeps, CI/PR watching, merging, plumbing, renames, tests to spec, doc fixes, summaries |
| `opus-thinker` | opus | Planning, review + ship-check, and genuinely hard calls: design, non-obvious root causes, audits/red-team, risky decisions. Never routine review fan-out |

- Main chat defaults to Sonnet; Opus only for planning, review or a hard stretch, then back. A main chat not on Opus orchestrates and sends hard thinking to `opus-thinker`.
- Unsure which tier: pick the cheaper one and escalate one tier only when the result is weak or the agent says it's unsure. Haiku briefs must be self-contained (files, change, how to verify); a vague brief goes to Sonnet.
- Effort medium by default; `high` only when hard (unclear root cause, security/money/prod data); `xhigh` for the hardest only. Never raise by habit.
- Sub-agents work silently and return ONE result under 300 words; not for a 1-3 call lookup. Ad-hoc agents must pass `model:`. Fork only when the task needs this chat's context and context < ~60k.
- Cloud first: work that can run in the cloud runs as a one-shot cloud routine; stay local only for vault secrets, DB/deploy CLIs, ssh and the built-in browser; at most ONE local sub-agent at a time (8GB laptop).

## Keep context lean
- No whole-file Reads of large files; filter big output and print only the answer. Don't load connectors you don't need; use CLIs (vercel/gh/supabase/apify/playwright-cli/ctx7).
- Always-loaded rules have a word budget (`tests/learning/test_word_budget.py`); detail goes in skills or memory loaded on demand.
