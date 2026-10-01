---
name: definition-of-done
description: The Unleashed definition of "shipped". Use whenever the founder says ship / done / finished / ready for users, before claiming a feature, PR, integration, API, CLI, MCP or migration is complete, and when writing a wave summary. Produces a filled DoD ledger with one honest state per row.
---

# Definition of Done

"Done" is a ledger, not a feeling. A feature is DONE only when every row below is one of
`DONE` · `N/A (why)` · `OWNER (who, what)`. Anything else is NOT DONE, and the summary
must say so in the first line. Never write "deferred". Write what is blocking and who owns it.

Fill the ledger in the PR body or the wave summary. One row per line, the state in caps first.

## 1 · Intent
- [ ] The user's ask is quoted or paraphrased, and each part maps to a row below (nothing silently narrowed).
- [ ] Plan exists (`tasks/<wave>-plan.md` or `docs/superpowers/plans/`) and the build matches it; deviations are listed with reasons.

## 2 · Front end
- [ ] Every screen reachable from a real entry point (Home / ALL / a parent screen), not only by URL.
- [ ] Empty, loading, error and offline states are real (no fabricated demo rows, no `TODO(live)`).
- [ ] Unlock rule or day-0 decision made explicitly; directory invariant tests green.
- [ ] Copy is verb-first, honest (no ✓ without a confirmed write), and readable aloud (Listen where the app speaks).
- [ ] Onboarding: a first-run hint or explainer where a new surface is not self-evident.
- [ ] Accessibility: labels on pressables, 44 px targets, reduced-motion respected, text wraps.
- [ ] Web export still builds (`expo export --platform web`) or the surface is explicitly native-only with a guard.

## 3 · Back end / data
- [ ] Tables have RLS (owner + service_role paths) and a migration that passes the idempotency checker.
- [ ] Every client insert/select uses columns that exist in the migration (grep both sides).
- [ ] Edge functions / routes validate input, bound size and rate, and fail soft with a typed error the UI can show.
- [ ] Secrets never in the bundle; new `EXPO_PUBLIC_*` names are plain endpoints and are on the allowlist.
- [ ] Cross-repo contract verified by reading the other repo's code, not the brief.

## 4 · Integrations, APIs, CLIs, MCPs
- [ ] Contract documented (request, response, errors, auth) in the PR body or `docs/`.
- [ ] Auth model stated (user JWT / service token / webhook secret) and tested for the unauthenticated path.
- [ ] Health endpoint or equivalent liveness signal exists for anything long-running.
- [ ] Deploy path exists and is written down (workflow, container, or the exact manual command + host).
- [ ] The consumer actually calls it (a client exists) or the row says `OWNER: no consumer yet`.

## 5 · Payments (when money moves)
- [ ] Prices/products exist in Stripe (test + live) and are referenced by env NAME only.
- [ ] Webhook signature verified; idempotency on every money-changing handler.
- [ ] Entitlement is read from the source of truth, never from client state.
- [ ] Refund / cancel / portal paths exist or the row says `OWNER`.

## 6 · Security
- [ ] No PII in logs, issues, or third-party payloads.
- [ ] Anti-enumeration on auth flows (sign-up, reset) verified against the real provider behaviour.
- [ ] Untrusted content (transcripts, comments, issue bodies) is wrapped/labelled before it reaches a model.
- [ ] `security-review` skill run on the diff when auth, payments, secrets, or uploads are touched.

## 7 · Verification
- [ ] Typecheck, lint, FULL test suite (repo-wide invariant suites, not lane-scoped), and any export/build gate — pasted tails, run in this session.
- [ ] Ship-check + red-team pass run against the claim ledger; every crack fixed with a regression test; residual risk listed.
- [ ] On-device / on-host verification done, or the exact unverified paths are listed under `OWNER`.
- [ ] CI on the PR head is green, or each red check has a one-comment root cause on the PR.

## 8 · Ship
- [ ] PR merged (or the row names who merges and why not yet).
- [ ] Migrations applied and edge functions / containers deployed, or the exact command + who runs it.
- [ ] Feature flags / providers enabled (e.g. Supabase Auth providers) or `OWNER`.
- [ ] Build produced where users get it (dev client, TestFlight, web) or `OWNER`.

## 9 · Aftercare
- [ ] Docs: feature-module doc or README updated; `tasks/<wave>-summary.md` written; `tasks/lessons.md` gets any genuinely new failure mode.
- [ ] Observability: errors reach Sentry / Sentinel; a failure is visible, not silent.
- [ ] Founder Console (or the current status page) updated with the ledger states.

## Output format

```
DoD · <feature>  —  DONE 31 · N/A 4 · OWNER 3 · NOT DONE 0
1 Intent ........ DONE
2 Front end ..... DONE (hint added on Home)
3 Back end ...... OWNER: Elliot — supabase db push (no CLI token in cloud env)
...
```
The first line is the verdict. If NOT DONE > 0, the feature is not shipped and the summary says so.
