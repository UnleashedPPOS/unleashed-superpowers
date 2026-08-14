---
description: Audit the current AI system design for human-team metaphor leakage and produce an engine/presentation/bridge split with parallelism-first defaults.
---

Audit the current AI-system design using the two-layer pattern. Run through four passes in order. Produce structured output.

## Pass 0 — Human expertise check

List every role/agent in the current design. For each, answer:
- What expertise did we mine about this role? What mistakes? What hard rules?
- If anything is missing, flag as a GAP.

## Pass 0.5 — Documentation check

List every SOP / runbook / eval harness / lessons-learned artefact referenced in the current design.
- Missing anywhere? Flag as a GAP.
- Is there a closed-loop update mechanism (AI proposes updates, human approves)? If not, design one.

## Pass 1 — Engine reframe

1. Enumerate every "agent," "role," "worker," "team," "specialist" mentioned. For each, decide:
   - **ARCHITECTURE (engine layer)** — must be reframed as an AI-native pattern
   - **SURFACE (presentation layer)** — keep anthropomorphic; confirm it is a view over engine events
2. List assumed constraints. Flag any human-team leakage (headcount, calendar, seniority, onboarding, meetings). Rewrite as AI-native (tokens, latency, observability, determinism, cost, parallelism, eval cadence).
3. Apply the parallelism default — every "A then B" gets challenged: *why is this not parallel?* Demand a sequential justification or flip to parallel.
4. For each architecture "agent," propose the AI-native replacement: blackboard, priority queue, ensemble, DAG, critic-loop, sub-agent spawn, pub-sub.
5. Stress-test the revised architecture against AI failure modes: token overrun, latency fanout, non-determinism, eval gap, hallucination cascade, cost blow-up, runaway spawn depth.

## Pass 2 — Presentation design

1. For each surface "agent," specify which engine events populate it.
2. Specify the drill-down path (UI claim → engine event).
3. Specify SOP viewer + proposed-updates inbox.

## Output format

Produce the revised design with these sections clearly separated:

### ENGINE
[AI-native architecture with pattern choices justified]

### PRESENTATION
[Anthropomorphic surface with tile roster and event feed]

### BRIDGE
[Event mappings + drill-down paths]

### GAPS
[What Pass 0 (expertise) and Pass 0.5 (documentation) are missing]

### 48-HOUR PROTOTYPE
If the original human-team estimate was in weeks, describe the 48-hour AI-native version.

---

Reference: `docs/specs/2026-04-18-two-layer-ai-native-design.md`
