#!/usr/bin/env python3
"""PostToolUse hook: nudge when a turn is a long run of single-tool calls.

Every tool call re-reads the whole context, so N serial one-call messages cost ~N full
context reads. Independent reads/greps/commands belong in ONE message (parallel calls) or
one ctx_batch_execute. Counts consecutive assistant messages since the last real user
prompt that carry exactly one tool_use (a parallel batch, edit or agent call ends the streak);
fires at LIMIT, then every LIMIT more.
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
    # one API response is split over several transcript entries sharing message.id, so group by id
    msgs = {}  # newest first (insertion order while walking backwards): message id -> {tool_use id: name}
    for raw in reversed(lines):
        if not raw.strip():
            continue
        try:
            e = json.loads(raw)
            if e.get("isSidechain") or e.get("isCompactSummary"):
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
            mid = msg.get("id") or e.get("requestId") or e.get("uuid")
            uses = msgs.setdefault(mid, {})
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    uses[c.get("id") or len(uses)] = c.get("name", "")
        except Exception:
            continue  # one malformed entry must not silence the hook
    sid_state = os.path.expanduser("~/.claude/state")
    sp = os.path.join(sid_state, f"serial-nudge-{sid}.json")
    try:
        fired = json.load(open(sp)).get("fired")
    except Exception:
        fired = None
    # trailing streak of single batchable calls; a parallel batch, an edit or an agent call ends it
    run = since = 0
    seen_fired = False
    for mid, uses in msgs.items():
        names = list(uses.values())
        if not names:
            continue  # text/thinking-only entry; not a call
        if len(names) != 1 or not (names[0] in BATCHABLE or names[0].startswith(BATCHABLE_PREFIX)):
            break
        run += 1
        if mid == fired:
            seen_fired = True
        if not seen_fired:
            since += 1
    fire = run >= LIMIT and since >= LIMIT
    if fire:
        os.makedirs(sid_state, exist_ok=True)
        newest = next(iter(msgs))
        fd, tmp = tempfile.mkstemp(dir=sid_state)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump({"fired": newest}, f)
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
