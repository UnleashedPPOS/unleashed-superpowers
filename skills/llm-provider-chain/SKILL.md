---
name: llm-provider-chain
description: "Detail behind the always-loaded LLM provider rule: Bedrock, Groq and Anthropic endpoints, model ids, gpt-oss and Haiku request quirks, cheapest-model eval rule, OpenRouter spend checks and the repo-migration routine. Use when adding, changing or reviewing any LLM call, choosing a model, writing an LLM helper or failover, moving a repo off OpenRouter, checking OpenRouter spend, or when the words Bedrock, Groq, gpt-oss, OpenRouter, provider chain, failover or LLM_ALLOW_OPENROUTER come up. SKIP for embeddings work: never change an embeddings model, and embeddings already on OpenRouter stay there and get reported."
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

## Catalogue: eval per repo (enforced by the eval-gate hook)
A commit or PR that changes an LLM prompt or model choice in these repos runs the matching eval first. The PR body then carries one line per eval: `Eval (<name>, offline|live): <score>`. The cloud runs offline. A machine with `vault` also runs live, and live evals never use OpenRouter. If no eval covers the change, the PR says `Eval: none: <why>`, and a small eval gets written (see above).

What counts as a prompt or model change:
- a prompt path (`prompts/`, `*_prompt.py`, `system_prompt`) or an eval's own data;
- an LLM file inside an eval's area, or a file anywhere that builds a system prompt;
- a changed line with a model id, a model assignment or a prompt string, outside tests and docs.

An eval counts as run only when a runner (`npm`, `bun`, `deno`, `pytest`, `uv`, `vault run` and the like) starts the command; naming it in a commit message or a grep does not.

The hook is `cloud-kit/hooks/eval-gate.py`, and its registry is `cloud-kit/hooks/eval-gate.json`. When you edit a row below, update the matching registry entry too; the test checks that the two agree. Off switch, for the founder only: `EVAL_GATE_OFF=1`.

| Repo | Eval | Covers | Offline (cloud) | Live (vault) |
|---|---|---|---|---|
| `unleashed-systems` | owner-context | `owner-context` | `npm run eval:owner-context` | none |
| `unleashed-systems` | inbox-triage (default) | `src/lib/inbox/`, `src/lib/evals/`, `evals/inbox-triage/` | `npm run eval:triage` | `vault run --keys BEDROCK_API_KEY,GROQ_API_KEY,ANTHROPIC_API_KEY -- npm run eval:triage:live` |
| `unleashed-leadgen` | qualify | `prompts/qualify.md`, `evals/golden/qualify/` | `PYTHONPATH=. uv run python -m evals.m3 qualify` | same with `--live`, under `vault run` (Netcup) |
| `unleashed-leadgen` | reply-intent | reply and intent code, `evals/golden/reply_intent*` | `PYTHONPATH=. uv run python -m evals.m3 reply-intent` | same with `--live`, under `vault run` (Netcup) |
| `unleashedos` | owner-memory | `owner-memory` | `deno test -A supabase/functions/_shared/owner-memory/evals_test.ts` | `vault run --keys BEDROCK_API_KEY -- deno run --allow-env --allow-net --allow-read scripts/owner-memory/live-eval.ts` |
| `unleashedos` | voice | `supabase/functions/voice/`, `_shared/voice/` | `deno test -A supabase/functions/voice/evals/` | none |
| `unleashed-os-mobile` | memo | `features/voice/memo/`, `scripts/voice-eval/` | `bun run eval:memo:check` | none (`eval:memo` calls OpenRouter) |
| `unleashed-os-mobile` | voice-transcription | `eval/voice/`, `features/voice/` | `bun run eval:voice:dry` | `bun run eval:voice` |
| `unleashed-os-mobile` | commands | `eval/commands/`, `eval/router/`, `features/brain/`, `features/os/` | `bun run eval:commands:dry && bunx jest eval/commands eval/router` | none (`eval:commands` calls OpenRouter) |
| `unleashed-voice` | prompts (default) | `livekit_agent/`, `voice_core/`, `selflearn/`, `eval/` | `python -m pytest -o addopts="" --no-cov tests/test_corrections.py tests/test_receptionist_eval.py livekit_agent/tests/test_prompt.py livekit_agent/tests/test_persona_prompt.py livekit_agent/tests/test_discovery_prompt.py livekit_agent/tests/test_crisis_prompts.py voice_core/tests/test_system_prompt.py` | none (`sales_line_eval.py` calls OpenRouter) |

These have no eval yet, so their PRs carry `Eval: none` until one is written:
- leadgen outreach drafts (`prompts/draft_*.md`);
- unleashedos narrate-story, stream-agent, personalization and voice-agent prompts;
- mobile prompts outside the areas above.

## Catalogue: OpenRouter spend checks
- Per key: `GET https://openrouter.ai/api/v1/key` (`usage_daily`, `limit_remaining`). Account: `GET /api/v1/credits`. Always via `vault run`, never print the key. These two read-only calls are the only OpenRouter calls the correction check allows outside the OS repos.

## Migration routine (moving a repo off OpenRouter, run as a cloud routine)
- **Goal:** every LLM call in the repo runs Bedrock → Groq → Anthropic through one shared helper per language, extended from the existing LLM code, callers, tests and docs. OpenRouter is not called by default.
- **Constraints:**
  - There are no API keys in the cloud, so make no live calls.
  - Docs and env examples get names only, never values.
  - Do not merge. This brief overrides the usual merge-it-yourself rule.
  - Model policy and sub-agent budget: Sonnet build, at most 2 sub-agents, never Fable.
- **Done when:**
  - Mocked-HTTP tests prove the failover order, the 402 skip and that OpenRouter is not called by default.
  - The repo's tests, lint and typecheck pass.
  - The repo's offline eval (table above) scores within 2% of its pre-migration score.
- **Report:** ONE PR to the default branch, titled `feat(llm): move off OpenRouter to Bedrock, Groq, Anthropic`. The body lists every call site moved, the env vars the deploy needs, anything left on OpenRouter and why, the test counts and the `Eval (...)` line. The final message is the PR link plus open items, under 200 words.

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
