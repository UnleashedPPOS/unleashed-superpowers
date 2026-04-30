# Unleashed Superpowers Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the `unleashed-superpowers` Claude Code plugin to `github.com/UnleashedPPOS/unleashed-superpowers` (public, MIT) containing Elliot's two confirmed originally-authored skills (`designing-ai-systems`, `document-feature-module`) and their commands, wire it back to local Claude Code, and remove the now-redundant local copies.

**Architecture:** A git repo mirroring the structure of Jesse Vincent's `superpowers` plugin (`.claude-plugin/plugin.json` + `marketplace.json`, `skills/`, `commands/`, standard README/LICENSE/CLAUDE.md). File contents are copied from their current locations (`~/.claude/skills/`, `~/.claude/commands/`, `~/Developer/unleashedos/.claude/`). Published via `gh repo create --public --source=. --push`. Local wiring tested first via `claude plugins install gh:UnleashedPPOS/unleashed-superpowers`; if unsupported in the user's Claude Code version, falls back to git clone + symlinks from `~/.claude/`.

**Tech Stack:** Git, GitHub CLI (`gh`), Markdown, JSON manifests. No code, no automated tests. Validation is by file existence, manifest JSON validity, successful git push, and a live regression test in a fresh Claude Code session.

---

## File Structure

**New files (in the new repo at `/Users/elliotkelly/Developer/unleashed-superpowers/`):**

```
unleashed-superpowers/
├── .claude-plugin/
│   ├── plugin.json                                        # Task 4
│   └── marketplace.json                                   # Task 4
├── skills/
│   ├── designing-ai-systems/SKILL.md                      # Task 5 (copy)
│   └── document-feature-module/SKILL.md                   # Task 5 (copy)
├── commands/
│   ├── ai-native-reframe.md                               # Task 6 (copy)
│   └── document-feature-module.md                         # Task 6 (copy)
├── docs/specs/
│   └── 2026-04-18-two-layer-ai-native-design.md           # Task 7 (copy)
├── .github/workflows/.gitkeep                             # Task 11
├── .gitignore                                             # Task 3
├── README.md                                              # Task 9
├── LICENSE                                                # Task 8
├── CLAUDE.md                                              # Task 10
├── AGENTS.md → CLAUDE.md (symlink)                        # Task 10
└── GEMINI.md                                              # Task 10
```

**Modified files (in the current worktree):**
- `tasks/lessons.md` — add a lesson about publishing (Task 18)
- `tasks/todo.md` — update the install-note section (Task 18)

**Source files (read-only copies):**
- `/Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md`
- `/Users/elliotkelly/.claude/commands/ai-native-reframe.md`
- `/Users/elliotkelly/Developer/unleashedos/.claude/skills/document-feature-module/SKILL.md`
- `/Users/elliotkelly/Developer/unleashedos/.claude/commands/document-feature-module.md`
- `/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21/docs/superpowers/specs/2026-04-18-two-layer-ai-native-design.md`

---

### Task 1: Preflight — verify gh auth and check for collisions

**Files:** none created; verification only.

- [ ] **Step 1: Verify gh CLI is authenticated as the expected user**

Run:
```bash
gh auth status 2>&1 | head -5
```
Expected: output contains `✓ Logged in to github.com account UnleashedPPOS` with `Active account: true`. If not, stop and tell the user to `gh auth login` as `UnleashedPPOS`.

- [ ] **Step 2: Confirm no existing GitHub repo named `unleashed-superpowers`**

Run:
```bash
gh repo view UnleashedPPOS/unleashed-superpowers 2>&1 | head -3
```
Expected: error `GraphQL: Could not resolve to a Repository` or similar "not found" output. If the repo already exists, stop and tell the user — this plan assumes fresh creation.

- [ ] **Step 3: Confirm no local directory collision**

Run:
```bash
ls -d /Users/elliotkelly/Developer/unleashed-superpowers 2>/dev/null && echo "EXISTS" || echo "OK, does not exist"
```
Expected: `OK, does not exist`. If `EXISTS`, stop — this plan creates that directory fresh.

- [ ] **Step 4: Confirm the source files exist**

Run:
```bash
ls -l \
  /Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md \
  /Users/elliotkelly/.claude/commands/ai-native-reframe.md \
  /Users/elliotkelly/Developer/unleashedos/.claude/skills/document-feature-module/SKILL.md \
  /Users/elliotkelly/Developer/unleashedos/.claude/commands/document-feature-module.md \
  "/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21/docs/superpowers/specs/2026-04-18-two-layer-ai-native-design.md"
```
Expected: all five files listed with non-zero size. If any is missing, stop and report.

---

### Task 2: Create local repo + git init

**Files:**
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/` (directory)

- [ ] **Step 1: Create the directory and initialise git**

Run:
```bash
mkdir -p /Users/elliotkelly/Developer/unleashed-superpowers
cd /Users/elliotkelly/Developer/unleashed-superpowers
git init -b main
```
Expected: `Initialized empty Git repository in /Users/elliotkelly/Developer/unleashed-superpowers/.git/`.

- [ ] **Step 2: Verify the initial branch is `main`**

Run:
```bash
cd /Users/elliotkelly/Developer/unleashed-superpowers && git symbolic-ref --short HEAD
```
Expected: `main`.

---

### Task 3: Write .gitignore

**Files:**
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/.gitignore`

- [ ] **Step 1: Write .gitignore**

Use the Write tool to create `/Users/elliotkelly/Developer/unleashed-superpowers/.gitignore` with this content:

```
# macOS
.DS_Store

# Editor
.vscode/
.idea/
*.swp

# Node (if any tooling added later)
node_modules/
*.log

# Local-only
.env
.env.local
```

- [ ] **Step 2: Verify the file**

Run:
```bash
wc -l /Users/elliotkelly/Developer/unleashed-superpowers/.gitignore
```
Expected: 12 or 13 lines.

---

### Task 4: Write plugin manifests

**Files:**
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/.claude-plugin/plugin.json`
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/.claude-plugin/marketplace.json`

- [ ] **Step 1: Create the directory**

Run:
```bash
mkdir -p /Users/elliotkelly/Developer/unleashed-superpowers/.claude-plugin
```

- [ ] **Step 2: Write plugin.json**

Use the Write tool to create `/Users/elliotkelly/Developer/unleashed-superpowers/.claude-plugin/plugin.json` with exactly this content:

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

- [ ] **Step 3: Write marketplace.json**

Use the Write tool to create `/Users/elliotkelly/Developer/unleashed-superpowers/.claude-plugin/marketplace.json` with exactly this content:

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

- [ ] **Step 4: Validate the JSON is well-formed**

Run:
```bash
python3 -m json.tool < /Users/elliotkelly/Developer/unleashed-superpowers/.claude-plugin/plugin.json > /dev/null && echo "plugin.json valid"
python3 -m json.tool < /Users/elliotkelly/Developer/unleashed-superpowers/.claude-plugin/marketplace.json > /dev/null && echo "marketplace.json valid"
```
Expected: two lines, `plugin.json valid` and `marketplace.json valid`. If either fails, fix the JSON syntax and re-run.

---

### Task 5: Copy the two skills

**Files:**
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/skills/designing-ai-systems/SKILL.md`
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/skills/document-feature-module/SKILL.md`

- [ ] **Step 1: Create the skills directories and copy designing-ai-systems**

Run:
```bash
mkdir -p /Users/elliotkelly/Developer/unleashed-superpowers/skills/designing-ai-systems
cp /Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md \
   /Users/elliotkelly/Developer/unleashed-superpowers/skills/designing-ai-systems/SKILL.md
```

- [ ] **Step 2: Copy document-feature-module**

Run:
```bash
mkdir -p /Users/elliotkelly/Developer/unleashed-superpowers/skills/document-feature-module
cp /Users/elliotkelly/Developer/unleashedos/.claude/skills/document-feature-module/SKILL.md \
   /Users/elliotkelly/Developer/unleashed-superpowers/skills/document-feature-module/SKILL.md
```

- [ ] **Step 3: Verify both files are byte-identical copies of their sources**

Run:
```bash
diff -q /Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md \
        /Users/elliotkelly/Developer/unleashed-superpowers/skills/designing-ai-systems/SKILL.md && \
  echo "designing-ai-systems identical"
diff -q /Users/elliotkelly/Developer/unleashedos/.claude/skills/document-feature-module/SKILL.md \
        /Users/elliotkelly/Developer/unleashed-superpowers/skills/document-feature-module/SKILL.md && \
  echo "document-feature-module identical"
```
Expected: two `identical` lines. `diff -q` outputs nothing when files match, so only the echoes print.

---

### Task 6: Copy the two commands

**Files:**
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/commands/ai-native-reframe.md`
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/commands/document-feature-module.md`

- [ ] **Step 1: Create the commands directory and copy ai-native-reframe**

Run:
```bash
mkdir -p /Users/elliotkelly/Developer/unleashed-superpowers/commands
cp /Users/elliotkelly/.claude/commands/ai-native-reframe.md \
   /Users/elliotkelly/Developer/unleashed-superpowers/commands/ai-native-reframe.md
```

- [ ] **Step 2: Copy document-feature-module command**

Run:
```bash
cp /Users/elliotkelly/Developer/unleashedos/.claude/commands/document-feature-module.md \
   /Users/elliotkelly/Developer/unleashed-superpowers/commands/document-feature-module.md
```

- [ ] **Step 3: Verify both files are byte-identical copies**

Run:
```bash
diff -q /Users/elliotkelly/.claude/commands/ai-native-reframe.md \
        /Users/elliotkelly/Developer/unleashed-superpowers/commands/ai-native-reframe.md && \
  echo "ai-native-reframe identical"
diff -q /Users/elliotkelly/Developer/unleashedos/.claude/commands/document-feature-module.md \
        /Users/elliotkelly/Developer/unleashed-superpowers/commands/document-feature-module.md && \
  echo "document-feature-module identical"
```
Expected: two `identical` lines.

---

### Task 7: Copy the companion spec doc

**Files:**
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/docs/specs/2026-04-18-two-layer-ai-native-design.md`

- [ ] **Step 1: Create the docs/specs directory and copy the spec**

Run:
```bash
mkdir -p /Users/elliotkelly/Developer/unleashed-superpowers/docs/specs
cp "/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21/docs/superpowers/specs/2026-04-18-two-layer-ai-native-design.md" \
   /Users/elliotkelly/Developer/unleashed-superpowers/docs/specs/2026-04-18-two-layer-ai-native-design.md
```

- [ ] **Step 2: Verify the copy matches the source**

Run:
```bash
diff -q "/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21/docs/superpowers/specs/2026-04-18-two-layer-ai-native-design.md" \
        /Users/elliotkelly/Developer/unleashed-superpowers/docs/specs/2026-04-18-two-layer-ai-native-design.md && \
  echo "spec doc identical"
```
Expected: `spec doc identical`.

---

### Task 8: Write LICENSE (MIT)

**Files:**
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/LICENSE`

- [ ] **Step 1: Write the MIT LICENSE**

Use the Write tool to create `/Users/elliotkelly/Developer/unleashed-superpowers/LICENSE` with exactly this content:

```
MIT License

Copyright (c) 2026 Elliot Kelly

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

- [ ] **Step 2: Verify**

Run:
```bash
wc -l /Users/elliotkelly/Developer/unleashed-superpowers/LICENSE
grep -c "Elliot Kelly" /Users/elliotkelly/Developer/unleashed-superpowers/LICENSE
```
Expected: 21 lines, 1 match for "Elliot Kelly".

---

### Task 9: Write README.md

**Files:**
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/README.md`

- [ ] **Step 1: Write README.md**

Use the Write tool to create `/Users/elliotkelly/Developer/unleashed-superpowers/README.md` with exactly this content:

```markdown
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

**`/ai-native-reframe`** — Mid-session audit. Takes the current AI-system design and produces structured output with five sections: ENGINE, PRESENTATION, BRIDGE, GAPS, 48-HOUR PROTOTYPE.

**`/document-feature-module <target>`** — Thin wrapper that invokes the `document-feature-module` skill against a target module.

## Roadmap

- **Phase 2** — audit and add (with attribution) a set of currently-held skills: `ui-ux-pro-max`, `/ux-simplify`, `/ship-check`, `/create-command`, `/list-mcps`, `/evaluate-repository`.
- **Upstream** — propose `designing-ai-systems` as a PR to [Jesse Vincent's `superpowers` plugin](https://github.com/obra/superpowers) for universal distribution.
- **Content** — turn the two-layer design spec into a blog post / conference talk.

## Contributing

See [CLAUDE.md](CLAUDE.md) for the contribution style guide (how to add a skill, naming rules, frontmatter requirements, trigger-phrase design).

## License

MIT. Copyright (c) 2026 Elliot Kelly.

## Author

Elliot Kelly — [Unleashed](https://unleashed.vision). Opinions on AI-system design are mine; the tools that enforce them are in this repo.
```

- [ ] **Step 2: Verify**

Run:
```bash
wc -l /Users/elliotkelly/Developer/unleashed-superpowers/README.md
head -3 /Users/elliotkelly/Developer/unleashed-superpowers/README.md
```
Expected: around 90 lines. First line: `# Unleashed Superpowers`.

---

### Task 10: Write CLAUDE.md, AGENTS.md symlink, and GEMINI.md stub

**Files:**
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/CLAUDE.md`
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/AGENTS.md` (symlink to CLAUDE.md)
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/GEMINI.md`

- [ ] **Step 1: Write CLAUDE.md**

Use the Write tool to create `/Users/elliotkelly/Developer/unleashed-superpowers/CLAUDE.md` with exactly this content:

```markdown
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
```

- [ ] **Step 2: Create AGENTS.md symlink pointing to CLAUDE.md**

Run:
```bash
cd /Users/elliotkelly/Developer/unleashed-superpowers && ln -s CLAUDE.md AGENTS.md
ls -la /Users/elliotkelly/Developer/unleashed-superpowers/AGENTS.md
```
Expected: output shows `AGENTS.md -> CLAUDE.md`.

- [ ] **Step 3: Write GEMINI.md stub**

Use the Write tool to create `/Users/elliotkelly/Developer/unleashed-superpowers/GEMINI.md` with exactly this content:

```markdown
# GEMINI.md

See [CLAUDE.md](CLAUDE.md) for the contribution guide. Same instructions apply for Gemini CLI usage.
```

- [ ] **Step 4: Verify all three files exist**

Run:
```bash
ls -la /Users/elliotkelly/Developer/unleashed-superpowers/CLAUDE.md \
       /Users/elliotkelly/Developer/unleashed-superpowers/AGENTS.md \
       /Users/elliotkelly/Developer/unleashed-superpowers/GEMINI.md
```
Expected: CLAUDE.md regular file, AGENTS.md symlink to CLAUDE.md, GEMINI.md regular file.

---

### Task 11: Create .github/workflows/ placeholder

**Files:**
- Create: `/Users/elliotkelly/Developer/unleashed-superpowers/.github/workflows/.gitkeep`

- [ ] **Step 1: Create the directory and placeholder**

Run:
```bash
mkdir -p /Users/elliotkelly/Developer/unleashed-superpowers/.github/workflows
touch /Users/elliotkelly/Developer/unleashed-superpowers/.github/workflows/.gitkeep
```

- [ ] **Step 2: Verify**

Run:
```bash
ls -la /Users/elliotkelly/Developer/unleashed-superpowers/.github/workflows/
```
Expected: `.gitkeep` file (empty) present.

---

### Task 12: Initial commit (local)

**Files:** all files above are staged and committed.

- [ ] **Step 1: Verify the full tree looks right before committing**

Run:
```bash
cd /Users/elliotkelly/Developer/unleashed-superpowers && find . -type f -o -type l | grep -v "^./.git/" | sort
```
Expected: all of these paths listed (order may vary):
```
./.claude-plugin/marketplace.json
./.claude-plugin/plugin.json
./.github/workflows/.gitkeep
./.gitignore
./AGENTS.md
./CLAUDE.md
./GEMINI.md
./LICENSE
./README.md
./commands/ai-native-reframe.md
./commands/document-feature-module.md
./docs/specs/2026-04-18-two-layer-ai-native-design.md
./skills/designing-ai-systems/SKILL.md
./skills/document-feature-module/SKILL.md
```

If anything is missing or extra, stop and fix before committing.

- [ ] **Step 2: Stage and commit**

Run:
```bash
cd /Users/elliotkelly/Developer/unleashed-superpowers && \
  git add -A && \
  git status
```
Expected: all 14 files listed as `new file`.

Then commit:
```bash
cd /Users/elliotkelly/Developer/unleashed-superpowers && \
  git commit -m "feat: initial plugin scaffold

Ships designing-ai-systems skill (four-pass AI-native reframe) and
document-feature-module skill (reference-quality feature docs). Plus
corresponding slash commands and the two-layer design spec as the
citable 'why' behind designing-ai-systems.

Structure mirrors Jesse Vincent's superpowers plugin: .claude-plugin/
manifests, skills/, commands/, docs/specs/. MIT licensed."
```

- [ ] **Step 3: Verify the commit**

Run:
```bash
cd /Users/elliotkelly/Developer/unleashed-superpowers && git log --oneline
```
Expected: one line starting with the short SHA and `feat: initial plugin scaffold`.

---

### Task 13: Create GitHub repo and push

**Files:** none local; creates remote GitHub repository.

- [ ] **Step 1: Create the remote public repo and push**

Run:
```bash
cd /Users/elliotkelly/Developer/unleashed-superpowers && \
  gh repo create unleashed-superpowers \
    --public \
    --source=. \
    --push \
    --description "AI-native design skills for Claude Code. Anthropomorphic surface, AI-native engine, event-log bridge."
```
Expected output ends with something like `https://github.com/UnleashedPPOS/unleashed-superpowers` and a successful push message.

- [ ] **Step 2: Verify the remote repo exists and is public**

Run:
```bash
gh repo view UnleashedPPOS/unleashed-superpowers --json name,visibility,description,url
```
Expected: JSON with `"name":"unleashed-superpowers"`, `"visibility":"PUBLIC"`, the description string, and the URL.

- [ ] **Step 3: Verify the initial commit is on the remote**

Run:
```bash
gh api repos/UnleashedPPOS/unleashed-superpowers/commits --jq '.[0].commit.message' | head -1
```
Expected: `feat: initial plugin scaffold`.

---

### Task 14: Test the preferred install mechanism

**Files:** none; verification only.

- [ ] **Step 1: Attempt `claude plugins install` from the git URL**

Run:
```bash
claude plugins install gh:UnleashedPPOS/unleashed-superpowers 2>&1 | tee /tmp/claude-plugin-install.log
```
Expected: either a success message AND a new directory appears under `~/.claude/plugins/cache/` containing the plugin, OR a clear error message (e.g. "command 'plugins' not recognised," "install source not supported," or similar).

- [ ] **Step 2: Determine whether Option 1 (plugin install) worked**

Run:
```bash
ls /Users/elliotkelly/.claude/plugins/cache/ 2>/dev/null | grep -i unleashed && echo "INSTALLED" || echo "NOT_INSTALLED"
```

- If output is `INSTALLED` → record success. Skip Task 15 (symlink fallback). Proceed to Task 16.
- If output is `NOT_INSTALLED` → the plugin-install-from-git flow did not work in this Claude Code version. Proceed to Task 15.

---

### Task 15: Fallback — install via git clone + symlinks (ONLY IF Task 14 failed)

**Skip this entire task if Task 14 reported `INSTALLED`.**

**Files:**
- Create: symlinks in `~/.claude/skills/` and `~/.claude/commands/` pointing into the cloned repo.

- [ ] **Step 1: Confirm the clone location**

The local repo already exists at `/Users/elliotkelly/Developer/unleashed-superpowers/` from Task 2 — no separate clone needed. The symlinks will point at this directory.

Run:
```bash
ls -d /Users/elliotkelly/Developer/unleashed-superpowers && echo "OK, source tree present"
```
Expected: `OK, source tree present`.

- [ ] **Step 2: Remove the old local copies and replace with symlinks**

First verify the old copies exist (we're about to replace them):
```bash
ls -la /Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md \
       /Users/elliotkelly/.claude/commands/ai-native-reframe.md
```
Expected: both files listed.

Then replace with symlinks:
```bash
rm -rf /Users/elliotkelly/.claude/skills/designing-ai-systems
ln -s /Users/elliotkelly/Developer/unleashed-superpowers/skills/designing-ai-systems \
      /Users/elliotkelly/.claude/skills/designing-ai-systems

ln -s /Users/elliotkelly/Developer/unleashed-superpowers/skills/document-feature-module \
      /Users/elliotkelly/.claude/skills/document-feature-module

rm /Users/elliotkelly/.claude/commands/ai-native-reframe.md
ln -s /Users/elliotkelly/Developer/unleashed-superpowers/commands/ai-native-reframe.md \
      /Users/elliotkelly/.claude/commands/ai-native-reframe.md

ln -s /Users/elliotkelly/Developer/unleashed-superpowers/commands/document-feature-module.md \
      /Users/elliotkelly/.claude/commands/document-feature-module.md
```

- [ ] **Step 3: Verify symlinks resolve correctly**

Run:
```bash
for p in ~/.claude/skills/designing-ai-systems/SKILL.md \
         ~/.claude/skills/document-feature-module/SKILL.md \
         ~/.claude/commands/ai-native-reframe.md \
         ~/.claude/commands/document-feature-module.md; do
  if [ -r "$p" ]; then echo "OK $p"; else echo "FAIL $p"; fi
done
```
Expected: four `OK` lines. If any `FAIL`, stop and debug the symlink target.

Note: because Task 15 was taken (plugin install failed), the cleanup step in Task 17 becomes a no-op for user-level files — they're already replaced by symlinks here. The unleashedos project-level copies of `document-feature-module` are NOT removed.

---

### Task 16: Regression test in a fresh Claude Code session (USER-RUN)

**This task must be run by the human user, not by a subagent.** A subagent in the current session cannot validate that a NEW session picks up the plugin — skill registries load at session start.

**Files:** none.

- [ ] **Step 1: User opens a fresh Claude Code session**

The user opens a new Claude Code session. Not a subagent invocation — a genuinely new top-level session, in any directory.

- [ ] **Step 2: User issues the designing-ai-systems trigger prompt**

User pastes verbatim:

> I want to build a team of 50 AI researchers that each cover a different topic, and they'll each have a senior reviewer agent to sign off their work. Can you help me design this? I think it'll take about 2-3 weeks.

Expected: Claude invokes the `designing-ai-systems` skill (visible as a Skill tool call or an explicit "I'm using the designing-ai-systems skill..." announcement) and produces output covering the four passes.

- [ ] **Step 3: User invokes /ai-native-reframe**

In the same or another fresh session, user pastes a small design and then `/ai-native-reframe`. Expected: structured output with ENGINE / PRESENTATION / BRIDGE / GAPS / 48-HOUR PROTOTYPE sections.

- [ ] **Step 4: User invokes /document-feature-module**

In a fresh session opened inside any codebase, user runs `/document-feature-module <some-folder>`. Expected: the skill loads and asks clarifying questions about the target module.

- [ ] **Step 5: User reports back**

User reports which tests passed or failed. If all pass, proceed to Task 17. If any fail:

- **Skill does not auto-invoke** → the `description` field may need more trigger phrases. Edit in the repo, commit, push. Go back to Task 14 to reinstall.
- **Skill invokes but output is wrong** → the skill body needs edits. Same fix loop.
- **Command does not appear** → check `~/.claude/commands/` (or the plugin cache) contains the file. Re-do Task 14 or 15.

Do NOT proceed to Task 17 until Task 16 reports success on all three tests.

---

### Task 17: Remove old user-level copies (after Task 16 passes)

**Files:**
- Delete (if Task 14 succeeded): `/Users/elliotkelly/.claude/skills/designing-ai-systems/` and `/Users/elliotkelly/.claude/commands/ai-native-reframe.md`
- No-op (if Task 15 was taken): those paths are already symlinks to the repo.

- [ ] **Step 1: Determine which branch Task 14 took**

Check if the plugin install worked:
```bash
ls /Users/elliotkelly/.claude/plugins/cache/ 2>/dev/null | grep -i unleashed && echo "PLUGIN_INSTALLED" || echo "SYMLINKS_USED"
```

- If `PLUGIN_INSTALLED` → continue to Step 2.
- If `SYMLINKS_USED` → skip Step 2 and 3, go directly to Step 4.

- [ ] **Step 2 (ONLY IF `PLUGIN_INSTALLED`): Verify the plugin cache has the skill before removing the old copy**

Run:
```bash
find /Users/elliotkelly/.claude/plugins/cache/ -name "SKILL.md" -path "*designing-ai-systems*" | head -3
find /Users/elliotkelly/.claude/plugins/cache/ -name "ai-native-reframe.md" | head -3
```
Expected: at least one result for each. If either is empty, STOP — do not remove the old copy.

- [ ] **Step 3 (ONLY IF `PLUGIN_INSTALLED`): Remove the old user-level copies**

Run:
```bash
rm -rf /Users/elliotkelly/.claude/skills/designing-ai-systems
rm /Users/elliotkelly/.claude/commands/ai-native-reframe.md
```

Verify:
```bash
ls /Users/elliotkelly/.claude/skills/designing-ai-systems 2>/dev/null && echo "STILL EXISTS — problem" || echo "OK, removed"
ls /Users/elliotkelly/.claude/commands/ai-native-reframe.md 2>/dev/null && echo "STILL EXISTS — problem" || echo "OK, removed"
```
Expected: two `OK, removed` lines.

- [ ] **Step 4: Final regression check**

Run a quick listing:
```bash
ls /Users/elliotkelly/.claude/skills/ | grep -E "designing-ai-systems|document-feature-module"
ls /Users/elliotkelly/.claude/commands/ | grep -E "ai-native-reframe|document-feature-module"
```

- If `PLUGIN_INSTALLED`: expect no direct listings (skills served from plugin cache).
- If `SYMLINKS_USED`: expect both skills and both commands to appear (as symlinks).

Either way is correct. The goal is the user's skill registry sees them — which Task 16 already confirmed.

---

### Task 18: Update worktree lessons.md and todo.md

**Files:**
- Modify: `/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21/tasks/lessons.md`
- Modify: `/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21/tasks/todo.md`

- [ ] **Step 1: Append a lesson about publishing the plugin**

Using the Edit tool, append the following to the end of `tasks/lessons.md`:

```

## 2026-04-18 — Publish reusable skills as a Claude plugin, not as dotfiles

**Pattern:** When I wanted the `designing-ai-systems` skill "available everywhere," my first instinct was a private dotfiles repo with symlinks. That solves my personal machine-switching problem and nothing else. The founder-frame move is to publish it as a public Claude Code plugin so anyone who needs the idea can install it with one command — and to propose it upstream to the `superpowers` plugin for universal distribution.

**Rule:** For any skill or command I author that has generic value (not tied to a specific product codebase), the target is: public Claude Code plugin at a GitHub repo I own, MIT-licensed, with trigger phrases designed for auto-invocation, and a companion design spec that argues the "why." Only keep skills in `~/.claude/` directly while they're in draft. Once a skill is stable, move it into the public plugin repo and let `claude plugins install` (or a symlink fallback) serve it.

**Example:** `designing-ai-systems` + `document-feature-module` → `github.com/UnleashedPPOS/unleashed-superpowers` v0.1.0. Phase 2 adds ambiguous-authorship skills after licensing audit. Upstream: propose `designing-ai-systems` as a PR to Jesse Vincent's `superpowers` plugin once it's been road-tested.

---
```

- [ ] **Step 2: Update the todo.md install note from the previous plan**

The previous plan (designing-ai-systems install) appended a section to `tasks/todo.md` titled "## 2026-04-18 — Skill + command installed (not git-tracked)". That note is now stale because the skill IS git-tracked in the new repo.

Using the Edit tool on `tasks/todo.md`, REPLACE the old section:

```
## 2026-04-18 — Skill + command installed (not git-tracked)

The `designing-ai-systems` skill and `/ai-native-reframe` command are installed at:

- `/Users/elliotkelly/.claude/skills/designing-ai-systems/SKILL.md`
- `/Users/elliotkelly/.claude/commands/ai-native-reframe.md`

`~/.claude/` is not currently a git repo. If later setting up a dotfiles repo for it, copy these two files in and commit. Also consider symlinking via `~/.agents/skills/` to match the pattern used by vendor skills.

---
```

...with this updated section:

```
## 2026-04-18 — designing-ai-systems + document-feature-module published

Both skills and their slash commands now live in the public plugin repo at `github.com/UnleashedPPOS/unleashed-superpowers` (v0.1.0, MIT). The local `~/.claude/` copies are either served from the plugin cache (if `claude plugins install` worked) or symlinked into the cloned repo at `~/Developer/unleashed-superpowers/` (fallback).

Follow-ups tracked separately:

- Phase 2: audit and add ambiguous-authorship skills (`ui-ux-pro-max`, `/ux-simplify`, `/ship-check`, `/create-command`, `/list-mcps`, `/evaluate-repository`) after licensing review.
- Upstream: propose `designing-ai-systems` as a PR to Jesse Vincent's `superpowers` plugin.
- Content: turn the two-layer design spec into a blog post / conference talk.
- Consider `unleashed-n8n` as a separate plugin repo for the seven n8n skills.

---
```

- [ ] **Step 3: Commit both changes in the worktree**

Run:
```bash
cd "/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21" && \
  git add tasks/lessons.md tasks/todo.md && \
  git commit -m "docs: record plugin-publication lesson and update install note

Replaces the prior 'skill installed, not git-tracked' todo entry with
the new state: designing-ai-systems and document-feature-module are
now served from the unleashed-superpowers plugin repo.

Adds a lesson capturing the 'publish as plugin, not as dotfiles'
pattern for future reusable skills."
```

Verify:
```bash
cd "/Users/elliotkelly/Developer/Claude code/.claude/worktrees/funny-haslett-30db21" && git log -1 --oneline
```
Expected: one line ending in `docs: record plugin-publication lesson ...`.

---

## Self-review

**1. Spec coverage check:**
- Phase 1 contents (2 skills + 2 commands) → Tasks 5, 6 ✓
- Phase 2 backlog noted → covered in README roadmap (Task 9) + todo.md update (Task 18) ✓
- Repo structure matches superpowers pattern → Tasks 2–11 enumerate every file ✓
- Manifest content (plugin.json + marketplace.json) → Task 4 ✓
- README shape (9 sections) → Task 9 content ✓
- Licensing and attribution policy → LICENSE in Task 8, CLAUDE.md section in Task 10, CREDITS.md policy deferred to Phase 2 ✓
- Install mechanism (plugins install primary + symlink fallback) → Tasks 14, 15 ✓
- Branding / naming (UnleashedPPOS account, `unleashed-superpowers` repo name) → Task 13 ✓
- Duplicate-resolution policy (for Phase 2 later) → not needed in Phase 1, spec noted it as deferred ✓
- Success criteria (7 items) → Task 12 verify step, Task 13 steps, Task 16 regression ✓
- Transition safety (keep old copies until plugin verified) → Task 17 gated on Task 14+16 results ✓

**2. Placeholder scan:** No TBDs or vague requirements. All file contents included inline. No "similar to Task N" references. Every verify command has an explicit expected output.

**3. Type consistency:** File paths absolute and consistent throughout. `UnleashedPPOS` used consistently as the GitHub account. `unleashed-superpowers` repo name consistent. Task 15 and Task 17 branch on the same variable (whether plugin install worked); the check is worded identically in both (`ls /Users/elliotkelly/.claude/plugins/cache/ | grep -i unleashed`).

No issues found. Plan ready for execution.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-18-unleashed-superpowers-plugin.md`. Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Good for this plan because the tasks are independent file ops + manifest writes + git/gh operations, and Task 16 requires you to run the regression check in a fresh session anyway.

**2. Inline Execution** — I execute tasks in this session with checkpoints between. Same caveat: Task 16 requires a fresh session and is yours regardless.

Which approach?
