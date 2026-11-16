# Founder hand-offs and credentials (HARD RULE, 2026-06-04; credential and hand-off rules merged 2026-11-16)

- Credentials, accounts, logins, 2FA, billing, API keys, OAuth setup: never self-drive (no browser automation, no headless signups) unless the founder says "you do it". Hand it off at once; the founder is far faster at their own logins.
- Never put a login on the founder's list for a tool we drive by CLI + vault key (supabase, gh, vercel, fly, ssh, telnyx, groq) ✓: check `vault list` and the CLI first.
- Each hand-off step: what it unlocks and what happens if skipped (one line), the exact deep link to the screen (never a homepage), what to click and copy, exactly what to paste back (variable names + format), and a doc link if useful.
- Verify every URL before giving it (fetch the docs, read project config or the source); if no exact link exists, say so and give the closest one ✓. URL state you haven't confirmed in the source (`?tab=`) is fiction.
- Where it goes: the status page's Needs you; chat only when there is no page or it is this turn's one question. (Replaces the old "in chat, not a doc" line, which predates status pages.)
- After the founder pastes, do every downstream step yourself: wiring, deploy, verification. Never punt steps back.
- Pasted credentials: store with `vault set`; never echo, commit or repeat them ✓.
- Deep-link patterns (Slack webhook, Supabase, Vercel, GitHub secrets, Stripe) and the full hand-off format: skill `founder-handoffs`.
