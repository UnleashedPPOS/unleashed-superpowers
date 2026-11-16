# LLM providers (HARD RULE, 2026-11-11; the one home for OpenRouter and the provider chain)

Founder 2026-11-11: Apple can use the app at any point during review, and "I cannot have them using my app with OpenRouter [dead]". Credit is nearly gone and there is no money to top up.

- OpenRouter is reserved for the live Unleashed OS mobile app and the backend functions it calls. Nothing else: no tests, evals, probes, replays, local dev, scripts, agents, routines or other products, and no dev-key runs (this retires `openrouter-deepseek.md`). The `correction-checks.py` hook blocks OpenRouter calls and keys outside the OS repos ✓.
- Inside the OS app OpenRouter may stay the first hop only while every call fails over instantly to Bedrock → Groq → Anthropic on a refusal, timeout or empty reply, covered by tests. No new OS feature without that fallback.
- Everything else uses the chain AWS Bedrock (OpenAI-compatible) → Groq → Anthropic Haiku, failing over with no gap on any non-2xx, timeout or empty reply. 401/402/403/429 skip to the next provider; a missing key skips that provider. OpenRouter only as an opt-in last hop behind `LLM_ALLOW_OPENROUTER=1`. Groq never gets health or journal content.
- Never Cerebras, Fireworks, DeepSeek direct or Gemini ✓. Never change an embeddings model (stored vectors stop matching): embeddings already on OpenRouter stay there and get reported.
- Pick the cheapest model that passes the job's eval; log provider, model and hop on every call.
- Before adding or changing any LLM call, check which provider it hits. A non-OS caller on OpenRouter: move it off or switch it off, and report it.
- Endpoints, model ids, request quirks, eval-to-switch rules, spend checks and the repo-migration routine: skill `llm-provider-chain`.
