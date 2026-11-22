#!/usr/bin/env python3
"""Brake-ledger hook (UserPromptSubmit, PostToolUse:Bash, Stop): a heavy job the memory brake killed
must be re-run, not forgotten.

memory-guard appends a `kill` line to ~/.local/share/memory-guard/brake-ledger.jsonl. The chat whose
cwd is in (or is) that worktree is told, once per entry on tool calls and on every new prompt:
re-run it through heavy-run. A green heavy-run in that worktree closes the entry. Stop is blocked
(up to twice per entry) when the final reply claims tests/typecheck/lint/build pass while an entry
is open. Entries older than 48 h expire with a log line. Silent on any error.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import heavy_lib as hl  # noqa: E402

PASS_CLAIM = re.compile(
    r"\b(?:tests?|specs?|suite|typecheck|type-check|tsc|lint(?:ing)?|eslint|build|jest|ci|checks?)\b[^.\n]{0,40}?"
    r"\b(?:pass(?:es|ed|ing)?|green|clean|succe(?:ed|eds|ssful)|ok)\b"
    r"|\ball (?:green|passing|tests pass)\b|\bgreen\b|\b\d+\s*/\s*\d+ (?:tests )?pass", re.I)


def msg_for(entries):
    lines = []
    for e in entries:
        lines.append(f"the memory brake stopped your `{e.get('command', '')[:100]}` in {e.get('worktree')} at "
                     f"{e.get('iso', '')} ({e.get('job_rss_mb', '?')} MB)")
    return ("[memory brake] " + "; ".join(lines) + ". Re-run it through heavy-run "
            f"(`{hl.heavy_run_bin()} <same command>`) before claiming tests pass; a green run closes this entry.")


def state_file(session):
    return hl.state_dir() / "nudged" / f"{os.path.basename(session or 'x')}.json"


def load_state(session):
    try:
        return json.loads(state_file(session).read_text())
    except (OSError, ValueError):
        return {}


def save_state(session, st):
    try:
        p = state_file(session)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(st))
    except OSError:
        pass


def last_assistant_text(path):
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as f:
            f.seek(max(0, size - 200_000))
            lines = f.read().decode(errors="ignore").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") == "assistant":
            c = (e.get("message") or {}).get("content")
            text = c if isinstance(c, str) else " ".join(b.get("text", "") for b in c or [] if isinstance(b, dict))
            if text.strip():
                return text
    return ""


def main():
    p = json.load(sys.stdin)
    event, session, cwd = p.get("hook_event_name", ""), p.get("session_id", ""), p.get("cwd", "")
    mine = [e for e in hl.open_entries() if hl.owns(e, cwd)]
    if not mine:
        return
    st = load_state(session)
    if event == "Stop":
        if not PASS_CLAIM.search(last_assistant_text(p.get("transcript_path") or "")):
            return
        blocks = st.setdefault("blocks", {})
        fresh = [e for e in mine if blocks.get(e["id"], 0) < 2]
        if not fresh:
            return
        for e in fresh:
            blocks[e["id"]] = blocks.get(e["id"], 0) + 1
        save_state(session, st)
        print(json.dumps({"decision": "block", "reason": msg_for(fresh) + " Your reply claims a pass; "
                          "re-run and report the real result instead."}))
        return
    nudged = st.setdefault("nudged", [])
    todo = mine if event == "UserPromptSubmit" else [e for e in mine if e["id"] not in nudged]
    if not todo:
        return
    st["nudged"] = sorted(set(nudged) | {e["id"] for e in todo})
    save_state(session, st)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": msg_for(todo)}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
