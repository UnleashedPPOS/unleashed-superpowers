#!/usr/bin/env python3
"""Stop hook: work that changed code must be ship-checked before the turn ends.

Since the last real (human) user prompt, if the assistant edited code (Edit/Write/NotebookEdit
outside ~/.claude, /tmp and the scratchpad), ran `git commit` / `gh pr create`, or a commit
landed in the session's repo (covers sub-agents, whose edits live in their own transcripts),
and has not invoked ship-check AFTER the first such change, block the stop once and tell it
to run /ship-check. Allows the stop when the hook already fired this cycle (stop_hook_active)
or when the prompt itself was /ship-check. Founder 2026-10-01: "every single time you do some
sort of work I want you to ship check it". Silent on any error.

Known gap: sub-agent edits that are neither committed in the session cwd's repo nor made by
this transcript (e.g. uncommitted work in another worktree) are not seen.
"""
import json, os, re, subprocess, sys
from datetime import datetime

HOME = os.path.expanduser("~")
SKIP_PREFIXES = (f"{HOME}/.claude/", "/tmp/", "/private/tmp/", "/var/folders/")
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
GIT_CHANGE = re.compile(r"\bgit\s+(?:-[Cc]\s+\S+\s+)*commit\b|\bgh\s+pr\s+create\b")
QUOTED = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1")
NOT_A_PROMPT = ("<task-notification", "<local-command", "[Request interrupted", "<system-reminder")
SHIP_CHECK_PROMPT = re.compile(r"^\s*/ship-check\b|<command-name>/?ship-check</command-name>")


def strip_heredocs(cmd):
    """Drop heredoc bodies (text fed to a command, never run by the shell itself)."""
    out, delim = [], None
    for line in cmd.splitlines():
        if delim is not None:
            if line.strip() == delim:
                delim = None
            continue
        out.append(line)
        m = HEREDOC.search(line)
        if m:
            delim = m.group(2)
    return "\n".join(out)


def runs_git_change(cmd):
    """True only if the shell itself runs git commit / gh pr create (not text in a heredoc or string)."""
    return bool(GIT_CHANGE.search(QUOTED.sub("''", strip_heredocs(cmd))))


def is_real_prompt(entry):
    if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isCompactSummary"):
        return False
    origin = entry.get("origin")
    if isinstance(origin, dict) and origin.get("kind") not in (None, "human"):
        return False
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return not content.lstrip().startswith(NOT_A_PROMPT)
    if isinstance(content, list):
        blocks = [b for b in content if isinstance(b, dict)]
        if any(b.get("type") == "tool_result" for b in blocks):
            return False
        texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
        return any(t.strip() and not t.lstrip().startswith(NOT_A_PROMPT) for t in texts)
    return False


def prompt_text(entry):
    content = (entry.get("message") or {}).get("content")
    if isinstance(content, str):
        return content
    return " ".join(b.get("text", "") for b in content if isinstance(b, dict))


def committed_since(cwd, ts):
    """True if the repo at cwd has a commit newer than the prompt timestamp (ISO 8601)."""
    if not cwd or not ts:
        return False
    try:
        since = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        out = subprocess.run(["git", "-C", cwd, "log", "-1", "--format=%ct"],
                             capture_output=True, text=True, timeout=3).stdout.strip()
        return bool(out) and int(out) > since
    except Exception:
        return False


def main():
    payload = json.load(sys.stdin)
    if payload.get("stop_hook_active"):
        return
    path = payload.get("transcript_path") or ""
    if not os.path.exists(path):
        return
    with open(path, errors="ignore") as f:
        lines = f.readlines()
    # Walk back to the last real prompt; only the tail gets parsed.
    tail, start = [], None
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except Exception:
            continue
        if is_real_prompt(e):
            start = e
            break
        tail.append(e)
    if start is None:
        return
    if SHIP_CHECK_PROMPT.search(prompt_text(start)):
        return
    tail.reverse()
    failed = {b.get("tool_use_id") for e in tail if e.get("type") == "user"
              for b in ((e.get("message") or {}).get("content") or [])
              if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("is_error")}
    changed = shipped = False
    for e in tail:
        if e.get("type") != "assistant":
            continue
        for b in (e.get("message") or {}).get("content") or []:
            if not isinstance(b, dict) or b.get("type") != "tool_use":
                continue
            name, inp = b.get("name", ""), b.get("input") or {}
            if name in ("Skill", "SlashCommand") and "ship-check" in json.dumps(inp):
                if changed:
                    return
                shipped = True
            elif b.get("id") in failed:
                continue
            elif name in EDIT_TOOLS:
                fp = str(inp.get("file_path") or inp.get("notebook_path") or "")
                if fp and not fp.startswith(SKIP_PREFIXES):
                    changed = True
            elif name == "Bash" and runs_git_change(str(inp.get("command", ""))):
                changed = True
    if not changed and not shipped:
        changed = committed_since(payload.get("cwd"), start.get("timestamp"))
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
