---
name: founder-handoffs
description: "How to hand a step to the founder: credentials, logins, API keys, OAuth clients, billing, vendor dashboards (Google Cloud, Railway, Firecrawl, Stripe, Cloudflare, Slack webhooks, GitHub secrets, Supabase, Vercel). Use whenever a task needs the founder's own account, a value pasted back, or a click in a third-party UI, and when writing a Needs you list. SKIP when the tool can be driven by CLI plus a vault key."
---

# Founder hand-offs

**Announce at start:** "I'm using the founder-handoffs skill to hand this step over."

## Thesis
The founder spends a minute in the browser; you do everything else. A hand-off is only good if every step has the exact deep link, one line of what to click, and exactly what to paste back. Guessed URLs and "navigate to settings" cost more than they save.

## When this fires
- Any step needing the founder's own credentials, account, 2FA, billing, API-key or OAuth setup.
- Any click in a third-party UI or the deployed app that you cannot do.

## Mandatory checklist

### Pass 1: can we avoid it?
1. `vault list` and the CLI first (supabase, gh, vercel, fly, ssh, telnyx, groq). If the tool is drivable, drive it; never put that login on the founder's list (founder 2026-10-01: "we have the CLI for all of them").
2. Self-drive a credential flow only if the founder said "you do it" / "drive it".

### Pass 2: write the hand-off
1. Line 0: what it unlocks and what happens if skipped (founder 2026-10-01: "what does openalex even help with???").
2. One line per step: deep link → what to click → what to copy.
3. What to paste back: variable names and format.
4. A doc link if useful.
5. Put it under Needs you on the status page; chat only when there is no page or it is the turn's one question.

### Pass 3: verify every URL
1. Fetch the vendor docs, read project files (`vercel.json`, `.vercel/project.json`, `package.json`) or query the CLI for deployed domains.
2. Read the source before adding URL state: `?tab=voice` is fiction if the app uses uncontrolled tabs.
3. No exact link found: say so ("closest is X, then click Y"). Never present a guess as working.

### Pass 4: finish downstream
1. When the value arrives: `vault set`, wire it, deploy, verify. Never punt a step back after the paste.

## Catalogue: deep links
| Action | Use |
|---|---|
| Slack incoming webhook | `https://my.slack.com/services/new/incoming-webhook/` (one page: pick channel, Add Integration, copy URL) |
| Supabase project | `https://supabase.com/dashboard/project/{REF}` plus the subpath |
| Vercel project | `https://vercel.com/{TEAM}/{PROJECT}` |
| GitHub repo secrets | `https://github.com/{OWNER}/{REPO}/settings/secrets/actions` |
| GitHub Actions run | `https://github.com/{OWNER}/{REPO}/actions/runs/{RUN_ID}` |
| Stripe | `https://dashboard.stripe.com/{test or live}/...` |

## Catalogue: format
```
Unlocks: Slack alerts for voice health; skipped = failures stay silent.
1. https://my.slack.com/services/new/incoming-webhook/ → pick #voice-health → Add Integration → copy webhook URL
2. Paste it back as SLACK_VOICE_WEBHOOK=https://hooks.slack.com/... and I'll set the secret.
```

## Anti-pattern flags
- "Go to Slack and create a webhook" with no link.
- "Log in to Supabase so I can..." → the correction check blocks it; use the CLI.
- Driving a vendor signup with Playwright.

## Integration with other skills
- `high-level` output style: hand-offs live in Needs you, first on the page.
- `definition-of-done`: an un-handed-off founder step makes the ledger WITH CAVEATS.

## Red flags
| Thought | Reality |
|---|---|
| "I'll walk us through it together" | Founder is faster alone with the link. |
| "The URL is probably /settings/api" | Verify it or say you couldn't. |
| "They can finish the deploy after pasting" | The contract: you finish everything after the paste. |

## Reference
- Always-loaded rule: `cloud-kit/rules/user-handoffs.md`.
