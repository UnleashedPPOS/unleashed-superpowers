---
name: llm-provider-chain
description: "Detail behind the always-loaded LLM provider rule: Bedrock, Groq and Anthropic endpoints, model ids, gpt-oss and Haiku request quirks, cheapest-model eval rule, OpenRouter spend checks and the repo-migration routine. Use when adding, changing or reviewing any LLM call, choosing a model, writing an LLM helper or failover, moving a repo off OpenRouter, checking OpenRouter spend, or when the words Bedrock, Groq, gpt-oss, OpenRouter, provider chain, failover or LLM_ALLOW_OPENROUTER come up. SKIP for embeddings work beyond the 'never change the model' line."
---

# LLM provider chain (detail)

**Announce at start:** "I'm using the llm-provider-chain skill to route this LLM call."

## Thesis
The always-loaded rule (`~/.claude/rules/llm-provider-chain.md`) says WHAT: OpenRouter is for the OS mobile app only, everything else runs Bedrock → Groq → Anthropic. This skill holds HOW: endpoints, ids and quirks that break a hop silently if you forget them. Every fact here was checked live on the date shown; re-check before relying on a stale one.

## When this fires
- Writing or changing any LLM call, helper, failover or provider config.
- Picking or downgrading a model.
- Moving a repo off OpenRouter (the migration routine below).
- Checking OpenRouter spend.

## Mandatory checklist

### Pass 1: route the call
1. Is this the live OS mobile app (or a backend function it calls)? Only then may OpenRouter stay the first hop, and only with the full fallback below, covered by tests.
2. Otherwise use the chain in order, with the shared helper for that language (one per language, no copies).
3. Missing key skips the provider; 401/402/403/429 skip straight to the next; any other non-2xx, timeout, empty reply or `finish_reason: length` fails over. Short connect timeout.

### Pass 2: build the request for each hop
1. **AWS Bedrock (OpenAI-compatible).** `POST https://bedrock-runtime.eu-west-2.amazonaws.com/openai/v1/chat/completions` (second region `us-east-1`), `Authorization: Bearer $BEDROCK_API_KEY`. Plain OpenAI body; never OpenRouter-only fields (`reasoning`, `provider`, `plugins`, `transforms`).
2. **Groq.** `https://api.groq.com/openai/v1/chat/completions`, `Bearer $GROQ_API_KEY`, `openai/gpt-oss-120b` or `openai/gpt-oss-20b`. Free tier, rate-limited. No health or journal content.
3. **Anthropic.** `https://api.anthropic.com/v1/chat/completions`, `Bearer $ANTHROPIC_API_KEY`, `claude-haiku-5-5`. Paid; last resort.
4. OpenRouter only as an opt-in last hop behind `LLM_ALLOW_OPENROUTER=1` (default off).

### Pass 3: prove it
1. Unit tests with mocked HTTP: failover order, the 402 skip, the Haiku field-stripping, and that OpenRouter is not called by default.
2. Log provider, model and hop on every call. A rising share of Haiku or Groq answers means the cheap hop is failing: fix it.

## Catalogue: Bedrock models (checked 2026-11-12)
| Model | Region | Use |
|---|---|---|
| `openai.gpt-oss-120b-1:0` | eu-west-2, us-east-1 | Quality, tool calls, writing, anything user-facing |
| `openai.gpt-oss-20b-1:0` | eu-west-2, us-east-1 | Cheap and fast (~0.5s): bulk, extraction, summaries |
| `mistral.ministral-3-14b-instruct` | us-east-1 only | Classification, tool routing (fastest) |
| `zai.glm-4.7-flash` | us-east-1 only | Classification, routing |
| `us.amazon.nova-2-lite-v1:0` | Converse API | Images (not checked on the OpenAI path; else send images to Anthropic) |

Two endpoints work with the same key: `bedrock-runtime.<region>.amazonaws.com/openai/v1` needs the `-1:0` ids; `bedrock-mantle.<region>.api.aws` (used by unleashedos) takes bare ids (`openai.gpt-oss-120b`). Don't mix them.

## Catalogue: quirks that kill a hop
- gpt-oss on `bedrock-runtime`: always send `"include_reasoning": false` or `content` starts with `<reasoning>…</reasoning>`. Strip a leading `<reasoning>`/`<think>` block defensively anyway. `bedrock-mantle` returns reasoning in a separate field.
- Never send `response_format` to gpt-oss (malformed JSON). Ask for JSON in the prompt, validate, fail over if it doesn't parse.
- gpt-oss reasoning tokens count against `max_tokens` even with `include_reasoning: false`: give JSON jobs ~4,000 (1,800 came back cut off 4 times in 5).
- Haiku 5.5 returns 400 for `temperature`, `top_p`, `response_format: json_object` and `json_schema` without `strict` (verified 2026-11-12). Strip them on the Anthropic hop only, with a test, or the last hop is dead.

## Catalogue: cheapest model that passes (founder 2026-11-12)
- Try in order: gpt-oss-20b (bulk, extraction, summaries) → ministral-3-14b (classification, routing) → gpt-oss-120b (tool calls, writing, user-facing). Haiku is the last hop only.
- Voice commands, 322 cases (2026-11-12): gpt-oss-120b 248, low reasoning 240, ministral-3-14b 235 (twice as fast), glm-4.7-flash 210, qwen3-next-80b 210. Tool-critical stays on gpt-oss-120b.
- Moving a job to a cheaper model: run the repo's eval on both, report both scores, switch only if within 2% (founder can change the margin). No eval means write a small one first.

## Catalogue: OpenRouter spend checks
- Per key: `GET https://openrouter.ai/api/v1/key` (`usage_daily`, `limit_remaining`). Account: `GET /api/v1/credits`. Always via `vault run`, never print the key. These two read-only calls are the only OpenRouter calls the correction check allows outside the OS repos.

## Migration routine (moving a repo off OpenRouter, run as a cloud routine)
1. Read the existing LLM code, callers, tests and docs; extend them into one shared helper per language.
2. No API keys in the cloud: no live calls. Mocked-HTTP tests for failover order, the 402 skip and "OpenRouter not called by default". Run the repo's tests, lint and typecheck.
3. Docs and env examples get names only, never values.
4. ONE PR to the default branch titled `feat(llm): move off OpenRouter to Bedrock, Groq, Anthropic`. Do not merge (this brief overrides the usual merge-it-yourself rule). PR body: every call site moved, env vars the deploy needs, anything left on OpenRouter and why, test counts.
5. Final message: PR link plus open items, under 200 words.

## Anti-pattern flags
- "Just for a quick test, use the OpenRouter key" → blocked; use Bedrock.
- Cerebras, Fireworks, DeepSeek direct, Gemini → out of credit or ruled out; the correction check blocks them.
- Changing an embeddings model → stored vectors stop matching. If embeddings go through OpenRouter, leave them and report it.

## Integration with other skills
- `/learnings` adds new provider corrections to `cloud-kit/hooks/corrections.json`.
- `red-team` should attack the failover: kill each hop in a mocked test.

## Red flags
| Thought | Reality |
|---|---|
| "It's only a dev run, OpenRouter is fine" | Dev-key runs are retired (2026-11-11). Every cent is reserved for App Store review. |
| "Haiku is the safest first hop" | It is the most expensive; last hop only. |
| "The JSON came back cut off, retry" | Raise `max_tokens` headroom and treat `length` as a failover. |

## Reference
- Always-loaded rule: `cloud-kit/rules/llm-provider-chain.md`.
- Inventory: `docs/learning/corrections-inventory.md`.
