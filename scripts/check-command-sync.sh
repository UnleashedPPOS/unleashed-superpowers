#!/usr/bin/env bash
# check-command-sync.sh — guards against red-team / definition-of-done content drift.
#
# This repo is markdown-only (no package.json, no CI). /red-team, /dod, and
# /ship-check Stage 2 / Stage 3 must share ONE source of truth per stage:
#   - skills/red-team/SKILL.md            (red-team methodology)
#   - skills/definition-of-done/SKILL.md  (DoD ledger)
#
# commands/red-team.md and commands/dod.md must stay THIN WRAPPERS that load
# the skill rather than re-deriving its content, and commands/ship-check.md
# must reference those same skills for Stage 2 / Stage 3 rather than
# duplicating their phase-by-phase bodies. This script fails the build if any
# of that drifts.
#
# Run: bash scripts/check-command-sync.sh

set -euo pipefail
cd "$(dirname "$0")/.."

fail=0

check_wrapper_is_thin() {
  local file="$1" skill_ref="$2" max_lines="$3"
  if [ ! -f "$file" ]; then
    echo "FAIL: $file is missing"
    fail=1
    return
  fi
  local lines
  lines=$(wc -l < "$file")
  if [ "$lines" -gt "$max_lines" ]; then
    echo "FAIL: $file has $lines lines (> $max_lines) — it should be a thin wrapper that loads $skill_ref, not a re-derivation of it"
    fail=1
  fi
  if ! grep -q "$skill_ref" "$file"; then
    echo "FAIL: $file does not reference $skill_ref — commands must load the skill, not duplicate it"
    fail=1
  fi
}

check_no_duplicated_phase_headers() {
  local file="$1" skill_file="$2"
  # A duplicated phase header (e.g. "## Phase 0 — Build the Claim Ledger") in
  # a command file that should be a thin wrapper is a strong drift signal.
  local dupes
  dupes=$(grep -F -f <(grep -E '^## Phase [0-9]' "$skill_file") "$file" 2>/dev/null || true)
  if [ -n "$dupes" ]; then
    echo "FAIL: $file duplicates phase headers from $skill_file:"
    echo "$dupes" | sed 's/^/  /'
    fail=1
  fi
}

check_wrapper_is_thin "commands/red-team.md" "skills/red-team/SKILL.md" 20
check_wrapper_is_thin "commands/dod.md" "skills/definition-of-done/SKILL.md" 20

check_no_duplicated_phase_headers "commands/red-team.md" "skills/red-team/SKILL.md"

# ship-check.md is intentionally long (Stage 1 is its own content), but its
# Stage 2 / Stage 3 sections must reference the skills rather than restate
# their phase headers.
if ! grep -q "skills/red-team/SKILL.md" commands/ship-check.md; then
  echo "FAIL: commands/ship-check.md does not reference skills/red-team/SKILL.md for Stage 2"
  fail=1
fi
if ! grep -q "skills/definition-of-done/SKILL.md" commands/ship-check.md; then
  echo "FAIL: commands/ship-check.md does not reference skills/definition-of-done/SKILL.md for Stage 3"
  fail=1
fi

if [ "$fail" -eq 0 ]; then
  echo "OK: red-team / definition-of-done stay single-sourced in skills/, commands stay thin wrappers or references."
else
  echo
  echo "One or more command files have drifted from their source-of-truth skill. Fix the skill file, then re-point the command at it — do not re-derive content in the command."
fi

exit "$fail"
