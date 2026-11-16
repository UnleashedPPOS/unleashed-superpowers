---
name: supabase-cli
description: "Supabase CLI cookbook and decision flow: apply SQL files, run queries, confirm the linked project, verify writes, migration layouts, and when the Supabase MCP is the right tool. Use for any Supabase database, migration, SQL, edge-function or project task, or when tempted to say 'paste this in the Supabase dashboard'. SKIP for client-side supabase-js code."
---

# Supabase CLI

**Announce at start:** "I'm using the supabase-cli skill to run this through the CLI."

## Thesis
The CLI is linked in every Unleashed repo and can do almost everything. "Paste this in the Dashboard" skips the CLI and hands the founder work we can do. MCP is a fallback for the few things the CLI can't expose; the Dashboard is last.

## When this fires
- Any SQL, migration or Supabase project operation.

## Mandatory checklist

### Pass 1: pick the tool
1. CLI can do it → CLI (`/opt/homebrew/bin/supabase` on the Mac).
2. CLI can't → state the limit, use MCP.
3. MCP unavailable → Dashboard SQL editor as a last resort.
4. Cloud session with no CLI or nothing linked: Supabase MCP if present, else write the SQL into the PR and list it under Needs you.

### Pass 2: run it safely
1. Confirm the linked project before any write: `supabase projects list | grep '●'`.
2. Wrong project linked: `supabase link --project-ref <ref>` only after the founder confirms.
3. Verify every write with a follow-up SELECT.

## Catalogue: commands
```bash
# Apply a SQL file (multi-statement OK)
cd <repo> && supabase db query --linked --file path/to/migration.sql
# Inline query
supabase db query --linked "SELECT count(*) FROM rag.sources;"
```
- `CREATE OR REPLACE FUNCTION` → `"rows": []` is success.
- `db push` only works on the `supabase/migrations/` layout. The brain repo uses top-level `migrations/` → `db query --file` per file.
- A multi-statement file failing partway: the CLI names the failing statement. Idempotent DDL (`CREATE OR REPLACE`, `IF NOT EXISTS`) is safe to replay.

## Catalogue: when MCP is right
- Branch operations the CLI doesn't expose (`list_branches`, `pause_project`, `rebase_branch`).
- The founder asks for MCP.
- Structured error fields the CLI formatting hides.

## Anti-pattern flags
- "Paste this into the SQL editor" → the correction check blocks it in replies.

## Integration with other skills
- `founder-handoffs` only when MCP and CLI are both unavailable.

## Red flags
| Thought | Reality |
|---|---|
| "The Dashboard is quicker" | It moves work onto the founder. |
| "It's probably the right project" | Check `projects list` first. |

## Reference
- Always-loaded rule: `cloud-kit/rules/supabase.md`.
