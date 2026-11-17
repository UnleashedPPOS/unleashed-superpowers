# Contradictions resolved (2026-11-16)

Each fact now has one home; anything else that mentions it points there.

| # | Contradiction | Resolution | One home |
|---|---|---|---|
| 1 | `token-discipline.md` had Sonnet as default builder and main chat; memory "Build in Fable" and the founder's 2026-09-26 "Fable stays in the driver's seat" said features go to Fable; the founder's newest HARD RULE (2026-11-16, merged to main during this run) says never Fable for lanes, routines or sub-agents. | The newest founder rule wins: plan in Opus → build in Sonnet (Haiku for mechanical) → review and ship-check in Opus; never Fable for delegated work. The Fable-builder idea is dropped; the memory "Build in Fable" is marked superseded in the rule. Enforced by check `never-fable-subagent` (Agent tool `model`, agent files, routine JSON). | `cloud-kit/rules/token-discipline.md` |
| 2 | `openrouter-deepseek.md` (Mac) allowed a dev-key OpenRouter allowance; `openrouter-os-mobile-only.md` retired it; `llm-provider-chain.md` repeated the chain order. | Merged into one rule: OpenRouter is for the OS mobile app only, with Bedrock → Groq → Anthropic failover. `openrouter-deepseek.md` and `openrouter-os-mobile-only.md` are listed in `cloud-kit/RETIRED`, so `install.sh` moves them out of `~/.claude/rules`. Endpoints, models and quirks moved to skill `llm-provider-chain`. Enforced by check `openrouter-outside-os`. | `cloud-kit/rules/llm-provider-chain.md` |
| 3 | A memory said "ask 2-4 questions"; `working-style.md` says at most one question per turn. | One question per turn wins (newer, repeated by the founder); the rule says it supersedes the memory. Enforced by `multiple-questions-in-reply`. | `cloud-kit/rules/working-style.md` |
| 4 | `user-handoffs.md` said hand-offs go "in chat, not a doc"; the High-Level style puts Needs you on the status page. | Hand-offs go on the page's Needs you with deep links; chat only when there is no page. `credential-handoffs.md` merged in and retired. | `cloud-kit/rules/user-handoffs.md` |
| 5 | `working-style.md` says "merge it yourself"; routine briefs often say "do not merge". | A brief that says do not merge wins. | `cloud-kit/rules/working-style.md` |
| 6 | Where-work-runs measurements (cloud/Netcup/laptop specs, limits) sat in the always-loaded rules and drifted. | Moved to skill `where-work-runs`; the rule keeps a one-line pointer. The monthly prune flags dated measurements older than 45 days. | `skills/where-work-runs/SKILL.md` |

Not resolvable from the cloud: the 76 Mac `feedback-*.md` memories and Mac-only rule files. The monthly prune's
Mac run lists any not yet cited in the registry (`scripts/corrections.py inventory --memory-dir`).
