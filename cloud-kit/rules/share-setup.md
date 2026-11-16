# Share every setup change through unleashed-superpowers (HARD RULE, 2026-10-02)

Founder: other people should be able to have the same setup, "and the same goes for any and all things we do to our setup".

- A session that changes how Claude works (rule, hook, skill, command, output style, correction check, or a fix to one) ships a shareable copy to `UnleashedPPOS/unleashed-superpowers` in the same job: skills → `skills/<name>/SKILL.md`, commands → `commands/`, output styles → `output-styles/`, rules → `cloud-kit/rules/`, hooks → `cloud-kit/hooks/`, corrections → `cloud-kit/hooks/corrections.json` (via `/learnings`).
- Then `bash scripts/build-cloud-manifest.sh`, bump `.claude-plugin/plugin.json` and `marketplace.json`, add a README line, run `claude plugin validate .`, open a PR, /ship-check, merge.
- Strip anything personal first: secrets, phone numbers, customer names, private hosts, vault key names. Rules that only fit Unleashed's own infrastructure stay in `~/.claude/rules/`.
- Not shareable: the vault, memory files, handoffs, project-specific CLAUDE.md content.
