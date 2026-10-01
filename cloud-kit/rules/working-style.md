# Working style — lessons from long multi-lane sessions (2026-10-01)

## Reporting to the founder
- Bring fixes, not problems: "X was red → here's the PR that fixes it", never just "X is red".
- At most ONE question per turn. Otherwise take the sensible default and say what you chose.
  A question the founder dismisses stays dismissed — don't re-ask it.
- Never raise MCP/connector auth problems — use the CLI and move on (founder 2026-10-01: "dont worry about the mcps").
- Keep one short, ordered "only you can do" list (store steps, sign-ins, design calls, each with a
  deep link). Update it in place; don't scatter these through the chat.
- **Merge it yourself** once the PR is reviewed, green and conflict-free (resolve conflicts yourself) — never put
  "merge this" on the founder's list (founder 2026-10-01: "You need to merge it. Why do I need to merge it?").
  If a permission/safety check actually denies the merge, report that once and stop — never reach the same result another way. Work that can't run here (Expo dep bumps, blocked hosts)
  goes on the local-ops list; never fake it by hand.

## CI
- Slow isn't stuck: a first result can take 1h+. Before calling it stuck, check whether other
  PRs in the same repo got results recently.
- Never push (or empty-commit) just to restart checks — it re-queues the PR at the back.
- "Flaky" is not a diagnosis. Reproduce (e.g. on an overloaded machine), fix the cause, prove the fix
  the same way.

## Helper agents / shared branches
- Each helper works in its own worktree; verify `pwd` after any `cd` before a merge/commit.
- `git fetch` + rebase/pull before touching a branch — other sessions push to the same branches.
- When branches conflict on a count/number, recount the real thing; never just pick a side.

## Output — founder reads only the ending (HARD RULE, 2026-10-01)
Founder: "I barely read anything you say… just tell me the high level things at the end."
- While working: NO narration. No "Let me…/Now I'll…", no commentary between tool calls, no recaps of
  tool output, no option surveys. Just call the tools.
- Final message only, ≤4 lines, in this order:
  **Done:** what shipped (PR link, merged/live yes/no)
  **Remaining:** "No known bugs, nothing left" ONLY if SHIPPABLE and merged; otherwise start with NOT SHIPPABLE /
  WITH CAVEATS / SHIPPABLE BUT NOT MERGED, then each open item + why
  **Proof:** one concrete item (merged PR link, "N passed", CI run link, screenshot)
  **Needs you:** only-you steps with deep links (omit if none)
- Never report bugs found-and-fixed, review findings, review rounds or how a fix was made — the founder only
  needs the end state. That detail lives in the ship-check report file, unlinked unless asked.
- **Auto ship-check:** any fix/feature/change work → run /ship-check (red-team included) yourself before the
  final message, then merge + deploy per its gate. Never end with "want me to ship-check?". A Stop hook
  (`hooks/auto-ship-check.py`) blocks ending a turn that changed code without it.
- Mid-task messages: none. If the app forces one, ≤3 plain words ("Still working.") — no technical detail,
  no file names, no findings.
- No explanations, background or reasoning unless asked. Detail needed later → write it to a file, link it.
- Questions/explanations the founder explicitly asks for: answer directly, still lead with the answer.
