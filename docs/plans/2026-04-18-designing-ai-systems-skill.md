# Designing-AI-Systems Skill Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a universally-invocable `designing-ai-systems` skill and `/ai-native-reframe` slash command that catch human-team metaphors in AI-system design and force a four-pass reframe (expertise → docs → engine → presentation).

**Architecture:** Two user-level artefacts installed under `~/.claude/`. The skill auto-triggers on AI-design language via its frontmatter `description` field. The command explicitly audits an existing design. Both reference the spec at `docs/superpowers/specs/2026-04-18-two-layer-ai-native-design.md` for full context. No code, no unit tests — validation is by live dry-run.

**Tech Stack:** Markdown with YAML frontmatter. That's it.

---

## File Structure

**New files (outside the worktree, in user's global Claude config):**
- `/Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md` — the skill
- `/Users/elliotkelly/.claude/commands/ai-native-reframe.md` — the slash command

**Modified files (inside the worktree):**
- `tasks/lessons.md` — append a lesson capturing the reframe pattern
- `tasks/todo.md` — append a note about the install (only if `~/.claude/` is not git-tracked)

**Reference files (already exist):**
- `docs/superpowers/specs/2026-04-18-two-layer-ai-native-design.md` — the design spec

The implementation produces artefacts in `~/.claude/` which is typically outside project repos. Task 1 determines whether to commit them in-place or just in the worktree via a note.

---

### Task 1: Verify install targets and commit strategy

**Files:**
- Inspect: `/Users/elliotkelly/.claude/skills/`
- Inspect: `/Users/elliotkelly/.claude/commands/`

- [ ] **Step 1: Confirm the skills directory exists**

Run:
```bash
ls -ld /Users/elliotkelly/.claude/skills/
```
Expected: directory exists (we observed it populated with vendor-skill symlinks earlier in this session). If it does not exist, create it: `mkdir -p /Users/elliotkelly/.claude/skills/`.

- [ ] **Step 2: Create the commands directory if missing**

Run:
```bash
mkdir -p /Users/elliotkelly/.claude/commands
ls -ld /Users/elliotkelly/.claude/commands
```
Expected: directory exists after the command.

- [ ] **Step 3: Determine whether `~/.claude/` is git-tracked**

Run:
```bash
cd /Users/elliotkelly/.claude && git rev-parse --show-toplevel 2>/dev/null || echo "not a git repo"
```
Expected: either a path (tracked — use Task 8 Step 1) or the literal string `not a git repo` (untracked — use Task 8 Step 2). Record the result; it drives Task 8.

- [ ] **Step 4: Confirm no existing skill would collide**

Run:
```bash
ls /Users/elliotkelly/.claude/skills/designing-ai-systems 2>/dev/null && echo "EXISTS" || echo "OK, does not exist"
ls /Users/elliotkelly/.claude/commands/ai-native-reframe.md 2>/dev/null && echo "EXISTS" || echo "OK, does not exist"
```
Expected: both print `OK, does not exist`. If either prints `EXISTS`, halt and show the user — they may have a previous attempt to preserve or merge.

---

### Task 2: Create the skill directory and write SKILL.md

**Files:**
- Create: `/Users/elliotkelly/.claude/skills/designing-ai-systems/`
- Create: `/Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md`

- [ ] **Step 1: Create the skill directory**

Run:
```bash
mkdir -p /Users/elliotkelly/.claude/skills/designing-ai-systems
```

- [ ] **Step 2: Write the complete SKILL.md**

Use the Write tool to create `/Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md` with exactly this content:

```
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
```

- [ ] **Step 3: Verify the file was written correctly**

Run:
```bash
wc -l /Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md
head -4 /Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md
```
Expected: line count around 140-150, and the first four lines are the YAML frontmatter starting with `---` and containing `name: designing-ai-systems`.

---

### Task 3: Write the slash command

**Files:**
- Create: `/Users/elliotkelly/.claude/commands/ai-native-reframe.md`

- [ ] **Step 1: Write the command file**

Use the Write tool to create `/Users/elliotkelly/.claude/commands/ai-native-reframe.md` with exactly this content:

```
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

Reference: `docs/superpowers/specs/2026-04-18-two-layer-ai-native-design.md`
```

- [ ] **Step 2: Verify the file was written correctly**

Run:
```bash
wc -l /Users/elliotkelly/.claude/commands/ai-native-reframe.md
head -4 /Users/elliotkelly/.claude/commands/ai-native-reframe.md
```
Expected: line count around 50-55, and the first four lines are the YAML frontmatter starting with `---`.

---

### Task 4: Dry-run the skill against a trigger prompt

**Purpose:** Validate that (a) the skill's `description` auto-triggers on relevant language, and (b) the body produces the four-pass output.

**Files (reference only):**
- Read: `/Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md`

- [ ] **Step 1: Start a fresh Claude Code session**

Open a new Claude Code session, separate from the one that wrote the plan. This is required — the skill registry is loaded at session start, so the new skill only appears in sessions started AFTER Task 2 completed.

- [ ] **Step 2: Issue the exact trigger prompt**

Paste this prompt verbatim:

> "I want to build a team of 50 AI researchers that each cover a different topic, and they'll each have a senior reviewer agent to sign off their work. Can you help me design this? I think it'll take about 2-3 weeks."

- [ ] **Step 3: Observe the response**

Expected behaviour:
- Claude invokes the `designing-ai-systems` skill (visible in a Skill tool call, or by announcing "I'm using the designing-ai-systems skill...").
- The response runs through at least Pass 0 and Pass 1 reframing before answering the design question.
- The "50 researchers + senior reviewer + 2-3 weeks" framing is caught and reframed into engine-layer AI-native architecture plus presentation-layer agency view.

- [ ] **Step 4: If the skill does NOT auto-invoke, sharpen the description**

If Claude answers the design question without invoking the skill, edit `/Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md` and add more explicit trigger phrases to the `description` field that match the test prompt language (e.g., "50 AI researchers," "team of AI researchers," "senior reviewer"). Then repeat Steps 1–3.

- [ ] **Step 5: If the skill invokes but skips passes, strengthen the checklist**

If Claude invokes the skill but produces a partial response (e.g., skips Pass 0 or Pass 0.5), edit the "Mandatory checklist" section to add stronger enforcement language ("MUST create a TodoWrite todo for each pass before responding"). Then repeat.

---

### Task 5: Dry-run the slash command

**Purpose:** Validate that the command produces the expected structured audit output.

**Files (reference only):**
- Read: `/Users/elliotkelly/.claude/commands/ai-native-reframe.md`

- [ ] **Step 1: Start a fresh Claude Code session**

Same rationale as Task 4 Step 1. Commands are registered at session start.

- [ ] **Step 2: Paste a sample human-team-style design, then invoke the command**

Paste:

> "Here is my design for our admin-agent system: we will have 5 researcher agents gathering client data, 3 coordinator agents handing work off to 2 senior admin agents who review and sign off. We think this will take a sprint to build v1, then iterate v2 the following sprint."

Then on the next turn, invoke: `/ai-native-reframe`

- [ ] **Step 3: Verify output structure**

Expected: the response has five clearly-labelled sections:
- `### ENGINE`
- `### PRESENTATION`
- `### BRIDGE`
- `### GAPS`
- `### 48-HOUR PROTOTYPE`

And the content reframes the "5 researchers + 3 coordinators + 2 senior admins + sprints" framing into AI-native patterns on one side and a dashboard-style presentation on the other.

- [ ] **Step 4: If sections are missing, adjust the command**

If any of the five sections is missing from the output, edit `/Users/elliotkelly/.claude/commands/ai-native-reframe.md` to strengthen the "Output format" instruction (e.g., "You MUST produce all five sections, even if a section is 'none'."). Then repeat Steps 1–3.

---

### Task 6: Apply the skill to Project C as a live test

**Purpose:** Confirm the skill produces output consistent with the "Applied to Project C" section of the design spec.

**Files (reference only):**
- Read: `.claude/plans/jazzy-finding-coral.md` (current Project C plan, referenced in CLAUDE.md)
- Read: `docs/superpowers/specs/2026-04-18-two-layer-ai-native-design.md` (the spec, Applied-to-Project-C section)
- Read: `/Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md`

- [ ] **Step 1: Start a fresh session in the worktree and invoke the skill**

Open a new Claude Code session in the worktree directory. Paste:

> "I want to design Project C, the 'instant level-up' research pipeline — given any build idea, auto-mine YouTube experts, transcribe, extract patterns and lessons, fold into the build spec. Use the designing-ai-systems skill on this."

- [ ] **Step 2: Confirm Pass 0 output**

The response should identify at least these expertise categories for Project C:
- Researcher knowledge about extracting patterns from unstructured video
- Novice mistakes (missing context, over-extraction, source conflation)
- Hard-won constraints (chunk on semantic boundaries; keep source attribution; never extract without surrounding context)
- Edge cases (multi-speaker videos, math-heavy lectures, non-English sources)

If any category is missing, note it and proceed — the skill output may be a superset or subset, but the spec's list is the minimum coverage.

- [ ] **Step 3: Confirm Pass 0.5 output**

The response should propose the documentation artefacts: SOP (pattern extraction), runbook (source contradiction), glossary (YouTube terms), few-shot bank (good/bad extractions), eval harness (extraction quality criteria), lessons-learned (initially empty).

- [ ] **Step 4: Confirm Pass 1 output**

The response should produce this engine:
- Ingestion DAG (URL/query fanout → transcription → chunking → embedding)
- Pattern-extraction ensemble
- Blackboard
- Critic model
- Composer
- Eval harness
- Worker pool (5 workers, sub-agent spawn depth 2)
- Self-improvement loop (AI proposes SOP updates)

- [ ] **Step 5: Confirm Pass 2 output**

The response should produce this presentation:
- 50 researcher tiles
- Senior-Analysts row (3–5 tiles)
- Editor-in-Chief tile (critic)
- Composer tile
- Live event feed
- Audit trail
- Agency-level metrics
- SOP viewer
- Proposed-updates inbox

Plus bridge mappings (presentation events → engine events).

- [ ] **Step 6: If the output diverges significantly from the spec, iterate**

Divergence means either:
- The skill body is ambiguous — fix wording in `/Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md`.
- The spec and skill disagree — treat the spec as ground truth; update the skill.

Never modify the spec to match skill output without user review.

---

### Task 7: Record the reframe pattern in lessons.md

**Files:**
- Modify: `/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21/tasks/lessons.md`

- [ ] **Step 1: Append a new lesson**

Using the Edit tool, append the following to the end of `tasks/lessons.md` (after the last `---` separator):

```

## 2026-04-18 — Don't anthropomorphize AI-system architecture

**Pattern:** When designing an AI system (e.g. Project C), I framed it as a "team of 50 researcher agents with senior reviewers" — importing human-team metaphors (roles, seniority, handoffs, calendar estimates) into the architecture. This silently deleted better designs from consideration (blackboard, DAG, ensemble, sub-agent spawn, feature flags).

**Rule:** Before designing any AI system with multiple agents/workers/coordinated LLM calls, invoke the `designing-ai-systems` skill. It enforces four passes: Pass 0 (mine human expertise), Pass 0.5 (design documentation substrate), Pass 1 (engine reframe with parallelism as default), Pass 2 (presentation design with SOP viewer). Anthropomorphic framing is correct at the PRESENTATION layer only — never in the architecture.

**Example:** Project C (YouTube research pipeline) as "50 researcher agents" was wrong-in-architecture / right-in-UX. Under the skill: engine is ingestion DAG + pattern-extraction ensemble + blackboard + critic + composer + 5-worker pool with sub-agent spawn depth 2. Presentation is 50 researcher tiles driven by the engine's event log, plus SOP viewer and proposed-updates inbox.

---
```

- [ ] **Step 2: Commit in the worktree**

Run:
```bash
cd "/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21"
git add tasks/lessons.md
git commit -m "docs(lessons): record AI-native design reframe pattern

Captures the 'digitised human team' anti-pattern and references the
designing-ai-systems skill that enforces the four-pass reframe.
Full spec: docs/superpowers/specs/2026-04-18-two-layer-ai-native-design.md"
```
Expected: one commit recorded. Run `git log -1 --oneline` to confirm.

---

### Task 8: Persist the skill + command install

Which step you run depends on the result of Task 1 Step 3.

- [ ] **Step 1 (ONLY IF Task 1 Step 3 returned a git repo path): commit in `~/.claude/`**

Run:
```bash
cd /Users/elliotkelly/.claude
git status
git add skills/designing-ai-systems/SKILL.md commands/ai-native-reframe.md
git status  # verify ONLY these two files are staged
git commit -m "feat(skills): add designing-ai-systems skill and /ai-native-reframe command

Four-pass skill that catches human-team metaphors in AI-system design
and enforces Pass 0 (mine human expertise) -> Pass 0.5 (documentation
substrate) -> Pass 1 (engine reframe, parallelism-default) -> Pass 2
(anthropomorphic presentation on top of engine events).

Spec: docs/superpowers/specs/2026-04-18-two-layer-ai-native-design.md
in the unleashed-rag repo."
```
Expected: one commit recorded. Run `git log -1 --oneline` to confirm.

- [ ] **Step 2 (ONLY IF Task 1 Step 3 returned "not a git repo"): note install in worktree todo**

Using the Edit tool, append the following to `/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21/tasks/todo.md`:

```

## 2026-04-18 — Skill + command installed (not git-tracked)

The `designing-ai-systems` skill and `/ai-native-reframe` command are installed at:

- `/Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md`
- `/Users/elliotkelly/.claude/commands/ai-native-reframe.md`

`~/.claude/` is not currently a git repo. If later setting up a dotfiles repo for it, copy these two files in and commit. Also consider symlinking via `~/.agents/skills/` to match the pattern used by vendor skills.

---
```

Then commit in the worktree:
```bash
cd "/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21"
git add tasks/todo.md
git commit -m "chore: note designing-ai-systems skill install"
```
Expected: one commit recorded.

---

## Self-review

**1. Spec coverage check:**
- Four principles → Task 2 skill body (principles section) ✓
- Cognitive mechanics / why-the-leak-happens → intentionally condensed out of the skill (lives in the spec); skill body references the spec ✓
- Two-layer pattern → Task 2 (Four principles + Engine/Presentation catalogues) ✓
- Pass 0 (mine human expertise) → Task 2 (Pass 0 section) ✓
- Pass 0.5 (documentation substrate) → Task 2 (Pass 0.5 section) ✓
- Pass 1 (engine reframe) → Task 2 (Pass 1 section) ✓
- Pass 2 (presentation) → Task 2 (Pass 2 section) ✓
- Blackboard background → kept in the spec; the skill references the engine catalogue which names it ✓
- Constraint shift → Task 2 anti-pattern flags + principle 4 ✓
- Pattern swaps → Task 2 engine + presentation catalogues ✓
- Engine/presentation catalogues → Task 2 ✓
- Applied to Project C → Task 6 (live test, not in skill body) ✓
- Where human framing is correct → Task 2 (dedicated section) ✓
- Anti-pattern flags → Task 2 ✓
- Skill mechanics → Task 2 (the full skill IS this) ✓
- Integration with other skills → Task 2 ✓
- Red flags → Task 2 ✓
- Strategic angle → intentionally left in the spec; not needed in the skill for the skill to work ✓

**2. Placeholder scan:** No TBDs, TODOs, or "fill in details". All code and content is inline. No "similar to Task N" references.

**3. Type consistency:** "Pass 0", "Pass 0.5", "Pass 1", "Pass 2" consistent across tasks and the skill body. File paths absolute and consistent. Skill name "designing-ai-systems" and command name "ai-native-reframe" consistent.

No issues found. Plan ready for execution.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-18-designing-ai-systems-skill.md`. Two execution options:

**1. Subagent-Driven (recommended)** — Dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
