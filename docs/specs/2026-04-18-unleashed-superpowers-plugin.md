# Unleashed Superpowers Plugin

## A public Claude Code plugin repo for Elliot's own AI-system design skills and commands, launched clean with only confirmed-authored content

**Status:** Design spec (2026-04-18)
**Origin:** Evolved from the 2026-04-18 brainstorm about persisting the `designing-ai-systems` skill. User raised the founder question ("what would Anthropic's founders do?"); answer was "package as a proper plugin, publish publicly, propose upstream." This spec defines the Phase 1 launch — minimum viable plugin with only originally-authored content, clean IP posture, room to grow.
**Implements-next:** Implementation plan at `docs/superpowers/plans/2026-04-18-unleashed-superpowers-plugin.md`.

---

## Goal

Publish a public, MIT-licensed Claude Code plugin repo at `github.com/UnleashedPPOS/unleashed-superpowers` containing the user's originally-authored skills and commands. Proves the distribution pipeline, establishes brand, and creates the artefact the content strategy (blog post, talk, upstream PR to `superpowers`) can point to.

## Phase 1 contents (minimum viable — all confirmed originally-authored)

### Skills (2)

| Skill | Current location | Purpose |
|---|---|---|
| `designing-ai-systems` | `~/.claude/skills/designing-ai-systems/` | Four-pass AI-native reframe — catches human-team metaphors in AI-system design, forces Pass 0 (expertise mining) → 0.5 (documentation substrate) → 1 (engine reframe) → 2 (presentation design) |
| `document-feature-module` | `~/Developer/unleashedos/.claude/skills/document-feature-module/` | Produce reference-quality feature-module docs using senior-engineer + senior-designer lenses, with the "every factual claim resolves to a grepable symbol" golden rule |

### Commands (2)

| Command | Current location | Purpose |
|---|---|---|
| `/ai-native-reframe` | `~/.claude/commands/ai-native-reframe.md` | Mid-session audit of an AI-system design, produces ENGINE / PRESENTATION / BRIDGE / GAPS / 48-HOUR PROTOTYPE output |
| `/document-feature-module` | `~/Developer/unleashedos/.claude/commands/document-feature-module.md` | Thin wrapper that invokes the `document-feature-module` skill against a target module |

### Companion docs

| File | Purpose |
|---|---|
| `docs/specs/2026-04-18-two-layer-ai-native-design.md` | Full design spec for the AI-native pattern (the "why" behind `designing-ai-systems`). Copied from the worktree's version. Becomes citable authority for the skill. |

## Phase 2 backlog (held until license due-diligence done)

Held out of Phase 1 due to uncertain authorship. Each must be verified before inclusion: track down original source, check license, decide between include-with-attribution / link-only / exclude.

- `ui-ux-pro-max` skill — 636K, has `data/` + `scripts/`, branded "Pro Max" — almost certainly third-party.
- `/evaluate-repository` — explicitly labelled "Awesome-Claude-Code · Full Version". From [hesreallyhim/awesome-claude-code](https://github.com/hesreallyhim/awesome-claude-code). Link only unless relicensed.
- `/ux-simplify` — versioned 2.0.0, cites Dieter Rams / Jony Ive / Julie Zhuo. Ambiguous — confirm authorship.
- `/ship-check` — mentions `voice-coverage-audit` (user's product). Ambiguous — confirm authorship.
- `/create-command` — "Command Creator Assistant" style — ambiguous.
- `/list-mcps` — simple utility — ambiguous.

All 7 n8n skills are out of scope for this repo entirely. Separate `unleashed-n8n` repo if desired later.

## Repo structure

Mirrors the pattern used by the `superpowers` plugin (Jesse Vincent's `claude-plugins-official/superpowers`):

```
unleashed-superpowers/
├── .claude-plugin/
│   ├── plugin.json              # plugin manifest
│   └── marketplace.json         # registry metadata
├── skills/
│   ├── designing-ai-systems/
│   │   └── SKILL.md
│   └── document-feature-module/
│       └── SKILL.md
├── commands/
│   ├── ai-native-reframe.md
│   └── document-feature-module.md
├── docs/
│   └── specs/
│       └── 2026-04-18-two-layer-ai-native-design.md
├── README.md                    # what this is, how to install, per-skill summary
├── LICENSE                      # MIT, © Elliot Kelly / UnleashedPPOS
├── CLAUDE.md                    # contribution style guide (how to add a skill)
├── AGENTS.md -> CLAUDE.md       # symlink for Codex/OpenAI compatibility
├── GEMINI.md                    # minimal stub for Gemini CLI compatibility
├── .gitignore
└── .github/
    └── workflows/               # empty for now, room to add release/lint
```

### Manifest content

`.claude-plugin/plugin.json`:
```json
{
  "name": "unleashed-superpowers",
  "description": "AI-native design skills — anthropomorphic surface, AI-native engine, event-log bridge. Plus reference-quality feature documentation.",
  "version": "0.1.0",
  "author": {
    "name": "Elliot Kelly",
    "email": "elliotkelly@unleashed.vision"
  },
  "homepage": "https://github.com/UnleashedPPOS/unleashed-superpowers",
  "repository": "https://github.com/UnleashedPPOS/unleashed-superpowers",
  "license": "MIT",
  "keywords": [
    "ai-native-design",
    "skills",
    "claude-code",
    "multi-agent",
    "documentation",
    "two-layer-design"
  ]
}
```

`.claude-plugin/marketplace.json`:
```json
{
  "name": "unleashed-superpowers",
  "description": "Public marketplace for Unleashed Superpowers — AI-native design skills and feature-documentation tooling",
  "owner": {
    "name": "Elliot Kelly",
    "email": "elliotkelly@unleashed.vision"
  },
  "plugins": [
    {
      "name": "unleashed-superpowers",
      "description": "AI-native design skills — anthropomorphic surface, AI-native engine, event-log bridge. Plus reference-quality feature documentation.",
      "version": "0.1.0",
      "source": "./",
      "author": {
        "name": "Elliot Kelly",
        "email": "elliotkelly@unleashed.vision"
      }
    }
  ]
}
```

## README shape

Aimed at strangers finding this via HackerNews / Twitter / a blog-post link. Sections:

1. **One-sentence pitch** — "A Claude Code plugin that catches human-team metaphors in AI-system design and forces AI-native reframing."
2. **The thesis (3–5 sentences)** — "Most people designing AI systems accidentally design digitised human teams. This skill catches that and reframes around tokens / latency / observability / parallelism. Anthropomorphic surface, AI-native engine, event-log bridge."
3. **Installation** (two options):
   - `claude plugins install gh:UnleashedPPOS/unleashed-superpowers` (if Claude's plugin-install system accepts git URLs)
   - Manual: `git clone` + symlink from `~/.claude/skills/` and `~/.claude/commands/`
4. **What's inside** — one paragraph per skill/command with trigger phrases and example usage.
5. **The deeper argument** — link to `docs/specs/2026-04-18-two-layer-ai-native-design.md`.
6. **Contributing** — link to `CLAUDE.md`.
7. **Roadmap** — Phase 2 backlog, upstream-to-superpowers note.
8. **License** — MIT.
9. **Author** — Elliot Kelly, Unleashed.

## Licensing and attribution policy

- **LICENSE** at repo root: MIT, copyright Elliot Kelly.
- **Phase 1 has no borrowed content**, so no `CREDITS.md` needed yet.
- **Phase 2 when adding borrowed skills:**
  - Create `CREDITS.md` listing each borrowed skill's original source and license.
  - Add an `origin:` field to each borrowed SKILL.md's frontmatter pointing to the original.
  - Per-skill `LICENSE` files if the original's license differs from MIT (Apache, GPL, etc.).
  - Refuse to redistribute anything with no license or a non-redistribution clause.

## Install mechanism (wiring published repo back to local)

After the repo is public, the local `~/.claude/skills/designing-ai-systems/` and `~/.claude/commands/ai-native-reframe.md` become redundant with the published copy. Options for reconciling:

1. **Claude plugins install (preferred)** — if `claude plugins install gh:UnleashedPPOS/unleashed-superpowers` works, use that. It places the plugin in `~/.claude/plugins/cache/` and the skills appear in the registry automatically.
2. **Symlink (fallback)** — `git clone` the repo to `~/Developer/unleashed-superpowers/` and symlink `~/.claude/skills/designing-ai-systems` → the cloned path. Same for commands.

Plan will test option 1 first. If it fails (plugin-install-from-git-URL is not yet a supported flow in the user's Claude Code version), fall back to option 2.

**During the transition:** keep the existing `~/.claude/` copies in place. Test the plugin install works BEFORE removing the local copies — otherwise the user loses access to skills they've been using.

## Branding / naming

- **Repo name:** `unleashed-superpowers`
- **GitHub owner:** `UnleashedPPOS` (user's primary account per `gh auth status`; NOT the `unleashed-peak-performance-os` org).
- **Plugin name** (in manifest): `unleashed-superpowers`
- **Author:** Elliot Kelly, Unleashed.
- **Pitch:** "AI-native design skills — anthropomorphic surface, AI-native engine, event-log bridge. Plus reference-quality feature documentation."

## Duplicate-resolution policy (for Phase 2 later)

Two skills/commands currently exist in both user-level (`~/.claude/`) and unleashedos project-level (`~/Developer/unleashedos/.claude/`):

- `ui-ux-pro-max` skill
- `ship-check` command

When Phase 2 considers these: diff the two copies. If identical, use the user-level as source of truth. If different, use the newer one by mtime and flag the divergence for review.

This policy is noted here, not acted on in Phase 1 — both items are held for Phase 2 licensing review anyway.

## Success criteria for Phase 1

1. Public repo live at `github.com/UnleashedPPOS/unleashed-superpowers`.
2. Manifest files valid; repo structure matches the superpowers pattern.
3. All 4 Phase 1 skill/command files committed and match what's currently installed locally.
4. README readable by strangers; installation instructions tested.
5. Companion spec doc (`two-layer-ai-native-design.md`) copied into the repo.
6. Local Claude Code picks up the plugin via `claude plugins install gh:UnleashedPPOS/unleashed-superpowers` OR a tested symlink fallback.
7. Original skills remain functional throughout the transition — no regression.

## Out of scope for Phase 1

- Phase 2 borrowed-skill audit (separate work).
- n8n skills (separate repo later if wanted).
- Blog post / conference talk / upstream PR to `superpowers` — these are the strategic follow-up but are their own projects.
- CI/CD workflows in `.github/workflows/` — empty directory committed to reserve the space; actual workflows added later.
- Automated release versioning (semantic-release or similar) — manual bumps for now.

## Follow-up work (tracked, not in this plan)

- **Blog post** from the two-layer spec (content for discovery).
- **Plugin registry submission** — research whether Claude has a central plugin registry yet, submit if so.
- **Upstream PR** — propose `designing-ai-systems` to Jesse Vincent's `superpowers` plugin for universal distribution.
- **Phase 2 licensing audit** — track down sources of `ui-ux-pro-max`, `/ux-simplify`, `/ship-check`, `/create-command`, `/list-mcps`, `/evaluate-repository` (this one already known — awesome-claude-code).
- **Sync strategy** — decide how local edits propagate to the repo (direct commits in the cloned repo, then `claude plugins update`? or edits in `~/.claude/` that get `git push`-ed upstream manually?).

## Next step

Invoke `superpowers:writing-plans` to produce the task-by-task implementation plan.
