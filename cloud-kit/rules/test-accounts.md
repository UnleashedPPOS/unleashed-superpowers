# Test accounts and fixtures: reuse, never recreate (HARD RULE, 2026-11-06)

The founder said: "there's no need to keep rebuilding and remaking… they should just be stored somewhere so that we can just use them whenever we need them."

## Where they live
- Credentials go in the vault: `TEST_<PROJECT>_<ROLE>_EMAIL` and `TEST_<PROJECT>_<ROLE>_PASSWORD`. Examples: `TEST_UNLEASHEDOS_MEMBER_EMAIL`, `TEST_UNLEASHEDOS_COACH_PASSWORD`. Run `vault list | grep ^TEST_` to see them all.
- The registry is memory `reference-test-accounts`. It lists each account's project, role, user id, what state it's in, and what it's for. Names and ids only, never passwords.
- Emails use the form `qa+<project>-<role>@unleashed.vision`. Never use the founder's personal addresses for QA.

## Before any QA, smoke test, e2e run or browser check
1. Check the registry and `vault list | grep ^TEST_`. If a fitting account exists, use it.
2. Only create a new account when no existing one fits the role. Save it to the vault and the registry straight away, in the same turn.
3. Need a clean state? Reset the account's data (a reset script or SQL), don't make a new account.

## Never
- Never delete, soft-delete or "clean up" a registered test account. On 2026-11-06, QA cleanup scripts soft-deleted 5 accounts, which left half-dead users that kept getting emails.
- Never put test passwords in chat, commits or PR bodies.
- Never create throwaway accounts per run. One stable account per project and role.

## Fixtures and test data
- Seed data and fixtures live in each repo (`supabase/seed.sql`, `tests/fixtures/`). Extend what's there; don't regenerate it.
- This rule is global (~/.claude/rules + cloud-kit), so every project and cloud session loads it; a repo with its own test roles lists them in the registry.
