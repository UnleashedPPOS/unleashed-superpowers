# Supabase

- CLI first, MCP only as fallback, Dashboard SQL editor last. Never default to "paste this in the Dashboard" ✓.
- Confirm the linked project before any write (`supabase projects list | grep '●'`) and verify writes with a follow-up SELECT. Wrong project linked: confirm with the founder before `supabase link`.
- Cloud session (no CLI, nothing linked): the Supabase MCP if present, else write the SQL into the PR and list it under Needs you.
- Commands, MCP-only operations and gotchas: skill `supabase-cli`.
