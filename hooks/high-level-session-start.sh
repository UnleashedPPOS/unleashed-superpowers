#!/usr/bin/env bash
# SessionStart hook: when High-Level mode is switched on, load its rules into every new
# session (CLI, desktop app, IDE), after /clear and after compaction. Output styles
# can't do this: the desktop app fixes a session's style when it starts.
# Runs on startup, /clear and compaction; a resumed chat already has the rules.
#
# On when either is true:
#   - the flag file exists: ~/.claude/high-level-mode   (created by /high-level-mode on)
#   - HIGH_LEVEL_MODE=1 is in the environment
# HIGH_LEVEL_MODE=0 forces it off for one session.
#
# The rules come from output-styles/high-level.md, so the style and the hook never drift.
set -u
flag="${HOME:-}/.claude/high-level-mode"
case "${HIGH_LEVEL_MODE:-}" in
  0) exit 0 ;;
  1) ;;
  *) [ -f "$flag" ] || exit 0 ;;
esac

root="${CLAUDE_PLUGIN_ROOT:-$(cd "$(dirname "$0")/.." && pwd)}"
style="$root/output-styles/high-level.md"
[ -f "$style" ] || exit 0

echo "High-Level mode is ON for this session (turn off with /high-level-mode off). Follow these reporting rules for every reply:"
echo
# Print the style body without its YAML frontmatter.
# Tolerates CRLF line endings.
awk '{sub(/\r$/, "")} NR==1 && $0=="---" {fm=1; next} fm && $0=="---" {fm=0; next} !fm' "$style"
