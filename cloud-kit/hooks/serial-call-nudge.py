#!/usr/bin/env python3
"""PostToolUse hook: nudge when a turn is a long run of single-tool calls.

Every tool call re-reads the whole context, so N serial one-call messages cost ~N full
context reads. Independent reads/greps/commands belong in ONE message (parallel calls) or
one ctx_batch_execute. Counts consecutive assistant messages since the last real user
prompt that carry exactly one tool_use; fires at LIMIT, then every LIMIT more.
Reads only the transcript tail. Silent on any error.
"""
import json, os, sys, tempfile

LIMIT = 8
TAIL = 400_000
# calls worth batching; Agent/Edit/Write/Workflow and wrap-ups are excluded on purpose
BATCHABLE = ("Bash", "Read", "Grep", "Glob", "WebFetch", "WebSearch")
BATCHABLE_PREFIX = ("mcp__tilth__", "mcp__plugin_context-mode", "mcp__Claude_Browser__")

try:
    payload = json.load(sys.stdin)
    path = payload.get("transcript_path") or ""
    sid = os.path.basename(payload.get("session_id") or "x")
    if not path or not os.path.exists(path):
        sys.exit(0)
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - TAIL))
        lines = f.read().split(b"\n")
    if size > TAIL:
        lines = lines[1:]  # first line is probably cut mid-record
    run = 0
    for raw in reversed(lines):
        if not raw.strip():
            continue
        try:
            e = json.loads(raw)
        except Exception:
            continue
        msg = e.get("message") or {}
        content = msg.get("content")
        if e.get("type") == "user":
            if isinstance(content, list) and any(c.get("type") == "tool_result" for c in content if isinstance(c, dict)):
                continue  # tool results are part of the turn
            if e.get("isMeta"):
                continue
            break  # a real user prompt ends the turn
        if e.get("type") != "assistant" or not isinstance(content, list):
            continue
        uses = [c for c in content if isinstance(c, dict) and c.get("type") == "tool_use"]
        if not uses:
            continue
        if len(uses) == 1:
            n = uses[0].get("name", "")
            if n in BATCHABLE or n.startswith(BATCHABLE_PREFIX):
                run += 1
            continue
        # a parallel batch is the behaviour we want; it does not extend the run
    state_dir = os.path.expanduser("~/.claude/state")
    os.makedirs(state_dir, exist_ok=True)
    sp = os.path.join(state_dir, f"serial-nudge-{sid}.json")
    warned = 0
    try:
        warned = int(json.load(open(sp)).get("warned", 0))
    except Exception:
        pass
    if run < warned:
        warned = 0  # new turn
    fire = run >= LIMIT and run >= warned + LIMIT if warned else run >= LIMIT
    if fire:
        warned = run
    fd, tmp = tempfile.mkstemp(dir=state_dir)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump({"warned": warned}, f)
        os.replace(tmp, sp)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
    if not fire:
        sys.exit(0)
    msg = (f"[token] {run} single-tool calls in a row this turn; each re-reads the full context. "
           "Batch independent reads/greps/commands into ONE message (parallel tool calls) or one "
           "ctx_batch_execute, read file regions in generous chunks, then act.")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
except Exception:
    sys.exit(0)
