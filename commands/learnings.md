---
description: Turn corrections and learnings from this chat (or pasted notes) into enforced checks, eval cases or one-line rules, filed in the corrections registry
argument-hint: "[optional: pasted learnings / file path / focus area / 'unenforced' / 'prune']"
---

# /learnings: a correction becomes a check, in one step

Source: $ARGUMENTS if given (pasted text or a file path), otherwise THIS chat: founder corrections, things that
went wrong, workarounds, anything that wasted tokens. `$ARGUMENTS` = `unenforced` → run
`python3 scripts/corrections.py unenforced` and promote what has been broken again; `prune` → follow
`docs/learning/monthly-prune.md`.

Work in a checkout of UnleashedPPOS/unleashed-superpowers. The registry `cloud-kit/hooks/corrections.json` is the
one source of truth: every founder correction is one entry, enforced by `cloud-kit/hooks/correction-checks.py`.

## 1. Extract (strict)
One line per candidate. Keep founder corrections ("don't X", "always Y", "I've told you before") first, then
process mistakes, non-obvious gotchas and repeated manual steps. Drop one-offs and generic advice.

## 2. Find it in the registry
`grep -n` 2-3 keywords in `cloud-kit/hooks/corrections.json`, `docs/learning/corrections-inventory.md` and
`cloud-kit/rules/`. Already there as **prose** but broken again → promote it (step 3). Already a **check** that
missed → add the missed text as a new `bad` example and widen the pattern. Repeated correction = it must not stay prose.

## 3. Classify and file it, in one step (all of a-d, every time)
a. **Class.** `check` if a regex/path rule can see it in a Bash command, a file write, the final reply or the
   founder's prompt. `eval` if it needs judgement on behaviour. `prose` only for genuine judgement calls.
b. **Registry entry** in `corrections.json`: `id`, `rule` (one line), `source` (memory / rule file / "founder
   YYYY-MM-DD"), `class`, `home` (the ONE file the rule line lives in), `anchor` (exact text in that home).
   - check: `surface` (bash / write / reply / prompt / turn), `action` (block / ask / warn / context),
     `check: regex` + `pattern` (+ `flags`, `unless`, `paths`, `skip_paths`), `message`, at least one `bad` and one `good` example.
     Logic a regex can't express goes in a named function in `corrections_lib.py` (`check: fn:<name>`).
   - eval: `eval: evals/<case>` and write `evals/<case>/prompt.md` + `graders/criteria.md` (copy an existing case).
c. **Rule line**: one line in the `home` file, containing the `anchor`. Replace or merge an older line; never
   add a second home for the same fact. Mark enforced lines with ✓ in rule files.
d. **Regenerate and test**: `python3 scripts/corrections.py inventory && python3 scripts/corrections.py unenforced`,
   then `python3 -m unittest discover -s tests/hooks && python3 -m unittest discover -s tests/learning`. The
   tests run every bad/good example, check every anchor exists and fail if the always-loaded set passes the word budget.

TDD: add the `bad` example first, watch `test_correction_checks` fail, then write the pattern.

## 4. Facts that are not rules
Project state, gotchas and measurements go to memory (Mac) or the PR body (cloud), not the rules. Detail a rule
needs goes in a skill, keeping the rule to one line (budget: `docs/learning/budget.json`).

## 5. Ship
Bump `.claude-plugin/plugin.json` + `marketplace.json` (patch), `bash scripts/build-cloud-manifest.sh`, open the PR,
run /ship-check. Cloud session: everything lands in the repo; the founder's machine syncs `cloud-kit`.

## 6. Report (on the status page, one line each)
- **Enforced now**: correction → check id / eval case (inventory row)
- **Promoted**: prose that became a check or eval
- **Stays prose**: correction → home, and why a check can't see it
- **Needs you**: anything only the founder can decide
