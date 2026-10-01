# Share every setup change through unleashed-superpowers (HARD RULE, 2026-10-02)

Founder 2026-10-02: other people should be able to have the same setup, "and the same goes for
any and all things we do to our setup".

When a session changes how Claude works for the founder (a new rule, hook, skill, command, output
style, or a fix to one), ship a shareable copy to `UnleashedPPOS/unleashed-superpowers` in the same job:
- Skills → `skills/<name>/SKILL.md`. Commands → `commands/<name>.md`. Output styles → `output-styles/<name>.md`.
- Standing rules → `cloud-kit/rules/`. Hooks → `cloud-kit/hooks/`.
- Then run `bash scripts/build-cloud-manifest.sh`, bump `.claude-plugin/plugin.json` (and the plugin
  entry in `marketplace.json`), add a README line, open a PR, run /ship-check, and merge.
- Strip anything personal before it goes in: secrets, phone numbers, customer names, private hosts,
  vault key names. Rules that only make sense for Unleashed's own infrastructure stay in `~/.claude/rules/`.
- Validate with `claude plugin validate .` before the PR.

Not shareable: the vault itself, memory files, handoffs, and project-specific CLAUDE.md content.
