#!/usr/bin/env python3
"""Stop hook: work that changed code must be ship-checked before the turn ends.

Since the last real user prompt, if the assistant edited code (Edit/Write/NotebookEdit
outside ~/.claude, /tmp and the scratchpad) or ran `git commit` / `gh pr create`, and has
not invoked the ship-check skill AFTER the first such change, block the stop once and tell
it to run /ship-check. Allows the stop when the hook already fired this cycle
(stop_hook_active). Founder 2026-10-01: "every single time you do some sort of work I want
you to ship check it". Silent on any error.
"""
import json, os, re, sys

HOME = os.path.expanduser("~")
SKIP_PREFIXES = (f"{HOME}/.claude/", "/tmp/", "/private/tmp/", "/var/folders/")
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
GIT_CHANGE = re.compile(r"(^|[;&|(]\s*)(git\s+commit|gh\s+pr\s+create)\b", re.M)
QUOTED = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")


def runs_git_change(cmd):
    """True only if the shell itself runs git commit / gh pr create (not text in a heredoc or string)."""
    kept = []
    for line in QUOTED.sub("''", cmd).splitlines():
        kept.append(line)
        if "<<" in line:
            break
    return bool(GIT_CHANGE.search("\n".join(kept)))


def is_real_prompt(entry):
    if entry.get("type") != "user" or entry.get("isMeta"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return True
    if isinstance(content, list):
        return any(b.get("type") == "text" for b in content if isinstance(b, dict)) and not any(
            b.get("type") == "tool_result" for b in content if isinstance(b, dict))
    return False


def prompt_text(entry):
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content if isinstance(b, dict))


def main():
    payload = json.load(sys.stdin)
    if payload.get("stop_hook_active"):
        return
    path = payload.get("transcript_path") or ""
    if not os.path.exists(path):
        return
    entries = []
    with open(path, errors="ignore") as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except Exception:
                pass
    start = max((i for i, e in enumerate(entries) if is_real_prompt(e)), default=-1)
    if start < 0:
        return
    if "ship-check" in prompt_text(entries[start]):
        return
    changed = False
    for e in entries[start + 1:]:
        if e.get("type") != "assistant":
            continue
        for b in (e.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name, inp = b.get("name", ""), b.get("input") or {}
            if name == "Skill" and "ship-check" in str(inp.get("skill", "")):
                if changed:
                    return
            elif name in EDIT_TOOLS:
                fp = str(inp.get("file_path") or inp.get("notebook_path") or "")
                if fp and not fp.startswith(SKIP_PREFIXES):
                    changed = True
            elif name == "Bash" and runs_git_change(str(inp.get("command", ""))):
                changed = True
    if changed:
        print(json.dumps({
            "decision": "block",
            "reason": "[auto-ship-check] Code changed this turn and /ship-check has not run. "
                      "Run the ship-check skill now (it includes red-team), then end with the short "
                      "Done / Not done / Ship-checked / Proof summary.",
        }))


try:
    main()
except Exception:
    sys.exit(0)
