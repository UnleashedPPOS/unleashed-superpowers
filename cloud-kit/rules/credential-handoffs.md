# Credential & Account Tasks — hand off, DON'T self-drive (HARD RULE, 2026-06-04)

When a task needs the **user's own** credentials / accounts / logins / 2FA / billing / API-key creation / OAuth-client setup (Google Cloud, Railway, Firecrawl, Stripe, Cloudflare, any vendor dashboard):

**DO NOT try to do it yourself the slow way.** No driving browsers (Playwright / computer-use), no headless signup flows, no "I'll walk us through it together." The user is *far* faster at their own logins than any browser automation.

**Instead, IMMEDIATELY give the user, in chat:**
0. One plain line on **what it unlocks** and what happens if skipped (founder 2026-10-01: "what does openalex even help with???").
1. The exact **deep-link URL** for each step (not a homepage — the precise screen).
2. One line per step: what to click, what to copy.
3. Exactly **what to paste back** (variable names + format).
4. Any relevant **doc link**.

Then do **everything downstream automatically** the moment they paste the value(s) back. The contract: they spend 60 seconds in the browser; you do all the wiring, deploy, and verification.

**Never put a login on the founder's to-do list for a tool we can drive by CLI + vault key** (supabase, gh, vercel, fly, ssh, telnyx/groq APIs…). Check `vault list` and the CLI first. Founder 2026-10-01: "why do you need me to log into these free tools… we have the CLI for all of them."

**Only** attempt to self-drive a credential flow if the user *explicitly* says "you do it" / "drive it."

This is the DEFAULT for credential/account work — strengthens `user-handoffs.md` (there, hand-off is best-practice; here, for credentials specifically, it is mandatory unless overridden). Rationale: the user said this directly — "just give me the URLs and instructions… I could have done the firecrawl and the Google thing so much quicker."
