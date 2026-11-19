# Monthly prune: routine prompt

This runs monthly as a cloud routine on Opus, because it makes judgement calls about retiring rules. A local run on the Mac covers what the cloud can't see: the hits log and the feedback memories.

The booking definition (schedule, model, repo) is `docs/learning/monthly-prune.routine.json`. The prompt is the block below; it has one home, and the routine content points here. `tests/learning/test_monthly_prune.py` checks that the booked definition passes model-guard: Opus, a stated sub-agent cap and a monthly schedule. To book it, pass the definition to RemoteTrigger `create` with this block as the event content.

```text
Monthly corrections prune for UnleashedPPOS/unleashed-superpowers.

Goal: the always-loaded rules stay small, current and enforced. Every founder correction has one home.
Checks that never fire are retired or justified. Prose corrections the founder keeps repeating become
checks or evals.

Constraints: no API keys and no live LLM calls. Model: Opus. Sub-agent budget: at most 1, Sonnet only,
never Fable. Never raise docs/learning/budget.json without the founder. Keep a never-fired check when the
mistake is rare but costly (credentials, OpenRouter, deleting test accounts).

Input: python3 scripts/corrections.py prune (never-fired checks, stale dated facts, unclassified
feedback memories). On the Mac also pass --hits ~/.claude/state/corrections-hits.jsonl and
--memory-dir <memory dir> (default: $CORRECTIONS_MEMORY_DIR or the first ~/.claude/projects/*/memory
with feedback-*.md files).

Done when all of these hold:
- Every check with 0 hits in 30 days is either kept, with the reason in the PR, or retired (class ->
  prose, or the entry and its rule line deleted).
- No always-loaded rule carries a measurement older than 45 days. Each one is either re-measured or moved,
  with its date, into the skill that owns it (where-work-runs, llm-provider-chain), leaving the rule line
  undated.
- The always-loaded set is under the word budget, with the extra detail moved into skills.
- Each fact (model table, provider order, question limit, merge policy) has one home, and any other
  copy is a pointer.
- Every prose correction the founder repeated this month is a check or an eval.
- On the Mac run, every feedback memory is classified with /learnings and cited as its entry's source.
- These pass: python3 scripts/corrections.py inventory --check, python3 scripts/corrections.py
  unenforced --check, and python3 -m unittest discover -s tests/hooks && python3 -m unittest discover
  -s tests/learning.

Report: one PR titled "chore(learning): monthly prune YYYY-MM", with the prune report in the body and
/ship-check run on it. Send a PushNotification only if something needs the founder.
```
