#!/usr/bin/env bash
# cloud-kit/install.sh — give a Claude Code CLOUD session the same rules, hooks,
# commands, skills and output style as Elliot's Mac.
#
# Cloud sessions never see ~/.claude from the Mac and don't install repo-declared
# plugins, so the cloud environment's setup script runs this once per VM image:
#
#   curl -fsSL https://raw.githubusercontent.com/UnleashedPPOS/unleashed-superpowers/main/cloud-kit/install.sh | bash
#
# It also adds a SessionStart hook that re-runs itself in the background, so each
# new session picks up the latest kit from main. Fetches only from
# raw.githubusercontent.com (on the cloud Trusted allowlist). Refuses to run outside
# a cloud session unless --force, so it can't clobber a local ~/.claude.
set -uo pipefail

RAW="${CLOUD_KIT_RAW:-https://raw.githubusercontent.com/UnleashedPPOS/unleashed-superpowers/main}"
CL="$HOME/.claude"

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ] && [ "${1:-}" != "--force" ]; then
  echo "cloud-kit: not a cloud session (CLAUDE_CODE_REMOTE!=true); pass --force to install anyway" >&2
  exit 0
fi

fetch() { curl -fsSL --retry 2 --max-time 20 "$RAW/$1"; }

manifest=$(fetch cloud-kit/MANIFEST) || { echo "cloud-kit: manifest fetch failed" >&2; exit 0; }

ok=0; bad=0
while IFS= read -r path; do
  case "$path" in ''|'#'*) continue ;; esac
  case "$path" in
    cloud-kit/rules/*) dest="$CL/rules/${path#cloud-kit/rules/}" ;;
    cloud-kit/hooks/*) dest="$CL/hooks/${path#cloud-kit/hooks/}" ;;
    commands/*|skills/*) dest="$CL/$path" ;;
    *) continue ;;
  esac
  mkdir -p "$(dirname "$dest")"
  if fetch "$path" > "$dest.tmp"; then mv "$dest.tmp" "$dest"; ok=$((ok+1)); else rm -f "$dest.tmp"; bad=$((bad+1)); fi
done <<< "$manifest"
chmod +x "$CL"/hooks/*.py 2>/dev/null

python3 - "$CL" <<'PY'
import json, os, sys
cl = sys.argv[1]
p = os.path.join(cl, "settings.json")
try:
    s = json.load(open(p))
except Exception:
    s = {}
s["outputStyle"] = "Concise"
s.setdefault("autoCompactWindow", 200000)
s.setdefault("env", {}).setdefault("CLAUDE_CODE_SUBAGENT_MODEL", "sonnet")
hooks = s.setdefault("hooks", {})

def ensure(event, command, **extra):
    arr = hooks.setdefault(event, [])
    if any(command == h.get("command") for m in arr for h in m.get("hooks", [])):
        return
    arr.append({"hooks": [dict(type="command", command=command, **extra)]})

ensure("Stop", f"{cl}/hooks/auto-ship-check.py", timeout=10)
ensure("PostToolUse", f"{cl}/hooks/context-size-nudge.py", timeout=10)
ensure("SessionStart",
       "curl -fsSL https://raw.githubusercontent.com/UnleashedPPOS/unleashed-superpowers/main/cloud-kit/install.sh | bash >/dev/null 2>&1",
       timeout=60, **{"async": True})
json.dump(s, open(p, "w"), indent=2)
PY

# Plugins ship-check leans on (reviewer agents). Best-effort: skipped if the CLI or network refuses.
if command -v claude >/dev/null 2>&1 && [ ! -f "$CL/.cloud-kit-plugins" ]; then
  timeout 120 claude plugin marketplace add anthropics/claude-plugins-official >/dev/null 2>&1
  timeout 120 claude plugin install superpowers@claude-plugins-official >/dev/null 2>&1
  timeout 120 claude plugin marketplace add affaan-m/everything-claude-code >/dev/null 2>&1
  timeout 120 claude plugin install everything-claude-code@everything-claude-code >/dev/null 2>&1 \
    && touch "$CL/.cloud-kit-plugins"
fi

echo "cloud-kit: installed $ok files ($bad failed) into $CL"
