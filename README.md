# Unleashed Superpowers

A Claude Code plugin that catches human-team metaphors in AI-system design and forces AI-native reframing. Plus a reference-quality feature-documentation skill that enforces source-grounded accuracy.

## The thesis

Most people designing AI systems accidentally design digitised human teams. They import agent roles, seniority framing, calendar estimates, and v1/v2 roadmaps — metaphors that silently delete better architectures from the design space.

This plugin catches that and reframes around AI-native constraints (tokens, latency, observability, determinism, parallelism). The four-principle summary:

1. **Don't anthropomorphize the structure.** No team-of-agents architecture. Use AI-native patterns (blackboard, DAG, ensemble, queue, sub-agent spawn).
2. **DO absorb human expertise as content.** Mine what humans know — especially their mistakes — and encode it as critic rules, validation schemas, few-shot examples.
3. **Documentation is executable.** SOPs, runbooks, and lessons-learned files are the persistent form of human expertise. The AI reads them, is tested against them, and proposes updates.
4. **Parallelism is the default.** Sequential is the exception that must justify itself.

Design thesis: *Anthropomorphic surface, AI-native engine, event-log bridge.*

Full argument: [docs/specs/2026-04-18-two-layer-ai-native-design.md](docs/specs/2026-04-18-two-layer-ai-native-design.md).

## Installation

### Option 1 — Claude Code plugin install (preferred)

```bash
claude plugins install gh:UnleashedPPOS/unleashed-superpowers
```

After install, the skills auto-register in every new Claude Code session.

### Option 2 — Git clone + symlink (fallback if Option 1 is not yet supported)

```bash
git clone https://github.com/UnleashedPPOS/unleashed-superpowers.git ~/Developer/unleashed-superpowers

# Skills
ln -s ~/Developer/unleashed-superpowers/skills/designing-ai-systems \
      ~/.claude/skills/designing-ai-systems
ln -s ~/Developer/unleashed-superpowers/skills/document-feature-module \
      ~/.claude/skills/document-feature-module
ln -s ~/Developer/unleashed-superpowers/skills/mac-tuneup \
      ~/.claude/skills/mac-tuneup

# Commands
ln -s ~/Developer/unleashed-superpowers/commands/ai-native-reframe.md \
      ~/.claude/commands/ai-native-reframe.md
ln -s ~/Developer/unleashed-superpowers/commands/document-feature-module.md \
      ~/.claude/commands/document-feature-module.md
```

Start a fresh Claude Code session. The skills appear in the registry.

## What's inside

### Skills

**`designing-ai-systems`** — Four-pass AI-native reframe.

Triggers automatically on phrases like "agentic system," "multi-agent," "50 researchers," "team of agents," "senior reviewer agent," or any design discussion for LLM-coordinated systems. Runs four passes in order:

- **Pass 0** — mine human domain expertise (mistakes, edge cases, hard rules, vocabulary)
- **Pass 0.5** — design the documentation substrate (SOPs, runbooks, lessons-learned, glossaries)
- **Pass 1** — engine reframe (AI-native patterns, parallelism-as-default, stress-test failure modes)
- **Pass 2** — presentation design (anthropomorphic surface, event-log bridge, SOP viewer)

Mantra: *"Humans as content. Documentation as fuel. Parallelism as default. Anthropomorphic surface, AI-native engine, event-log bridge."*

**`document-feature-module`** — Reference-quality feature documentation.

Produces docs a new contributor (or AI agent) can trust without cross-checking the source. Two lenses: Senior Engineer (every code claim must grep to a real symbol; invariants justified with `Why:` lines; failure modes and perf characteristics named) and Senior Designer (scanability, verb-first copy, clear extension points).

Golden rule: **every factual claim resolves to a grepable symbol.** If you can't grep it, don't write it.

**`seo-geo`** — Data-first SEO, GEO and AI-search playbook.

The 7-step workflow (project instructions, About My Business, buyer-question gaps, audit, strategy, week-1 implementation, Monday dashboard) wired to the unleashed-funnel-factory engine (`seo-audit`, `indexnow`, `seo-playbook`, `seo-weekly`). Truth rule: no invented stats, rankings or reviews; absent providers are "not connected". Reference files cover AI-bot robots rules, backlinks and distilled open-seo methods.

**`high-level`** — High-Level mode: end-state-only reporting.

Like caveman mode, but you keep normal sentences and drop everything the reader doesn't need. No narration while the agent works, then one status page that lists only open items (Needs you first, count headline, finished items moved to a done log) and a one-line chat reply. One line per item, each fact said once, with no line cap so open items are never dropped. Say "high-level mode" (or `/high-level`) to turn it on and "normal mode" to turn it off.

To make it permanent, run **`/high-level-mode on`** once. That writes a flag file (`~/.claude/high-level-mode`), and the plugin's SessionStart hook ([`hooks/high-level-session-start.sh`](hooks/high-level-session-start.sh)) then loads the rules into every new session: terminal, desktop app and IDE, plus after `/clear` and compaction (resumed chats already have them). `/high-level-mode off` turns it off; `HIGH_LEVEL_MODE=0` skips it for one session. Use the hook or the output style, not both, or the rules load twice. This is the recommended route because the desktop app fixes a session's output style when the session starts and only lists custom styles in Settings.

### Output styles

**`High-Level`** ([`output-styles/high-level.md`](output-styles/high-level.md)) — the single source of the High-Level rules (the hook reads this file). You can also pick it as an output style for new sessions: in the terminal via `/output-style`, in the desktop app via Settings → Claude Code (copy the file into `~/.claude/output-styles/` first if the plugin's styles aren't listed). Cloud sessions set up with `cloud-kit/install.sh` use it by default.

### Commands

| Command | What it does |
|---|---|
| `/ship-check` | The whole ship gate, one command. Runs, in order, and refuses to report success if any stage fails: **1. Verify** (repo's own gates — typecheck, lint, FULL test suite, build/export — plus the review/cleanup chain and smoke checks), **2. Red-Team** (adversarial falsification — same `red-team` skill `/red-team` uses standalone, includes the AI-native-coverage and voice-coverage attack lanes), **3. Definition of Done** (fills the ledger from `skills/definition-of-done/SKILL.md`, verdict line first — same skill `/dod` uses standalone), **4. Ship** (pre-merge verdict + automatic merge of this session's isolated PRs). `--no-merge` stops before the merge phase; `--scope=<freeform>` overrides the inferred session intent. |
| `/red-team [scope]` | Standalone adversarial falsification pass — attacks every "it's done" claim from this session with a disconfirming experiment, fixes what cracks, reports only when clean. Also runs as `/ship-check` Stage 2 — both invoke `skills/red-team/SKILL.md`, one source of truth. |
| `/dod <feature>` | Standalone Definition-of-Done ledger fill, verdict line first. Also runs as `/ship-check` Stage 3 — both invoke `skills/definition-of-done/SKILL.md`, one source of truth. |
| `/high-level-mode on\|off\|status` | Turns High-Level mode on or off for this and every future session (flag file + SessionStart hook). |
| `/ai-native-reframe` | Mid-session audit. Takes the current AI-system design and produces structured output with five sections: ENGINE, PRESENTATION, BRIDGE, GAPS, 48-HOUR PROTOTYPE. |
| `/document-feature-module <target>` | Thin wrapper that invokes the `document-feature-module` skill against a target module. |
| `/learnings [notes\|unenforced\|prune]` | Turns each founder correction into an enforced check or eval case plus a one-line rule, in one step, filed in the corrections registry and inventory. `unenforced` lists corrections still prose-only; `prune` runs the monthly prune. |

`/red-team` and `/dod` stay available standalone for sessions that want just one stage — `scripts/check-command-sync.sh` fails the build if either command (or `/ship-check`) drifts out of sync with its source-of-truth skill.

## Continuous learning

Founder corrections are enforced, not just written down. [`cloud-kit/hooks/corrections.json`](cloud-kit/hooks/corrections.json) holds every correction from the always-loaded rules, classified as a **check** (run by [`correction-checks.py`](cloud-kit/hooks/correction-checks.py) on tool calls, the final reply and the founder's prompt: credentials, OpenRouter outside the OS app, "X for Y" brand copy, time estimates, unverified links, status in chat and more), an **eval** case under `evals/`, or **prose** with one home. [`docs/learning/corrections-inventory.md`](docs/learning/corrections-inventory.md) is the generated table; `docs/learning/unenforced.md` lists what is still prose-only; [`docs/learning/monthly-prune.md`](docs/learning/monthly-prune.md) is the monthly routine (booking definition: `monthly-prune.routine.json`). The always-loaded rules are capped by [`docs/learning/budget.json`](docs/learning/budget.json) and a test fails if they grow past it.

Outcome gate: [`cloud-kit/hooks/eval-gate.py`](cloud-kit/hooks/eval-gate.py) blocks a commit or PR that changes an LLM prompt or model in a product repo until that repo's eval has run, and the PR body must carry the score. It runs offline in the cloud and live through `vault run` locally. The per-repo eval commands are in [`cloud-kit/hooks/eval-gate.json`](cloud-kit/hooks/eval-gate.json), with a table in the `llm-provider-chain` skill. Lane, routine and sub-agent briefs state the goal, the constraints and a success check; the template is in the `where-work-runs` skill.

Chief reporting: [`cloud-kit/hooks/chief-cloud-report.py`](cloud-kit/hooks/chief-cloud-report.py) makes a cloud chat report in to Chief (session start, prompt, stop, waiting-on-you, end) when `CHIEF_INGEST_CLOUD_TOKEN` is set; unset, it does nothing. Each heartbeat carries the chat register fields: state (working / waiting on you / done) and the chat's last line (200 characters, secrets scrubbed, never your messages). Write-only token, 2 s timeout, never blocks or prints the token.

Heavy-job gate: [`cloud-kit/bin/heavy-run`](cloud-kit/bin/heavy-run) makes jest/tsc/eslint/builds wait their turn (2 slots, memory-aware) on the 8 GB Mac; [`heavy-gate.py`](cloud-kit/hooks/heavy-gate.py) routes bare heavy commands through it, and [`heavy-ledger-hook.py`](cloud-kit/hooks/heavy-ledger-hook.py) makes sure a job the memory brake killed is re-run before a chat claims tests pass. Details in `skills/mac-tuneup/REFERENCE.md`.

Tests: `python3 -m unittest discover -s tests/hooks && python3 -m unittest discover -s tests/learning`.

## Definition of Done

`skills/definition-of-done/SKILL.md` is the ledger every "ship it" must fill: intent, front end, back end, integrations, payments, security, verification, ship, aftercare. `/dod <feature>` prints it with the verdict first, and it runs as `/ship-check` Stage 3. Rows are DONE · N/A · OWNER · NOT DONE, never "deferred".

## Red-Team

`skills/red-team/SKILL.md` is the adversarial falsification pass every "it's done" claim must survive: a Claim Ledger, a disconfirming experiment per claim, a hidden-failure sweep (including the AI-native-coverage and voice-coverage attack lanes), and a fix-verify-report loop. `/red-team [scope]` runs it standalone, and it runs as `/ship-check` Stage 2.

## Roadmap

- **Phase 2** — audit and add (with attribution) a set of currently-held skills: `ui-ux-pro-max`, `/ux-simplify`, `/create-command`, `/list-mcps`, `/evaluate-repository`.
- **Upstream** — propose `designing-ai-systems` as a PR to [Jesse Vincent's `superpowers` plugin](https://github.com/obra/superpowers) for universal distribution.
- **Content** — turn the two-layer design spec into a blog post / conference talk.

## Contributing

See [CLAUDE.md](CLAUDE.md) for the contribution style guide (how to add a skill, naming rules, frontmatter requirements, trigger-phrase design).

## License

MIT. Copyright (c) 2026 Elliot Kelly.

## Author

Elliot Kelly — [Unleashed](https://unleashed.vision). Opinions on AI-system design are mine; the tools that enforce them are in this repo.
