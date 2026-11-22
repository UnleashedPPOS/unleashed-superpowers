# Founder hand-offs and credentials (HARD RULE, 2026-06-04)

- Credentials, accounts, logins, 2FA, billing, API keys, OAuth setup: never self-drive (no browser automation, no headless signups) unless the founder says "you do it". Hand it off at once; the founder is far faster at their own logins.
- Never put a login on the founder's list for a tool we drive by CLI + vault key (supabase, gh, vercel, fly, ssh, telnyx, groq) ✓: check `vault list` and the CLI first.
- Each hand-off step: what it unlocks and what happens if skipped (one line), the exact deep link to the screen (never a homepage), what to click and copy, exactly what to paste back (variable names + format), a ready paste-in starter, a phone-or-laptop tag, and a doc link if useful. An item closes only when you have checked the result (founder 2026-11-22).
- Verify every URL before giving it (fetch the docs, read project config or the source); if no exact link exists, say so and give the closest one ✓. URL state you haven't confirmed in the source (`?tab=`) is fiction.
- Where it goes: the status page's Needs you; chat only when there is no page or it is this turn's one question.- After the founder pastes, do every downstream step yourself: wiring, deploy, verification. Never punt steps back.
- Pasted credentials: store with `vault set`; never echo, commit or repeat them ✓.
- Never print a secret (`vault get`, `printenv`, `cat .env`) or put a credential in a command or file; use `vault run` ✓.
- Deep-link patterns (Slack webhook, Supabase, Vercel, GitHub secrets, Stripe) and the full hand-off format: skill `founder-handoffs`.
