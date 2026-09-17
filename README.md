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

### Commands

| Command | What it does |
|---|---|
| `/ship-check` | The whole ship gate, one command. Runs, in order, and refuses to report success if any stage fails: **1. Verify** (repo's own gates — typecheck, lint, FULL test suite, build/export — plus the review/cleanup chain and smoke checks), **2. Red-Team** (adversarial falsification — same `red-team` skill `/red-team` uses standalone, includes the AI-native-coverage and voice-coverage attack lanes), **3. Definition of Done** (fills the ledger from `skills/definition-of-done/SKILL.md`, verdict line first — same skill `/dod` uses standalone), **4. Ship** (pre-merge verdict + automatic merge of this session's isolated PRs). `--no-merge` stops before the merge phase; `--scope=<freeform>` overrides the inferred session intent. |
| `/red-team [scope]` | Standalone adversarial falsification pass — attacks every "it's done" claim from this session with a disconfirming experiment, fixes what cracks, reports only when clean. Also runs as `/ship-check` Stage 2 — both invoke `skills/red-team/SKILL.md`, one source of truth. |
| `/dod <feature>` | Standalone Definition-of-Done ledger fill, verdict line first. Also runs as `/ship-check` Stage 3 — both invoke `skills/definition-of-done/SKILL.md`, one source of truth. |
| `/ai-native-reframe` | Mid-session audit. Takes the current AI-system design and produces structured output with five sections: ENGINE, PRESENTATION, BRIDGE, GAPS, 48-HOUR PROTOTYPE. |
| `/document-feature-module <target>` | Thin wrapper that invokes the `document-feature-module` skill against a target module. |

`/red-team` and `/dod` stay available standalone for sessions that want just one stage — `scripts/check-command-sync.sh` fails the build if either command (or `/ship-check`) drifts out of sync with its source-of-truth skill.

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
