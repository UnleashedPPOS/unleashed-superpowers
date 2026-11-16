# Test accounts and fixtures: reuse, never recreate (HARD RULE, 2026-11-06)

Founder: "they should just be stored somewhere so that we can just use them whenever we need them."

- Credentials live in the vault as `TEST_<PROJECT>_<ROLE>_EMAIL` / `_PASSWORD` (`vault list | grep ^TEST_`). The registry is memory `reference-test-accounts`: project, role, user id, state, purpose; never passwords. Emails: `qa+<project>-<role>@unleashed.vision`, never the founder's personal addresses.
- Before any QA, smoke test, e2e run or browser check, use a fitting existing account. Create one only when none fits the role, and save it to the vault and the registry in the same turn. One stable account per project and role; never throwaway accounts per run.
- Need a clean state: reset the account's data (script or SQL), don't make a new account.
- Never delete, soft-delete or "clean up" a registered test account ✓ (2026-11-06: cleanup scripts soft-deleted 5, leaving half-dead users that kept getting emails).
- Never put test passwords in chat, commits or PR bodies ✓.
- Fixtures and seed data live in each repo (`supabase/seed.sql`, `tests/fixtures/`): extend, don't regenerate. A repo with its own test roles lists them in the registry.
