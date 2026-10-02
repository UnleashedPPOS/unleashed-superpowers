# cloud-kit

Gives Claude Code **cloud sessions** the same rules, hooks, commands, skills, output style and
reviewer plugins as the Mac. Cloud sessions never see `~/.claude` from the Mac, so this is how
`/ship-check`, the auto-ship-check Stop hook and the token rules reach them.

## Setup (once per cloud environment)

Paste into the environment's **Setup script** (claude.ai/code → environment selector → settings):

```bash
curl -fsSL https://raw.githubusercontent.com/UnleashedPPOS/unleashed-superpowers/main/cloud-kit/install.sh | bash -s -- --force
```

`--force` is needed because the setup script runs before the session, where `CLAUDE_CODE_REMOTE`
may not be set yet. Without `--force` the installer refuses to run anywhere but a cloud session.

## What it does

- Downloads the `MANIFEST` paths under these five trees (from `main`): `cloud-kit/rules/*` → `~/.claude/rules/`,
  `cloud-kit/hooks/*` → `~/.claude/hooks/`, `commands/`, `skills/` and `output-styles/` → `~/.claude/`.
- Prunes files a previous run installed that `MANIFEST` no longer lists (`~/.claude/.cloud-kit-files`).
- Merges `~/.claude/settings.json`: forces the High-Level output style (`output-styles/high-level.md`); sets `autoCompactWindow` to 250000 (if unset or still the old
  200000 default) and Sonnet sub-agents only if unset; and adds the Stop / PostToolUse / SessionStart hooks (replaced in place on upgrade, never duplicated).
  An unparseable settings file is left untouched.
- The SessionStart hook re-runs the installer in the background, so each session gets the latest kit.
- Installs the `superpowers` and `everything-claude-code` (pinned `v1.10.0`) plugins once.

## Maintaining

After adding or removing a rule, hook, command or skill file:

```bash
bash scripts/build-cloud-manifest.sh
```

`scripts/check-command-sync.sh` fails if `MANIFEST` is stale (run it before committing; the repo has no CI workflow).
