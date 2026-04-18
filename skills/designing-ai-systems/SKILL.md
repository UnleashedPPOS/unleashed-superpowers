---
name: designing-ai-systems
description: Use when designing ANY AI system with multiple agents, workers, sub-agents, or coordinated LLM calls. Catches human-team metaphors leaking into architecture, reframes design around AI-native constraints (parallelism, tokens, latency, observability, determinism), and separates the AI-native engine from the anthropomorphic presentation layer. Triggers on phrases like "agentic system," "multi-agent," "AI team," "50 researchers," "research pipeline," "sub-agents," "build a team of AI," "team of agents," "senior reviewer agent," "handoff between agents," or any design discussion for LLM-coordinated systems. Four passes: mine human expertise → design documentation substrate → engine reframe → presentation design. MUST be invoked BEFORE superpowers:brainstorming when the thing being designed is an AI system.
---

# Designing AI Systems (Not Digital Human Teams)

Most people designing AI systems accidentally design **digitised human teams**. The agent roles, seniority framing, calendar estimates, v1/v2 roadmaps — all imported from human team-building — silently delete better architectures from the design space.

**Announce at start:** "I'm using the designing-ai-systems skill to [reframe / audit / design] this."

## Four principles

1. **Don't anthropomorphize the STRUCTURE.** No team-of-agents architecture. Use AI-native patterns (blackboard, DAG, ensemble, queue, sub-agent spawn).
2. **DO absorb human expertise as CONTENT.** Mine what humans know — especially their mistakes — and encode as critic rules, validation schemas, few-shot examples, retrieval sources.
3. **Documentation is executable.** SOPs, runbooks, and lessons-learned files are the persistent form of human expertise. The AI reads them at runtime, is tested against them, and proposes updates.
4. **Parallelism is the default.** Sequential is the exception that must justify itself. AI systems can run 10, 50, 500 concurrent workers; human teams cannot.

**Thesis:** *Anthropomorphic surface, AI-native engine, event-log bridge. Humans as content. Documentation as fuel. Parallelism as default.*

## When this fires

Invoke this skill when any of these are true:
- User or you are designing a system with multiple agents, workers, or coordinated LLM calls
- User drafts a design with sequential handoffs between named agents
- User estimates AI-system work in "weeks" or "sprints"
- User uses seniority metaphors ("senior agent reviews," "editor signs off")
- User maps an org chart into an agent chart
- User says any of the anti-pattern trigger phrases below

## Mandatory checklist

Create a TodoWrite todo for each pass; complete in order. Do NOT skip passes. The skill runs ALL FOUR even when the user only asked about one.

### Pass 0 — Mine human domain expertise

For each role the AI will occupy, gather and document:

1. **What do experienced humans in this role know?** (Core competencies, standard practices)
2. **What mistakes do newcomers make?** (Common failure modes)
3. **What edge cases have seasoned practitioners seen?** (The rare but real)
4. **What hard rules have they learned?** ("Never do X because Y" — war stories)
5. **What vocabulary is load-bearing?** (Domain terms the agent must use correctly)
6. **What documents would a human consult before acting?** (Manuals, runbooks, SOPs, reference guides)

**Output:** structured list of expertise artefacts per role.

**Mechanisation:** if Project C (the "instant level-up" research pipeline, planned at `.claude/plans/jazzy-finding-coral.md`) is available, invoke it to mechanise this pass. Otherwise gather manually (interviews, forum mining, YouTube, books, industry publications).

### Pass 0.5 — Design the documentation substrate

For each role, decide:

1. **Which of the nine documentation types does this role need?**
   - SOP — step-by-step procedures
   - Runbook — incident / edge-case handling
   - Playbook — strategic decision trees
   - Lessons-learned — captured mistakes
   - Glossary — shared vocabulary
   - System prompt — role / personality definition
   - Few-shot bank — good/bad examples
   - Eval harness — testable criteria derived from the SOP
   - Decision log (ADR) — why-we-chose-this
2. **Canonical SOP shape** (steps, inputs, outputs, failure modes).
3. **Versioning and review process** (who approves, how often).
4. **Closed-loop update mechanism** — how the AI proposes changes, who reviews, how changes ship.
5. **Presentation rendering** — how users see the SOP the AI is following.

**Output:** documentation plan per role. Every artefact becomes both engine input AND presentation artefact.

### Pass 1 — Engine reframe

1. **Detect human-team framing.** Scan the draft architecture for the anti-pattern trigger phrases below.
2. **Rewrite constraints.** Replace headcount/calendar/seniority with tokens/latency/observability/determinism/cost/parallelism.
3. **Flip the parallelism default.** Every "A then B" is suspect — demand a sequentiality justification. Default to parallel.
4. **Propose AI-native candidates.** Pick from the engine pattern catalogue (blackboard / pipeline / DAG / ensemble / self-queue / critic-loop / pub-sub / sub-agent spawn).
5. **Stress-test** against AI-native failure modes: token overrun, latency fanout, non-determinism, eval gap, hallucination cascade, cost blow-up, runaway spawn depth.
6. **Weekend-prototype forcing function** — if the human-team estimate was weeks, demand: *what's the 48-hour AI-native version?*

**Output:** engine architecture with pattern choices justified.

### Pass 2 — Presentation design

1. **Take the engine architecture** as input.
2. **Design the user-facing agency view** on top (50 tiles, named personas, event feed, Gantt).
3. **Name personas, design tiles, specify the event feed.** Be generous with anthropomorphism here — it is the correct cognitive shortcut for users.
4. **Define the bridge** — how each presentation event maps to an engine event.
5. **Verify audit drill-down** — every UI claim must be clickable to the raw engine event that produced it.
6. **Include SOP visibility** — users must be able to see and review the documentation the AI is following, plus an inbox for AI-proposed updates.

**Output:** presentation spec with bridge mappings.

## Top-of-invocation mantra

> "Humans as content. Documentation as fuel. Parallelism as default. Anthropomorphic surface, AI-native engine, event-log bridge."

## Engine pattern catalogue

Pick from these; don't invent new patterns without justification.

- **Blackboard** — shared state, opportunistic workers. For tasks with unpredictable partial results.
- **DAG** — explicit dependencies, parallel where independent. For known task graphs.
- **Self-assigning queue** — uniform independent tasks pulled by workers.
- **Ensemble + consensus** — same call N times, voted or clustered. For safety-critical or low-tolerance outputs.
- **Critic loop** — worker writes, critic evaluates, iterate. For quality-over-speed work.
- **Sub-agent spawn / recurse** — agent spawns its own sub-agents for sub-problems. For irregular tree depth.
- **Pub-sub** — workers subscribe to event types. For reactive decentralised coordination.
- **Pipeline (A→B→C)** — sequential. Use ONLY when each stage's output IS the next stage's input AND parallelism is impossible. Most "pipelines" are actually DAGs.

## Presentation pattern catalogue

- **Named agent tiles** — persistent UI elements representing logical roles, subscribing to engine events.
- **Live event feed** — chronological anthropomorphic projection of the event log.
- **Progress indicators** — per-tile + aggregate, derived from event counts.
- **Team timelines / Gantt** — high-level temporal views.
- **Audit trail per artefact** — named contributors and reviewers, every claim traceable.
- **Progressive disclosure** — agency view by default; engine event log one click away.
- **Agency-level metrics** — "research hours," "sources reviewed" — event counts in human language.
- **SOP viewer** — users read the exact procedure the AI follows.
- **Proposed-updates inbox** — AI-suggested SOP/runbook changes awaiting human approval.

## Anti-pattern flags (architecture context only)

If the design uses these in ARCHITECTURE context, reframe immediately:

- "team of 50 [agents/researchers/workers]"
- "senior [agent/reviewer] signs off"
- "hand-off between agents"
- "agent X reports to agent Y"
- "2-3 weeks" / "sprint to ship"
- "v1 / v2 roadmap"
- "meeting point" / "sync" between agents
- "onboarding" an agent
- "training" an agent in the workflow sense
- "manager agent"
- "A then B" without a justification for sequentiality

In **PRESENTATION context** these are fine or preferable — that is the cognitively cheap framing users want.

## Where human-team framing IS correct

Don't be dogmatic. Keep the human frame at:

- Human-AI boundary (UX, onboarding, support flows)
- Audit / regulation (regulators think in named roles)
- Billing / attribution (cost accounting per agent)
- Hard sequential gates (legal, compliance — parallelism forbidden)
- Accountability (a named entity owning each output)
- The entire presentation layer (cognitive cheapness for users is a feature)

## Integration with other skills

- **Pre-flight before `superpowers:brainstorming`** when designing an AI system. Invoke this skill FIRST; it sets the four-principle frame that brainstorming then operates within.
- **Checkpoint inside `superpowers:writing-plans`** — when reviewing a plan for an AI system, verify it separates engine from presentation, encodes Pass 0, designs documentation substrate, defaults to parallel.
- **Slash command `/ai-native-reframe`** for mid-session audit of an existing design without running the full skill.

## Red flags

These thoughts mean STOP — you're rationalising:

| Thought | Reality |
|---|---|
| "It's just a pipeline, no reframe needed" | Most "pipelines" are DAGs with hidden parallelism. Check. |
| "The dashboard can come later" | Designing without Pass 2 means you do not know the event-log shape. Design both layers together. |
| "We'll optimise tokens in v2" | Parallelism is architectural, not optimisation. Decide now. |
| "Just use CrewAI / AutoGen" | These frameworks encode the anthropomorphic trap. Using them is not doing the design work. |
| "The agents will figure out coordination" | They will not. Coordination must be explicit — on a blackboard, in a DAG, or through events. |
| "Pass 0 is optional, we know the domain" | You know the domain FROM THE OUTSIDE. Pass 0 captures what insiders forget you do not know. |
| "SOPs are overhead" | In AI systems, the SOP IS the prompt. Skipping it means your agent is undocumented code. |

## Reference

Full design spec with cognitive-science grounding, prior art, and worked examples: `docs/superpowers/specs/2026-04-18-two-layer-ai-native-design.md`.
