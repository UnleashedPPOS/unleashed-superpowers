# Two-Layer AI-Native Design

## A universal pattern for designing AI systems — anthropomorphic surface, AI-native engine, event-log bridge, documentation-driven, human-content-rich, parallelism-first

**Status:** Design spec v2 (2026-04-18)
**Origin:** Synthesised from a 2026-04-18 brainstorm about Project C (the "instant level-up" research pipeline from the 2026-04-17 agent-build-backlog brainstorm) and a prior conversation where the user caught themselves using human-team metaphors ("researchers as roles → v1 dashboard pushed to v2 because engineering → 2-3 week estimates") while designing a multi-agent system.
**Implements-next:** `~/.claude/skills/designing-ai-systems/SKILL.md`, `~/.claude/commands/ai-native-reframe.md`.

---

## TL;DR

Most people designing AI systems accidentally design **digitised human teams** instead. The agent roles, the seniority framing, the calendar-based estimates, the v1/v2 roadmaps — all imported from human team-building — silently delete better architectures from the design space.

The fix rests on **four principles**:

1. **Don't anthropomorphize the STRUCTURE.** No team-of-agents architecture. Use AI-native patterns (blackboard, DAG, ensemble, queue, sub-agent spawn).
2. **DO absorb human expertise as CONTENT.** Mine what humans know — especially their mistakes — and encode it as critic rules, validation schemas, few-shot examples, and retrieval sources.
3. **Documentation is executable.** SOPs, runbooks, and lessons-learned files are the persistent form of human expertise. The AI reads them at runtime, is tested against them, and proposes updates back to them.
4. **Parallelism is the default.** Sequential is the exception that must justify itself. AI systems can run 10, 50, 500 concurrent workers; human teams cannot.

The engine layer applies all four. The presentation layer stays anthropomorphic (50 named researcher tiles, personas, dashboards, audit trails) because anthropomorphism is cognitively cheap for users — and that cheapness is a feature. Engine and presentation are bridged by an **event log** — every engine write becomes a presentation event.

**Design thesis:** *Anthropomorphic surface, AI-native engine, event-log bridge.*
**Guiding principles:** *Humans as content, not structure. Documentation as fuel. Parallelism as default.*

---

## The core insight

### The cognitive mechanics

Humans have specialised neural hardware for modelling other minds — mirror neurons, mentalising circuits, theory of mind. Predicting what another agent will do is ancient, fast, automatic. Your brain runs it in parallel with almost no effort.

Systems thinking — holding multiple variables in mind simultaneously, tracing feedback loops, reasoning about parallel state — has no evolved shortcut. It engages working memory directly, and working memory is tiny (~7±2 items). The moment you reason about more than a handful of tightly coupled variables, you hit a hard wall.

So when your brain encounters "design a multi-agent system," it does the rational thing: **it repurposes the faster machinery (mind-reading) to approximate the harder problem (system design).** You slot "agents" into the theory-of-mind simulator and reason through the system as a team.

This isn't laziness. It's brain architecture doing what it was built for. Kids animate the weather. Engineers blame "the computer" for being slow. Product managers reach for personas before flows. Even when you KNOW the system isn't a team, the anthropomorphism still fires automatically. Naming something an "agent" loads the social simulator.

### Why the leak happens (five reinforcing forces)

1. **Vendors and frameworks speak team-language.** "Agents," "researchers," "assistants," "coworkers," "crew," "autogen." The naming IS the trap.
2. **Every knowledge worker's career trained them in team metaphors.** Decades of practice reaching for "who does what."
3. **Project tooling encodes team structure.** Jira tickets, OKRs, v1/v2 roadmaps, sprint planning — calendrical and role-based by construction.
4. **Anthropomorphism is cognitively cheaper** than systems thinking (see above).
5. **AI startups LARP as normal SaaS startups** — teams, sprints, seniority ladders, head-count-based effort estimates. This infects how they design their own AI.

### What the leak produces

Concrete failure modes observed in real design sessions:

- **Role casting** — "we need a researcher agent, a writer agent, an editor agent" → sequential handoff pipeline → idle seats, rigid ordering, one breakage blocks everything.
- **Calendar estimates** — "2-3 weeks" based on how long a human team would take → completely disconnected from actual AI-system cost (tokens × eval-loop-turns).
- **Seniority metaphors** — "senior reviewer agent signs off" → single-model critic with no ensemble, no consensus, no confidence scoring.
- **v1/v2 roadmap sequencing** — "dashboard pushed to v2 because engineering is busy with v1" → false scarcity; in an AI system, many things can ship in parallel behind feature flags.
- **Meeting-based coordination** — "we need a sync point where agent A tells agent B" → direct messaging between agents → tight coupling, hidden state, no replay.
- **Communication bandwidth at human speed** — design assumes words-per-minute rather than tokens-per-second.
- **Blindness to parallelism** — the design contains "A then B then C" where B could run alongside A. Human teams cannot see this because their experience has never had it.

Each of these blocks a better architecture. Remove the human frame, and the better architecture just falls out.

### The missing affordance: parallelism

Human teams have a hard cap on parallelism — headcount. You can have 5, maybe 50 people on a problem, and past a certain point coordination overhead (Brooks' Law) means adding more makes the system slower, not faster.

AI systems have no such cap. You can have 10, 50, 500, 5,000 concurrent workers on a single query, with sub-agents spawning their own sub-agents. The ceiling is rate limits and cost, not architecture or coordination.

**Consequence for design:** in AI-system design, **parallelism is the default. Sequential is the exception that must justify itself.** Every time you write "A then B then C," ask: *why isn't this A and B in parallel, then C?* Human teams reason "how can I parallelise this?" AI systems reason "why shouldn't this be parallel?"

This affordance doesn't just scale throughput. It unlocks architectures human teams can't build:

- **N parallel workers on the same task with consensus** — drop false-negatives without extra human effort
- **Fanout-fanin** — one question explodes into 50 sub-queries, then collapses into a single answer
- **Speculative execution** — try 3 approaches in parallel, pick the best retroactively
- **Deep sub-agent spawning** — each agent can spawn its own sub-agents to recurse into sub-problems
- **Ensemble-of-ensembles** — critical decisions run through multiple consensus layers

When you see a human-team design where a "specialist" is waiting for another "specialist" to finish, you're looking at an architecture that can't see parallelism. Fix it.

---

## The two-layer pattern

### Layer 1 — Engine (AI-native internals)

**Optimised for:** tokens (cost-per-call), latency (ms-to-seconds), observability (replay, audit, debug), determinism (reproducibility, test), eval loop (measurable quality), cost-per-query (unit economics), **parallelism** (concurrency ceiling, spawn depth, fanout factor).

**Concurrency-specific constraints:**
- **Concurrency ceiling** — how many workers can run in parallel (bounded by rate limits + cost, not architecture)
- **Spawn depth** — how many levels of sub-agent recursion are allowed before the system must consolidate
- **Fanout factor** — how wide a single task can explode (e.g. one question → 50 sub-queries)

**Common components:**
- **Blackboard** — a shared data structure where partial answers accumulate
- **Self-assigning worker pool** — N identical workers, differentiated by prompt at pickup
- **Priority queue** — tasks sitting until a worker grabs them
- **DAG** — directed acyclic graph of dependencies, with parallel fanout wherever independent
- **Ensemble + consensus** — same call run N times, clustered or voted
- **Critic model** — evaluates partial results, decides saturation
- **Event log** — every state change recorded for replay
- **Feature flags + shadow mode** — new engine components run dark until evals confirm
- **Sub-agent spawn / recurse** — agents that can spawn their own sub-agents to recurse into sub-problems

### Layer 2 — Presentation (anthropomorphic surface)

**Optimised for:** human trust (the system feels real), legibility (a person can follow what's happening), oversight (regulators and auditors can verify), marketing (the product is sellable), accountability (a named entity owns each output).

Common components:
- **Named agent tiles** — "Senior Researcher," "Fact Checker," "Editor-in-Chief"
- **Live event feed** — "Analyst 7 found pattern X at 14:32"
- **Progress indicators** — per-agent and aggregate
- **Team timelines / Gantt views** — phased project layouts
- **Audit trail per artefact** — "Contributed by Analysts 4, 12, 17; reviewed by Editor"
- **Agency-level metrics** — "Research hours," "Sources reviewed," "Patterns extracted"
- **SOP viewer** — users can read the exact procedure the AI is following
- **Proposed-updates inbox** — AI-suggested SOP or runbook changes for human review

The presentation layer leans INTO anthropomorphism deliberately. Cheap cognition is a feature for users, not a bug. What we reject is cheap cognition in the architecture.

### The bridge (event log)

Every presentation-layer agent is a **view slot** populated from engine-layer events:

| Presentation event | Engine event |
|---|---|
| "Agent 23 is reading paper X" | `worker picked task_id=X from queue at T` |
| "Senior Editor reviewed this" | `critic model threshold-passed output Y` |
| "Research team synthesised findings" | `composer consumed blackboard entries A,B,C,D` |
| "Fact-checker flagged a conflict" | `contradiction-checker wrote conflict record to board` |

Physically, the engine might have 5 worker processes cycling through 50 logical tasks. The UI shows 50 tiles because 50 tiles is what makes the work legible. Both are real — and because every presentation claim maps 1:1 to an engine event, any user can drill down from UI to engine and audit what actually happened.

This separation is also what lets you **rearchitect independently.** Swap blackboard for DAG? The presentation layer doesn't care. Redesign the dashboard? The engine doesn't care. The bridge is the contract.

---

## Humans as content, not structure

The reframe has a second half that's easy to miss: **don't anthropomorphize the architecture, but DO absorb human expertise as raw material.** Human knowledge is the single most valuable input to an AI system — but it has to enter the system as content the AI consumes, not as a template the AI imitates.

For a domain like admin work, medical triage, legal review, customer support, or research:

- **Mistakes humans commonly make** → **critic checks** the AI runs against its own output ("did the AI forget the thing admins always forget?")
- **Steps humans tend to skip** → **validation schemas** that require those fields
- **Hard-won constraints** ("never send an invoice before the PO is confirmed") → **prompt hardening** and **guardrails**
- **Edge cases humans have encountered** → **few-shot examples** in the prompt or retrieval corpus
- **Industry vocabulary and conventions** → **glossary** the agent queries
- **War stories and post-mortems** → **lessons-learned** documents the agent retrieves before acting

The best AI systems don't replace human expertise — they absorb it, at scale, and apply it consistently in ways no single human could.

### The false dichotomy

"AI vs humans" is the wrong frame. The right frame is **"how do we extract everything a human knows about this domain — including what they've learned the hard way — and make it part of the system?"** The human's job shifts from *doing the work* to *teaching the system to do the work and reviewing its output.*

### Pass 0 in the skill

Before any engine design begins, the skill's **Pass 0** is: **mine human domain expertise.** For each role the AI will occupy, answer:

1. What do experienced humans in this role know?
2. What mistakes do newcomers make?
3. What edge cases have seasoned practitioners seen?
4. What hard rules have they learned? ("Never do X because Y.")
5. What vocabulary is load-bearing?
6. What documents would a human consult before acting?

Each answer becomes a specific artefact in the engine: critic rule, validation field, prompt clause, few-shot example, retrieval source. No expertise is wasted. No mistake has to be re-learned.

### Connection to Project C

Project C (the "instant level-up" research pipeline) **is the mechanised version of Pass 0.** Once Project C is shipped, every subsequent AI-system design you do gets a fully-automated Pass 0: point it at "admin work" and out comes a mined corpus of expertise, mistakes, constraints, edge cases, and vocabulary — ready to encode. The skill tells you what to gather; Project C is the tool that gathers it for you.

---

## Documentation as executable substrate

In human systems, documentation is overhead — usually outdated, rarely read. **In AI systems, documentation is directly executed.** The SOP IS the prompt. The runbook IS the decision tree. The lessons file IS the guardrail.

This inversion changes everything. Documentation flips from cost centre to fuel. The better an organisation documents, the better its AI performs. And critically — AI can close the documentation-reality gap automatically, observing what actually happens vs what's written, and proposing updates. Humans never could do that at scale.

### Types of documentation that matter (nine, all first-class)

- **SOPs (Standard Operating Procedures)** — step-by-step procedures the agent follows
- **Runbooks** — incident and edge-case handling
- **Playbooks** — strategic decision trees for ambiguous situations
- **Lessons-learned** — captured mistakes (like this project's `tasks/lessons.md`)
- **Glossaries / ontologies** — shared vocabulary between user, agent, and systems
- **System prompts** — role and personality definitions
- **Few-shot banks** — good/bad examples the agent retrieves before acting
- **Eval harnesses** — testable criteria derived directly from the SOP
- **Decision logs (ADRs)** — why we chose this approach, so the agent doesn't re-litigate

All nine are really one substance: **persistent, version-controlled, AI-readable expertise.** The SOP is the canonical form; the others are specialisations.

### The closed loop

The most powerful property of AI-native documentation is that it self-improves:

```
AI executes SOP → observes gap or edge case → proposes SOP update
       ↑                                              ↓
       └────── human reviews and approves ──────────┘
```

Every execution is a potential improvement. Every approved improvement compounds. Over time the SOP — and the AI that runs it — becomes insanely sharp, because it has absorbed every edge case anyone has ever hit.

`tasks/lessons.md` in this very project already works exactly this way. Every correction becomes a rule. The rule prevents the mistake. The AI sharpens. Scale the pattern to every AI system.

### How documentation sits in the two-layer design

SOPs are the **persistent bridge between Pass 0 and ongoing operation:**

- **Pass 0** gathers human expertise (the raw material)
- **SOPs encode it** in persistent, version-controlled form
- **Engine reads SOPs** at runtime (they become prompts and retrieval sources)
- **Presentation shows SOPs** to users ("here's exactly what the AI is following")
- **Feedback loop updates SOPs** (AI proposes, human approves)

On the presentation layer this becomes marketable UX:

- Users READ the SOP the AI is following
- Users REVIEW proposed updates ("the AI wants to add step 4 because it saw X")
- Audit trail shows "AI followed SOP v2.3, sections 4 and 7"
- The SOP itself becomes the product artefact ("our AI follows the same proven playbook every time")

### Pass 0.5 in the skill

After Pass 0 gathers expertise and before Pass 1 designs the engine: **design the documentation substrate.** For each role the AI will occupy:

1. Which of the nine documentation types does this role need?
2. What's the canonical SOP shape for this task? (Steps, inputs, outputs, failure modes.)
3. How is the SOP versioned and reviewed?
4. What closed-loop mechanism proposes updates?
5. How does the presentation layer render the SOP for users?

Every artefact here becomes an engine input AND a presentation artefact.

---

## Background: what a blackboard is

The pattern that most often falls out when you reframe a human-team design AI-native, and the least familiar to most builders.

### The metaphor

Imagine a room with one big blackboard on the wall and a bunch of specialists standing around it. Nobody is assigned tasks. Nobody reports to anyone. Everyone reads the board continuously. Anyone who spots something they can contribute to walks up, writes on the board, and steps back. Work accumulates on the board until a controller decides it's done.

### The mechanism

Three pieces:
1. **The board** — one shared data structure holding partial answers, hypotheses, evidence, open questions.
2. **Workers** (called "knowledge sources" in the classical literature) — narrow specialists who scan the board, act when they can contribute, post updates.
3. **A controller** — decides "done enough" or prioritises pending contributions if compute is limited.

Workers never communicate directly. Everything flows through the board.

### Worked example (Project C)

Board starts with: `Question: "What are the best patterns for building a YouTube-expert research pipeline?"`

Workers in parallel:
- **Searcher** → `"Found 12 relevant videos: [urls]"`
- **Transcriber** → `"Transcribed video 1: [text]"`
- **Chunker** → `"Chunked video 1 into 34 passages"`
- **Pattern-extractor** → `"Found pattern: timestamps as chunk boundaries"`
- **Contradiction-checker** → `"Conflict between pattern A and B"`
- **Synthesiser** → `"Consolidated answer: [section]"`
- **Critic** → `"Confidence 0.87. Gaps: no rate-limit coverage"`
- **Searcher** (re-fires) → goes looking for rate-limit content

When the critic says "confidence high, no gaps," the controller declares done and the composer writes the final spec.

### Why it fits AI

1. **Parallel by default** — N workers all read the board simultaneously, each firing when they can.
2. **State is explicit** — everything useful is on the board, not hidden in conversation history. Replay, debug, audit are free.
3. **Resilient** — if one worker fails, another with overlapping capability can still contribute.
4. **Opportunistic** — workers don't need a pre-made plan. They react to emerging partial state. Research IS like this.
5. **Composable** — new capability = new worker watching for a new pattern. No rewiring.

Everyday analogue: a Trello board where the entire team watches continuously and every card auto-updates in milliseconds.

---

## The constraint shift

| Human-team constraint | AI-native engine constraint |
|---|---|
| Headcount | Tokens / cost-per-call |
| Calendar (weeks) | Latency (ms — seconds) |
| Seniority / trust | Capability scoping + output validation |
| Onboarding time | System prompt + RAG + few-shot |
| Meeting fatigue / morale | Rate limits, model capability ceiling |
| Communication overhead (Brooks' Law) | Context-window bandwidth |
| Coordination cap (~5–10 people) | **Unbounded parallelism**: 10 / 50 / 500+ concurrent workers, recursive sub-agent spawning |
| Timezone / geography | Model region / availability |
| Annual performance review | Continuous eval harness |
| Escalation chain | Confidence threshold → bigger model |
| Politics / credit / promotion | Non-issue — delete from design |
| Tribal knowledge (in someone's head) | Documentation (SOP, runbook, lessons) — persistent, versioned, queryable |
| Documentation as overhead, often stale | Documentation as executable fuel, continuously refreshed by closed loop |

This table applies to the **engine layer only.** The presentation layer can and should continue using human constraints as its native language — that's what users understand.

---

## Pattern swaps (three columns)

| Human framing (wrong in architecture) | AI-native engine | Anthropomorphic surface |
|---|---|---|
| "Team of 50 researchers, each assigned a beat" | Blackboard + self-assigning worker pool + sub-agent spawn | 50 researcher tiles with live activity |
| "Manager assigns work" | Priority queue | "Task Coordinator" tile with assignment log |
| "Meetings / standups" | Event log + pub-sub | "Daily Sync" timeline view |
| "Senior reviewer signs off" | Ensemble + consensus / critic model | "Senior Editor" agent with review transcript |
| "Hand-off between people" | Schema-typed context hand-off | Animated baton-pass: "Researcher 7 → Analyst 2" |
| "Knowledge in someone's head" | Vector DB + graph memory + SOPs/runbooks | Browsable "Team Knowledge Base" + SOP viewer |
| "v1 before v2 because scope" | Feature flags + shadow mode | Hidden — this is delivery infra |
| "Sequential workflow" | DAG with parallel fanout-fanin | "Project Timeline" Gantt view |
| Code review by humans | Multi-agent split-role review | "Review Panel" with named reviewers |
| Training / onboarding | System prompt + few-shot + RAG + SOP | Hidden — this is setup |
| "Update the training" | Closed-loop SOP updates reviewed by humans | "Proposed-updates inbox" |

---

## Engine pattern catalogue

**Blackboard** — shared state, opportunistic workers. Use when tasks depend on partial results from other tasks AND the order of operations can't be pre-planned. (Research pipelines, complex synthesis.)

**DAG (directed acyclic graph)** — explicit dependencies, parallel where independent. Use when task dependencies ARE pre-known and each task has a deterministic input/output shape. (ETL, build pipelines.)

**Self-assigning queue** — tasks sit in a queue, workers pull next one. Use when tasks are uniform and independent. (Bulk embedding, bulk classification.)

**Ensemble + consensus** — same call, N times, clustered or voted. Use when you need diversity of analysis or low false-negative rates on critical decisions. (Safety-critical output, synthesis validation.)

**Critic loop** — worker writes, critic evaluates, iterate. Use when quality matters more than first-pass speed and quality is measurable. (Spec generation, code output.)

**Sub-agent spawn / recurse** — an agent can spawn its own sub-agents to decompose a sub-problem, then consolidate results. Use when problems have irregular tree depth. (Research into unknown territory, multi-step reasoning.)

**Pub-sub** — workers subscribe to event types, react independently. Use when coordination patterns shouldn't be centralised. (Reactive workflows.)

**Pipeline (A→B→C)** — sequential stages. Use when each stage's output is the next stage's input AND no parallelism is possible. Usually a sign to rethink — most "pipelines" are actually DAGs.

---

## Presentation pattern catalogue

**Named agent tiles** — persistent UI elements representing logical roles ("Senior Researcher," "Fact Checker"). Each tile subscribes to a stream of events from the engine and renders them as agent-level activity.

**Live event feed** — chronological stream of "Agent X did Y at T." Direct projection of the engine's event log with anthropomorphic framing.

**Progress indicators** — per-tile progress bars and aggregate completion. Derived from engine event counts and critic confidence.

**Team timelines (Gantt, phase bars)** — high-level temporal view of the project. Useful for non-technical stakeholders.

**Audit trail per artefact** — for each output, "produced by X, reviewed by Y, validated by Z." Direct trace to engine events.

**Progressive disclosure** — by default, show the agency view; let technical users drill into the event log. Bret Victor–style ladder from concrete (tiles) to abstract (engine log).

**Agency-level metrics** — "Research hours," "Sources reviewed," "Patterns extracted." These are engine-event counts framed in human terms.

**SOP viewer** — renders the exact documentation the AI is following, with section-level linking. Users click through to see "here's the procedure, here's the evidence the agent executed it correctly."

**Proposed-updates inbox** — closed-loop UI: the AI observes a gap or edge case during execution and drafts an SOP update. Human reviewer approves, rejects, or edits. Approved updates ship with a version bump and immediately sharpen future executions.

---

## Applied to Project C

### Pass 0 — human expertise mined
For "build a YouTube-expert research pipeline" specifically:
- Mine what experienced researchers know about extracting usable patterns from unstructured video content
- Mistakes novices make (missing context, over-extraction, source conflation, ignoring chapter boundaries)
- Hard-won constraints (chunk on semantic boundaries not time; always keep source attribution; never extract without the surrounding context window)
- Edge cases (multi-speaker videos, math-heavy lectures, non-English sources, low-quality transcripts)

### Pass 0.5 — documentation encoded
- **SOP** — "how to extract a pattern from a chunked transcript" (steps, required fields, failure modes)
- **Runbook** — "what to do when two sources contradict" (decision tree)
- **Glossary** — YouTube-specific vocabulary (chapter / Shorts / auto-caption-vs-transcript / creator-vs-channel)
- **Few-shot bank** — curated good/bad extraction examples
- **Eval harness** — "does extraction preserve source, context, and claim strength?"
- **Lessons-learned** — empty at v1; populated by the closed loop as the system runs

### Engine
1. **Ingestion DAG** — URL/query fanout → parallel transcription → chunking → embedding.
2. **Pattern-extraction ensemble** — same query run with N framings; clustered.
3. **Blackboard** — typed partial answers (claim, evidence, confidence, source).
4. **Critic model** — reads blackboard against the eval harness; decides saturation.
5. **Composer** — folds entries into target spec format, following the SOP.
6. **Eval harness** — continuous spec-quality delta vs baseline, derived from Pass 0.5 criteria.
7. **Worker pool** — N identical workers; start N=5, scale empirically. Workers spawn sub-agents when a chunk contains multiple distinct claims (spawn depth 2).
8. **Self-improvement loop** — when critic detects recurring gap, proposes SOP/runbook update for human review.

### Presentation
1. **"Research Team" dashboard** — 50 researcher tiles, each showing current source, progress, last finding.
2. **"Senior Analysts" row** — 3–5 higher-order tiles running pattern extraction.
3. **"Editor-in-Chief" tile** — the critic, with confidence meter.
4. **"Composer" tile** — synthesis agent, shown "writing" the spec.
5. **Live event feed** — chronological agent activity.
6. **Audit trail per spec section** — contributor and reviewer attribution.
7. **Agency-level metrics** — research hours, papers read, patterns extracted.
8. **SOP viewer** — users read the exact procedure the AI is following, with version history.
9. **Proposed-updates inbox** — AI-suggested SOP changes awaiting human review ("add step 4: verify chapter boundaries").

### The bridge
Every "Agent 23 found pattern X" in the UI maps to a specific `worker-id T wrote blackboard entry Y` event. Drilling into any tile reveals the raw engine events that populated it. Every SOP reference in the audit trail points to a specific version of the SOP document.

---

## Where human-team framing IS correct

- **Human-AI boundary** (UX, onboarding, support) — respect human constraints at the edges.
- **Audit / regulation** — regulators think in named roles. Presentation layer gives them that.
- **Billing / attribution** — "who did this" matters for cost accounting. Map presentation agents to engine cost slices.
- **Hard sequential gates** (legal, compliance) — parallelism forbidden. Model as DAG nodes with explicit gating.
- **Accountability** — when something breaks, a named "agent" has to own it, even if that agent is a dashboard slot.
- **The entire presentation layer** — anthropomorphism is cognitively cheap for users; that cheapness is a feature.

---

## Anti-pattern flags (trigger phrases)

If the design uses these words in ARCHITECTURE context, reframe:

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
- "A then B" without a justification for the sequentiality

In PRESENTATION context, the same words are fine or even preferable.

---

## Prior art

### Engine side
- **Anthropic "Building effective agents"** (Sept 2024) — "workflows first, agents only when necessary" is itself AI-native framing.
- **Blackboard architecture** — Erman et al., HEARSAY-II (1970s). Pattern predates modern AI by 50 years.
- **Actor model** — Erlang/OTP. Pre-dates AI, maps cleanly to agents-with-mailboxes.
- **Unix philosophy** — small tools + pipes = AI-native before AI.
- **The Bitter Lesson** — Sutton, 2019. Related axis: general methods > human cleverness.
- **Map-reduce** — data-flow > control-flow thinking.
- **LangGraph** — DAG abstraction done well.
- **CrewAI, AutoGen** — cautionary tales. Most fall into the anthropomorphic trap.
- **Simon Willison's LLM essays** — prompt composition + retrieval practice.

### Presentation side
- **Air traffic control dashboards** — hundreds of parallel agents, legible at a glance.
- **CI/CD pipelines** (GitHub Actions, Buildkite) — workflows as teams of runners.
- **Kubernetes UIs** (Lens, k9s) — pods as members visually; scheduler AI-native underneath.
- **Distributed database monitors** (Datadog, Grafana) — nodes as characters on a stage.
- **Game AI overlays** (SC2 replays, Factorio production stats) — hundreds of workers shown legibly.
- **SCADA / industrial control operator consoles** — massively parallel processes framed as named operators.
- **NORAD / FedEx SuperHub ops displays** — ops centres rendering thousands of concurrent actors.
- **Bret Victor's "Ladder of Abstraction"** — progressive disclosure from concrete to abstract.
- **Edward Tufte** — making parallel activity legible.

### Documentation side
- **Aviation SOP culture** (checklists, post-incident updates) — the gold standard for executable documentation in safety-critical work.
- **Toyota Production System / A3 reports** — structured documentation that captures not just what, but why and what-we-learned.
- **Runbook practices from SRE** (Google SRE book) — "the runbook is the automation spec" culture.
- **Atul Gawande, The Checklist Manifesto** — why checklists beat expertise memory in complex domains.
- **Anthropic's own `CLAUDE.md` pattern** — per-project operating manual the AI actually reads.
- **This project's `tasks/lessons.md`** — working closed-loop SOP in the wild.
- **ADR (Architecture Decision Records)** — why-we-chose-this persisted for future agents.

### Cognitive science
- **Theory of Mind** literature (Baron-Cohen, Premack & Woodruff).
- **Mirror neurons** (Rizzolatti, Gallese).
- **Dennett's intentional stance** — treating systems as agents is pragmatic but sometimes misleading.
- **Miller's 7±2** — working memory limit.
- **Simon's chunking** — why we're good at hierarchies, bad at flat parallel systems.
- **Donella Meadows, "Thinking in Systems"** — why organic systems handle parallelism differently from hierarchies.

---

## Skill mechanics

The `designing-ai-systems` skill runs **four passes**.

### Pass 0 — Mine human domain expertise
For each role the AI will occupy, gather:
1. What do experienced humans in this role know?
2. What mistakes do newcomers make?
3. What edge cases have seasoned practitioners seen?
4. What hard rules have they learned?
5. What vocabulary is load-bearing?
6. What documents would a human consult before acting?

If Project C is available, invoke it to mechanise this pass. Otherwise, gather manually (interviews, forum mining, YouTube, books).

### Pass 0.5 — Design the documentation substrate
For each role:
1. Which of the nine documentation types does this role need? (SOP, runbook, playbook, lessons-learned, glossary, system prompt, few-shot bank, eval harness, decision log.)
2. Define the canonical SOP shape (steps, inputs, outputs, failure modes).
3. Specify versioning and review process.
4. Define the closed-loop update mechanism (how AI proposes changes, who approves).
5. Specify how the presentation layer renders the SOP for users.

Every artefact here becomes both engine input AND presentation artefact.

### Pass 1 — Engine reframe
1. Detect human-team framing in the architecture.
2. Rewrite constraints as tokens / latency / observability / determinism / cost / **parallelism**.
3. Flip the parallelism default — every "A then B" is suspect; demand justification if sequential.
4. Propose AI-native candidates (blackboard / pipeline / DAG / ensemble / self-queue / critic-loop / pub-sub / sub-agent spawn).
5. Stress-test against AI-native failure modes (token overrun, latency fanout, non-determinism, eval gap, hallucination cascade, cost blow-up, runaway spawn depth).
6. Apply the weekend-prototype forcing function — if human framing said weeks, demand the 48-hour AI-native version.

### Pass 2 — Presentation design
1. Take the engine architecture.
2. Design the user-facing agency view on top.
3. Name personas, design tiles, specify the event feed.
4. Define the bridge — how each presentation event maps to engine events.
5. Verify audit drill-down — every UI claim traceable to an engine event.
6. Include SOP visibility — users must be able to see and review the documentation the AI is following, plus an inbox for AI-proposed updates.

Top-of-invocation mantra: *"Humans as content. Documentation as fuel. Parallelism as default. Anthropomorphic surface, AI-native engine, event-log bridge."*

---

## Integration with existing superpowers

- **Pre-flight before `superpowers:brainstorming`** for AI systems — sets the four-principle frame from turn 1.
- **Checkpoint inside `superpowers:writing-plans`** — "does this plan separate engine from presentation, encode Pass 0, design documentation substrate, default to parallel?"
- **Slash command `/ai-native-reframe`** — mid-session audit of an existing design.
- **Review-style skill** (parallel to `code-reviewer`) — flags leaks from presentation language into engine decisions and vice versa.
- **Potential `CLAUDE.md` Hard Rule** for AI-system projects — "before designing any agentic system, invoke `designing-ai-systems`."

---

## Strategic / thought-leadership angle

Most AI startups today ship **flat single-layer** systems. Either:
- **Pure agency** — CrewAI-of-50 — architecturally broken under load, non-deterministic, expensive, hard to debug.
- **Pure pipeline** — well-engineered ETL — UX-dead, unremarkable, hard to market.

Very few teams build both layers. Even fewer invest in documentation-as-substrate. The two-layer pattern plus disciplined SOP-driven operation is the synthesis. Packaged well, it's:

- A blog-post series (reframe → four principles → pattern → worked example).
- A conference talk ("Stop designing AI systems like digital human teams").
- A framework / library (two layers with a defined bridge API + SOP schema).
- A product wedge: *"we help you design AI systems that work AND sell — and get better every day."*

### The documentation moat

Companies that invest in AI-ready documentation — SOPs, runbooks, lessons-learned, glossaries — compound improvements. Each execution sharpens the SOP; each sharper SOP produces a sharper AI; each sharper AI sharpens the SOP faster. This is a flywheel no competitor can catch up to without the same upfront investment.

Companies that don't invest in documentation will find their AI systems stagnate — or regress, as edge cases the team once knew get forgotten and the AI keeps re-learning them.

Early adopters of this pattern — especially in domains like admin, customer support, research, legal review, where SOP culture already exists — build unfair advantages over teams still porting their org chart into agents.

---

## Next steps

1. Write `~/.claude/skills/designing-ai-systems/SKILL.md` based on the four-pass mechanics above.
2. Write `~/.claude/commands/ai-native-reframe.md` based on the Pass 0 → 0.5 → 1 → 2 checklist.
3. Apply both to Project C's current design as a live test.
4. Iterate the skill's description / trigger phrases based on whether it auto-fires on the right conversations.
