# /ship-check — conditional checklists 1.2–1.8 (reference)

Read by `commands/ship-check.md` Phase 1. Read a section if its trigger matches the diff. If you're unsure whether it applies, read it. Each skipped section still gets a Phase 7 row: `n/a — <why>`.

### 1.2 DB & migrations (trigger, MANDATORY: any DB change this session by any route: migration file, ORM/codegen schema, out-of-band SQL, RLS/policy/function edit). The drift check is mandatory and CLI-first (`~/.claude/rules/supabase.md`). Bare `supabase` is hook-blocked in Bash, so use `ctx_execute`; MCP is the fallback.
- [ ] Each new migration is applied on the linked project. Prove it with a live `db query --linked` SELECT on `information_schema.columns`/`pg_indexes`/`pg_policies`/`pg_proc`. "Ran the CLI" ≠ evidence.
- [ ] New tables: RLS on + an owner policy (`user_id = auth.uid()` / parent `EXISTS`), proven by a `pg_policies` row. Columns filtered at query time are indexed (`pg_indexes`).
- [ ] `schema_migrations` has a row per repo migration. If they diverge → `supabase migration repair --status applied <ts>`, then re-verify (lessons § 1.2). Docker down → `--use-api`.
- [ ] 0 **new** advisories on session tables (`supabase inspect db`; MCP advisors as fallback).

### 1.3 Edge functions / serverless (trigger: edge fn, Worker, Lambda, API route, server handler)
- [ ] Deployed version is newer than the last commit touching the function (`supabase functions list`; `wrangler deployments list` / `vercel ls` / `aws lambda get-function --query LastModified`).
- [ ] Auth uses the repo's current verification call (CLAUDE.md / auth util). `verify_jwt=false` (or equivalent) only with in-code auth compensating. Rate limiting on user-facing endpoints if the repo has a convention.
- [ ] Input validated server-side (numbers clamped, enums allow-listed, strings capped). Every `JSON.parse`/`.json()` guarded.
- [ ] User text in LLM prompts sits in a delimited block (`<context>…</context>`), never raw in the system prompt.
- [ ] Every mutating DB call checks its result (the repo's `assertWriteOk`/`assertOk` if present, else `{ error }`).

### 1.4 Security & privacy, beyond the always-on secrets/PII/sanitizer line in the command (trigger: auth, input, endpoints, secrets, payments, server handlers, logging, LLM calls). Also auto-invoke `everything-claude-code:security-review`.
- [ ] No `user_id`/email/phone/query keys in toasts or logs. Identifiers sent to an error tracker are hashed or bucketed. CORS uses real origins, never `*`.
- [ ] User-facing errors go through the repo's sanitizer (grep `src/lib`/`src/utils`, e.g. `extractErrorMessage`, `getCorsHeaders`), never raw `String(error)` or a stack trace.
- [ ] PII sent to an LLM is justified and minimised.

### 1.5 Accessibility (trigger: any UI change)
- [ ] `aria-live="polite"` on dynamic content · reduced-motion respected (`prefers-reduced-motion`/`useReducedMotion()`) · accessible names on interactive elements · keyboard/touch equivalents for hover-only interactions.

### 1.6 UX failure paths (trigger: any UI, mutation, fetch or routing change)
- [ ] Mutation errors surface the REAL reason (via the 1.4 sanitizer). 429/402 become human messages. Empty states for first run. Loading state on every async fetch.
- [ ] No silent route bounces: gated routes check `loading`/`pending` BEFORE redirecting. Grep `isAuthenticated`/`useAuth` callers (lessons § PR #309).

### 1.7 Dead code & simplicity (trigger: any code change)
- [ ] No unused imports/vars/exports · no query/mutation logic duplicated across ≥2 consumers (lift it into a hook) · no commented-out code · no dead defensive defaults (`X[slot] ?? 10_000` on a fixed-length `as const`).

### 1.8 Docs (trigger: any code change; a code change without a doc update is incomplete)
- [ ] Touched modules' docs updated · the repo's tracking doc updated if one exists (e.g. the Voice Coverage Matrix in `future.md`) · `CLAUDE.md` updated for any new convention · a module with no docs gets `/document-feature-module <module>` (or the minimum doc a contributor needs).
