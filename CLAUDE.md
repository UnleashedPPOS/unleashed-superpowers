# CLAUDE.md — Unleashed Superpowers Contribution Guide

For contributors (and AI agents) extending this plugin.

## Anatomy of a skill

Every skill lives at `skills/<kebab-case-name>/SKILL.md` with YAML frontmatter:

```yaml
---
name: kebab-case-name
description: One paragraph. Must include every phrase that should auto-trigger the skill ("agentic system," "multi-agent," specific tool names, etc.). 2–4 sentences.
---
```

Body sections, in this order:

1. **Announce at start** — one-liner Claude says before doing anything ("I'm using the X skill to Y.").
2. **Four principles / thesis / hook** — 3–5 sentences on the core insight.
3. **When this fires** — explicit trigger scenarios.
4. **Mandatory checklist** — numbered passes. Each pass has: 1–2 sentences of purpose, then a numbered list of concrete steps.
5. **Pattern catalogue(s)** — reference material the AI cites.
6. **Anti-pattern flags** — phrases or situations that should re-trigger the skill or escalate.
7. **Integration with other skills** — how this composes with the rest of the library.
8. **Red flags** — a table of "thought" → "reality" pairs for rationalisation detection.
9. **Reference** — link to the full design spec if one exists.

## Anatomy of a command

Every command lives at `commands/<kebab-case-name>.md` with YAML frontmatter:

```yaml
---
description: One sentence describing what the command does. Shown in the slash-command picker.
---
```

Body is the prompt Claude sees when the command fires. Keep it tight — 40–80 lines is the sweet spot.

## Naming rules

- **Verb-first for commands** (`/ai-native-reframe`, `/ship-check`, `/evaluate-repository`).
- **Noun-phrase for skills** (`designing-ai-systems`, `document-feature-module`).
- **Lowercase kebab-case** throughout.
- **No `superpowers:` prefix** — we are `unleashed-superpowers`, not `superpowers`.

## Trigger-phrase design

The `description` field is the most important line in a skill. It's what Claude reads to decide whether to invoke.

- **List real user phrasings** — not technical jargon but the words a user actually types. "Agentic system," "multi-agent," "team of agents," "50 researchers" — these are what trigger.
- **Include anti-patterns** — "senior reviewer agent," "handoff between agents," "2-3 weeks sprint" — phrases that indicate the skill SHOULD fire.
- **Be specific about when to skip** — explicit "SKIP: ..." clauses reduce false positives.

## Adding a new skill

1. Create `skills/<name>/SKILL.md` with frontmatter + body per the anatomy above.
2. Add trigger phrases to the description until the skill auto-fires reliably in fresh sessions.
3. If the skill is substantial, add a design spec at `docs/specs/YYYY-MM-DD-<name>-design.md` and link it from the skill body.
4. Bump `.claude-plugin/plugin.json` version (minor for new skill, patch for fix).
5. Commit with message `feat(skill): add <name>`.

## Adding a new command

1. Create `commands/<name>.md` with frontmatter + prompt body.
2. If the command wraps a skill, have it invoke the skill explicitly in the prompt.
3. Bump version (patch is fine for commands).
4. Commit with message `feat(cmd): add /<name>`.

## Attribution policy

This plugin currently contains only originally-authored content. If a skill is borrowed or forked from elsewhere:

- Credit the original author in a `CREDITS.md` entry at the repo root.
- Add an `origin:` field to the skill's frontmatter pointing to the upstream source.
- Include the upstream's license (as a per-skill `LICENSE` file) if it differs from the repo MIT.
- Refuse to redistribute anything with no license or a non-redistribution clause.

## Releases

Versioning in `.claude-plugin/plugin.json` follows semver. Until v1.0.0, breaking changes can happen on minor bumps.
