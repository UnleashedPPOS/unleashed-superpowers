# Monthly prune: routine prompt

Book this as a monthly cloud routine on Opus (it makes judgement calls about retiring rules), plus a
local run on the Mac for the parts the cloud can't see (hits log, feedback memories). Paste the block below as
the routine prompt.

```text
Monthly corrections prune for UnleashedPPOS/unleashed-superpowers. No API keys, no live LLM calls.
Sub-agent cap: 1.

1. Clone the repo. Run:
     python3 scripts/corrections.py prune > /tmp/prune.md
     python3 scripts/corrections.py inventory --check
     python3 scripts/corrections.py unenforced --check
     python3 -m unittest discover -s tests/hooks && python3 -m unittest discover -s tests/learning
   On the Mac also pass --hits ~/.claude/state/corrections-hits.jsonl and
   --memory-dir ~/.claude/projects/-Users-elliotkelly-Developer/memory (the defaults).

2. Never-fired checks (0 hits in 30 days): keep it if the mistake is rare but costly (credentials,
   OpenRouter, deleting test accounts); otherwise retire it (class -> prose, or delete the entry and its rule
   line) and say why in the PR.

3. Stale dated facts (measurements older than 45 days in always-loaded rules): re-measure if the cloud
   can, else move the fact into the skill that owns it (where-work-runs, llm-provider-chain) with its date,
   and leave the rule line undated.

4. Word budget: if over docs/learning/budget.json, move detail into skills until under. Never raise the
   budget without the founder.

5. Unclassified feedback memories (Mac run): classify each with /learnings (check, eval or prose) and cite
   it as the entry's source.

6. Unenforced report: any prose correction the founder repeated this month gets promoted to a check or eval.

7. Contradictions: grep the rules and skills for two homes of one fact (model table, provider order,
   question limits, merge policy). Each fact keeps one home; the other becomes a pointer.

8. One PR titled "chore(learning): monthly prune YYYY-MM" with the prune report in the body, /ship-check,
   and a PushNotification only if something needs the founder.
```
