#!/usr/bin/env bash
# cloud-kit/install.sh — give a Claude Code CLOUD session the same rules, hooks,
# commands, skills and output style (High-Level) as Elliot's Mac.
#
# Cloud sessions never see ~/.claude from the Mac and don't install repo-declared
# plugins, so the cloud environment's setup script runs this once per VM image:
#
#   curl -fsSL https://raw.githubusercontent.com/UnleashedPPOS/unleashed-superpowers/main/cloud-kit/install.sh | bash -s -- --force
#
# (--force because the setup script runs before the session starts, so CLAUDE_CODE_REMOTE may not be set yet.)
#
# It also adds a SessionStart hook that re-runs itself in the background, so each
# new session picks up the latest kit from main. Fetches only from
# raw.githubusercontent.com (on the cloud Trusted allowlist). Refuses to run outside
# a cloud session unless --force, so it can't clobber a local ~/.claude.
set -uo pipefail

RAW="${CLOUD_KIT_RAW:-https://raw.githubusercontent.com/UnleashedPPOS/unleashed-superpowers/main}"
CL="$HOME/.claude"
case "$RAW" in
  https://raw.githubusercontent.com/UnleashedPPOS/*) ;;
  *) echo "cloud-kit: CLOUD_KIT_RAW must be under https://raw.githubusercontent.com/UnleashedPPOS/" >&2; exit 1 ;;
esac
command -v python3 >/dev/null 2>&1 || { echo "cloud-kit: python3 is required (settings merge + hooks)" >&2; exit 1; }

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ] && [ "${1:-}" != "--force" ]; then
  echo "cloud-kit: not a cloud session (CLAUDE_CODE_REMOTE!=true); pass --force to install anyway" >&2
  exit 0
fi

fetch() { curl -fsSL --retry 2 --max-time 20 "$RAW/$1"; }

manifest=$(fetch cloud-kit/MANIFEST) || { echo "cloud-kit: manifest fetch failed" >&2; exit 0; }

ok=0; bad=0; installed=""
while IFS= read -r path; do
  case "$path" in ''|'#'*|/*|../*|*/../*|*/..) continue ;; esac
  case "$path" in
    cloud-kit/rules/*) dest="$CL/rules/${path#cloud-kit/rules/}" ;;
    cloud-kit/hooks/*) dest="$CL/hooks/${path#cloud-kit/hooks/}" ;;
    cloud-kit/agents/*) dest="$CL/agents/${path#cloud-kit/agents/}" ;;
    commands/*|skills/*|output-styles/*) dest="$CL/$path" ;;
    *) continue ;;
  esac
  mkdir -p "$(dirname "$dest")"
  tmp=$(mktemp "$dest.XXXXXX")
  if fetch "$path" > "$tmp"; then mv "$tmp" "$dest"; ok=$((ok+1)); else rm -f "$tmp"; bad=$((bad+1)); fi
  installed+="$dest"$'\n'
done <<< "$manifest"
chmod +x "$CL"/hooks/*.py 2>/dev/null

# Remove files a previous kit installed that the current MANIFEST no longer lists.
list="$CL/.cloud-kit-files"
if [ -f "$list" ]; then
  while IFS= read -r old; do
    [ -n "$old" ] && case "$old" in "$CL"/*) grep -qxF "$old" <<< "$installed" || rm -f "$old" ;; esac
  done < "$list"
fi
printf '%s' "$installed" > "$list"

python3 - "$CL" "$RAW" <<'PY' || echo "cloud-kit: settings.json left untouched" >&2
import json, os, sys, tempfile
cl, raw = sys.argv[1], sys.argv[2]
p = os.path.join(cl, "settings.json")
if os.path.exists(p):
    try:
        s = json.load(open(p))
    except Exception:
        sys.exit("cloud-kit: settings.json does not parse; not overwriting it")
else:
    s = {}
s["outputStyle"] = "High-Level"
# 250000 is the kit value; the old kit default (200000) is upgraded, any other
# value the user chose is left alone.
if s.get("autoCompactWindow") in (None, 200000):
    s["autoCompactWindow"] = 250000
s.setdefault("env", {}).setdefault("CLAUDE_CODE_SUBAGENT_MODEL", "sonnet")
hooks = s.setdefault("hooks", {})

def ensure(event, key, command, **extra):
    """One kit hook per key: replace an earlier version in place, else append."""
    hook = dict(type="command", command=command, **extra)
    arr = hooks.setdefault(event, [])
    for m in arr:
        for i, h in enumerate(m.get("hooks", [])):
            if key in str(h.get("command", "")):
                m["hooks"][i] = hook
                return
    arr.append({"hooks": [hook]})

ensure("Stop", "/.claude/hooks/auto-ship-check.py", f'"{cl}/hooks/auto-ship-check.py"', timeout=10)
ensure("PostToolUse", "/.claude/hooks/context-size-nudge.py", f'"{cl}/hooks/context-size-nudge.py"', timeout=10)
ensure("SessionStart", "/cloud-kit/install.sh | bash", f"curl -fsSL {raw}/cloud-kit/install.sh | bash >/dev/null 2>&1",
       timeout=600, **{"async": True})
fd, tmp = tempfile.mkstemp(dir=cl, prefix=".settings.")
with os.fdopen(fd, "w") as f:
    json.dump(s, f, indent=2)
os.replace(tmp, p)
PY

# Plugins ship-check leans on (reviewer agents). Third-party marketplace pinned to a release tag:
# v1.10.0 is the last tag that still names the plugin everything-claude-code (v2 renamed it ecc,
# which would break the everything-claude-code:* agent names ship-check calls).
# Best-effort: skipped if the CLI or network refuses; retried next session until all succeed.
if command -v claude >/dev/null 2>&1 && [ ! -f "$CL/.cloud-kit-plugins" ]; then
  timeout 120 claude plugin marketplace add anthropics/claude-plugins-official >/dev/null 2>&1
  timeout 120 claude plugin install superpowers@claude-plugins-official >/dev/null 2>&1 && p1=1
  timeout 120 claude plugin marketplace add "affaan-m/everything-claude-code#v1.10.0" >/dev/null 2>&1
  timeout 120 claude plugin install everything-claude-code@everything-claude-code >/dev/null 2>&1 && p2=1
  [ -n "${p1:-}" ] && [ -n "${p2:-}" ] && touch "$CL/.cloud-kit-plugins"
fi

echo "cloud-kit: installed $ok files ($bad failed) into $CL"
[ "$bad" -eq 0 ] || echo "cloud-kit: WARNING $bad files failed to download; older copies (if any) kept" >&2
