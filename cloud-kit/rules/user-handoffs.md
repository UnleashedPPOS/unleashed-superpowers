# User Hand-offs — make them frictionless

When you reach a step the user has to do themselves (set up something in a third-party UI, click around in a deployed app, etc.), follow these rules:

## 1. Put the hand-off in chat, not a doc

Don't bury the action in a file the user has to open. Inline in the chat reply, terse.

## 2. Always give the direct URL

Every "go do X" line MUST include a clickable URL that opens the exact screen the user needs. Not the homepage. Not "navigate to settings, then…". The deep link itself.

## 3. If you don't know the URL, look it up

Before instructing the user, verify the URL exists and is correct. Use any of:
- `ctx_fetch_and_index` or `firecrawl-scrape` on the vendor's docs
- Project files (vercel.json, .vercel/project.json, package.json)
- Database queries / CLI calls to discover deployed domains
- `firecrawl-search` if the docs URL itself is unknown

If after looking you still can't find an exact URL, say so explicitly: "I couldn't find a direct link — closest is X, then click Y." Don't pretend a guessed URL works.

## 4. Magic URLs to prefer

Some services have legacy/single-page setup flows that bypass app-builder UIs. Use these when they exist:

| Action | Use this, not the modern flow |
|---|---|
| Slack incoming webhook | `https://my.slack.com/services/new/incoming-webhook/` (one page, dropdown channel, click submit, copy URL) |
| Supabase project dashboard | `https://supabase.com/dashboard/project/{REF}` (then specific subpath) |
| Vercel project | `https://vercel.com/{TEAM}/{PROJECT}` |
| GitHub repo Secrets | `https://github.com/{OWNER}/{REPO}/settings/secrets/actions` |
| GitHub Actions workflow run | `https://github.com/{OWNER}/{REPO}/actions/runs/{RUN_ID}` |
| Stripe Dashboard | `https://dashboard.stripe.com/{ENV}/...` (env = test/live) |

When the action is in one of these systems, prefer the deep link.

## 5. Tell the user what they'll see + what to do, one line per step

```
1. https://my.slack.com/services/new/incoming-webhook/ → pick #voice-health → "Add Integration" → copy webhook URL
2. Paste here, I'll set the secret.
```

Not:
```
Go to Slack and create a new incoming webhook for #voice-health…
```

## 6. Verify the URL works by previewing it mentally

If you wrote `https://x.com/admin?tab=voice` but the app uses uncontrolled tabs, the `?tab=voice` is fiction. Read enough of the source to know whether the URL state is real before suggesting it.

## 7. When the user follows the steps, that's the contract

If you said "click here, paste back" — finish the rest yourself once they paste. Don't punt steps back to them after the paste.
