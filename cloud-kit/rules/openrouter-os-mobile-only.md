# OpenRouter is for the OS mobile app ONLY (HARD RULE, 2026-11-11)

Founder 2026-11-11: "not let anything be used by OpenRouter unless it is to do with the OS mobile app, because at any point Apple can go and use my app, and I cannot have them using my app with OpenRouter [dead]."

Why: the account had $1.99 left on 2026-11-11 and there is no money to top up. If it hits zero during App Store review, the app's AI features fail in front of Apple.

## The rule
- OpenRouter credit is reserved for the live Unleashed OS mobile app (and the backend functions that app calls). Nothing else.
- NEVER call OpenRouter for: tests, evals, probes, replays, local dev, leadgen, outreach, Factory, Newsroom, Arena, Studio, research, scripts, agents, cloud routines or any new feature outside the OS mobile app. This also retires the dev-key allowance in `openrouter-deepseek.md` for now: no dev-key runs either.
- Everything else uses a non-OpenRouter provider first (see memory `reference-llm-provider-chain` for the current order and keys). Gemini is not an option right now.
- Even inside the OS mobile app, OpenRouter should be the LAST fallback, not the first hop, wherever a free or credit-funded provider can do the job.
- Before adding or changing any LLM call: check which provider it hits. If it is OpenRouter and not the OS mobile app, move it or stop and tell the founder.
- Found a non-OS caller on OpenRouter? Move it off or switch it off, and report it. Don't leave it running.

## Checking spend
- Per key: `GET https://openrouter.ai/api/v1/key` (`usage_daily`, `limit_remaining`). Account: `GET /api/v1/credits`. Always via `vault run`, never print the key.
