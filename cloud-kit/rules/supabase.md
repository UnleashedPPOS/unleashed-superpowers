# Supabase

Cloud session (no Mac CLI, nothing linked): if `supabase` is missing or unlinked, use the Supabase MCP if present, else write the SQL into the PR and list it under Needs you.

**Rule: CLI first, MCP only as fallback.** CLI lives at `/opt/homebrew/bin/supabase`; Unleashed repos are already linked.

## Decision flow

1. CLI can do it → use CLI.
2. CLI can't → state the limitation, offer MCP.
3. MCP unavailable → Dashboard SQL editor (last resort).

Never default to "paste this in the Dashboard" — that skips the CLI.

## CLI cookbook

```bash
# Apply a SQL file (multi-statement OK — CLI handles it in one call)
cd <repo> && supabase db query --linked --file path/to/migration.sql

# Inline query
supabase db query --linked "SELECT count(*) FROM rag.sources;"

# Confirm linked project before any write
supabase projects list | grep '●'
```

Notes:
- `CREATE OR REPLACE FUNCTION` → `"rows": []` is success.
- Verify writes with a follow-up `SELECT`.
- `db push` only works on `supabase/migrations/` layout. Brain repo uses top-level `migrations/` → use `db query --file` per-file.
- If wrong project linked: `supabase link --project-ref <ref>` — confirm with user before mutating.
- Multi-statement file fails partway → CLI surfaces the failing statement. Idempotent DDL (`CREATE OR REPLACE`, `IF NOT EXISTS`) is safe to replay.

## When MCP is the right tool

- Branch ops the CLI doesn't expose (`list_branches`, `pause_project`, `rebase_branch`).
- User explicitly asks for MCP.
- Need structured error fields the CLI formatting hides.
