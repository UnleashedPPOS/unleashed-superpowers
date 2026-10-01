# /red-team — lessons & live examples (reference)

Read on demand only. `commands/red-team.md` points at the section it needs. The rules are in the command; this file holds the incidents and reasoning behind them.

Where it started, the standing instruction: *"We show everything, all good. Now look for a reason for it NOT to be."* That sentence is the whole job.

## Memory files that govern red-team
- `feedback_close_findings_before_reporting.md`: never hand the user a list you could have closed. The only acceptable returns: "Done, here's the proof"; a tracked OWNED-ELSEWHERE item; "Blocked on [genuine external input]".
- `feedback_subagent_completion_verification.md`: GitHub `mergeable`/`mergeStateStatus` lag and lie. A subagent's "completed" can be a mid-thought cutoff.
- `feedback_senior_dev.md`: apply clearly-correct fixes immediately.
- Lessons 2026-04-15 ("work complete" ≠ done) and 2026-05-21 (streaming/tools: silent empty-success).

## Real path, not proxy: SES vs Supabase SMTP
We proved the SES identity could send (SigV4 API) but never proved that Supabase's stored SMTP credentials authenticate (a derived password). The component worked; the wired path did not. Always drive the exact path production uses.

## Silent empty-success
An HTTP 200 with `actions:[]`. An insert that RLS denied without throwing. A no-op that logs nothing. None of these show up in Sentry, logs, or to users. Assert on the effect (row written, email received, state changed).

## "Work complete" ≠ done: what counts as proof
- Migration → an `information_schema` SELECT via `supabase db query --linked` (CLI-first per `~/.claude/rules/supabase.md`; MCP as fallback).
- Edge fn → `supabase functions list` (or the platform's deploy manifest) shows `updated_at` advanced, plus a 2xx in the logs.
- Test → exit code + count.

## Verification theater: arg-name mis-split
A "ship-check passed" report claimed reviews had run. They hadn't; someone eyeballed the diff. An arg-name mis-split bug got through until the reviews actually ran. If you can't cite the agent's findings, the review didn't happen.

## Entangled "merge it"
"Merge it" can silently mean "ship a 20-commit multi-author track to prod". Check for a dedicated PR, authors (`git log origin/main..HEAD --format='%an'`), and live pushes (a foreign commit after yours, a `.git/index.lock` collision).

## OWNED-ELSEWHERE: PR #368
Red-team was closing the detection half of a drift fix while the runtime half was being written in PR #368 (latest commit 3 minutes old). Force-fixing it would have collided. Disposition: link it, confirm it covers the crack, mark it tracked. This is not a violation of fix>flag, because the fix IS happening, just not by your hand.

## Hands off others' WIP
A "leftover" you blow away can be hours of a parallel session's unsaved work. Run `git status --porcelain` + `git worktree list` before any branch switch, prune, stash or reset.

## Self-spawning orchestrator parks
One dispatched agent fans out background reviewers, then reports "I'll act once their notifications land" and parks. A nudge gets "standing by". A second "resume" agent duplicates work and can race a live merge or migration, so kill the parked duplicate. Completions from nested agents DO reach the top session.

## Customer-facing link pointed at the wrong host
A minted sign-in link pointed at the wrong host, and it looked identical in code review. Only hitting the real URL (`curl -sL <url> | grep -o '<title>[^<]*</title>'`) caught it. Check for a staging domain, a default landing page, or the wrong tenant.

## A stale "admin-only" comment
A comment saying a field is "not writable through X" can survive a refactor that made it writable. Grep every RPC, edge function and UI form that could write the field.

## Provider-pending states
A WhatsApp template stuck in `PENDING`, a domain still verifying, a webhook not yet subscribed. The submit call returning 200 does not mean it's approved. Query the provider's actual state.

## Biggest claim first: the onboarding crash
The onboarding-crash falsification came from attacking the claim "state of the art", not from grepping `String(error)`. Load-bearing claims hide the highest-value cracks.

## INSPECTED → SURVIVED needs a new experiment: the uniqueness constraint
A reviewer claimed "nothing enforces uniqueness on X", and it still looked right on a second read. A real duplicate insert against the live DB showed the constraint already existed under a different name. Re-reading rebuilds the same mental model that produced the claim, so it can't show that the claim's premise was false.
