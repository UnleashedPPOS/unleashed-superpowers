#!/usr/bin/env python3
"""PostToolUse hook: suggest a fresh chat only for genuinely long-lived sessions.

Auto-compact (200k) keeps each chat's context bounded, so a chat can and should keep
working through compactions until the job is done. This hook never asks a chat to stop.
It counts compactions; after COMPACT_AT of them (and every STEP more) it reminds the chat
that, once the current job is finished, the NEXT job should start in a fresh session.
Reads the transcript incrementally (offset cached in /tmp). Silent on any error.
"""
import json, os, sys

COMPACT_AT = 4
STEP = 2
MARK = b'"subtype":"compact_boundary"'

try:
    payload = json.load(sys.stdin)
    path = payload.get("transcript_path") or ""
    sid = payload.get("session_id") or "x"
    if not path or not os.path.exists(path):
        sys.exit(0)
    state_path = f"/tmp/claude-compact-nudge-{sid}"
    st = {"off": 0, "n": 0, "warned": 0}
    if os.path.exists(state_path):
        st.update(json.load(open(state_path)))
    size = os.path.getsize(path)
    if size < st["off"]:
        st = {"off": 0, "n": 0, "warned": 0}
    with open(path, "rb") as f:
        f.seek(st["off"])
        chunk = f.read()
    # only count complete lines; resume from the last newline next time
    end = chunk.rfind(b"\n") + 1
    st["n"] += chunk[:end].count(MARK)
    st["off"] += end
    fire = st["n"] >= COMPACT_AT and st["n"] >= st["warned"] + (STEP if st["warned"] else 0) and st["n"] != st["warned"]
    if fire:
        st["warned"] = st["n"]
    json.dump(st, open(state_path, "w"))
    if not fire:
        sys.exit(0)
    msg = (f"[token] {st['n']} compactions. Keep working; when the whole job is done, "
           "run session-handoff and end with a paste-in starter.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
except Exception:
    sys.exit(0)
