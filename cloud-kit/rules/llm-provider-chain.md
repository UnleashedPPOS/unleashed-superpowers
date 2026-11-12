# LLM provider chain off OpenRouter (HARD RULE, 2026-11-11)

Goes with `openrouter-os-mobile-only.md`. OpenRouter has about $2 left and is reserved for the OS mobile app. Every other repo calls this chain, failing over with no gap on any non-2xx, timeout or empty reply. Checked live 2026-11-11.

## The chain
1. **AWS Bedrock, OpenAI-compatible** (tools and `usage` work). `POST https://bedrock-runtime.eu-west-2.amazonaws.com/openai/v1/chat/completions` (second region `us-east-1`), header `Authorization: Bearer $BEDROCK_API_KEY`. Models:
   - `openai.gpt-oss-120b-1:0`: quality, tool calls, writing.
   - `openai.gpt-oss-20b-1:0`: cheap and fast (about 0.5s), bulk and extraction.
   - `mistral.ministral-3-14b-instruct` and `zai.glm-4.7-flash`: us-east-1 only; classification, tool routing.
   - Images: `us.amazon.nova-2-lite-v1:0` (Converse API; not checked on the OpenAI-compatible path). If that is awkward, send image jobs to Anthropic.
   - Plain OpenAI body. Never send OpenRouter-only fields (`reasoning`, `provider`, `plugins`, `transforms`).
2. **Groq**: `https://api.groq.com/openai/v1/chat/completions`, `Bearer $GROQ_API_KEY`, `openai/gpt-oss-120b` or `openai/gpt-oss-20b`. Free tier, rate-limited. No health or journal content.
3. **Anthropic**: `https://api.anthropic.com/v1/chat/completions`, `Bearer $ANTHROPIC_API_KEY`, `claude-haiku-5-5`. Paid; last resort.

OpenRouter leaves the default chain. Keep it only as an opt-in last hop behind env `LLM_ALLOW_OPENROUTER=1` (default off).

## Cheapest model that passes (founder 2026-11-12: "stick to the cheaper models… still monitoring quality")
- Pick the cheapest Bedrock model that passes the job's eval. Order to try: `openai.gpt-oss-20b-1:0` (bulk, extraction, summaries) → `mistral.ministral-3-14b-instruct` (classification, routing; fastest) → `openai.gpt-oss-120b-1:0` (tool calls, writing, anything user-facing). Claude Haiku is the last hop only, never a first choice.
- Voice commands, 322 cases on Bedrock (2026-11-12): gpt-oss-120b 248, same with low reasoning 240, ministral-3-14b 235 (twice as fast), glm-4.7-flash 210, qwen3-next-80b 210. So tool-critical stays on gpt-oss-120b.
- Moving a job to a cheaper model: run that repo's eval on both, report both scores, and switch only if the cheaper one is within 2% (my default; founder can change it). No eval for the job means write a small one first.
- Log provider, model and which hop answered on every call. A rising share of Haiku or Groq answers means the cheap hop is failing: fix it, don't leave it.
- Two Bedrock endpoints work with the same key: `bedrock-runtime.<region>.amazonaws.com/openai/v1` needs the `-1:0` ids; `bedrock-mantle.<region>.api.aws` (used by unleashedos) takes the bare ids (`openai.gpt-oss-120b`). Don't mix them.

## Behaviour
- A missing key skips that provider. 401 / 402 / 403 / 429 skip straight to the next provider (never stop the chain).
- Short connect timeout so a dead provider fails over fast.
- Never use Cerebras, Fireworks, DeepSeek direct (all out of credit) or Gemini (founder: not an option).
- Never change an embeddings model: stored vectors would stop matching. If embeddings go through OpenRouter, leave them and report it.

## When moving a repo (cloud routine)
- First read the existing LLM code, its callers, tests and docs, and extend them: one shared helper per language, no copies.
- A cloud session has no API keys: make no live calls. Write unit tests with mocked HTTP proving the failover order, the 402 skip, and that OpenRouter is not called by default. Run the repo's existing tests, lint and typecheck.
- Update docs and env examples with names only, never values.
- Open ONE PR to the default branch titled `feat(llm): move off OpenRouter to Bedrock, Groq, Anthropic`. Do not merge. PR body: every call site moved, env vars the deploy needs, anything left on OpenRouter and why, test counts.
- Final message: PR link plus open items, under 200 words.
