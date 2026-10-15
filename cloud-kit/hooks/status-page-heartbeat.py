#!/usr/bin/env python3
"""PostToolUse + Stop hook: keep the founder's HTML status page live during long work.

Founder 2026-10-15: "long work… the status updates every so often… work spawned off from a chat
gets the global update… when work is done it gets the update".

PostToolUse: once a turn has run INTERVAL minutes without the status page being republished,
remind the chat to republish it with progress (and again every INTERVAL minutes after that).
Stop: if real work happened after the page was last published this turn (edits outside temp
dirs, commits, PRs, merges, spawned agents/sessions), block the stop ONCE and ask for the final
page update. Ship-check ordering is left to auto-ship-check.py, which fires on the same Stop.

Which page: a status page this session published (an Artifact publish whose file name contains
"status"; other artifacts such as reports don't count), else a claude.ai artifact link given in a
prompt that mentions "status" (a side session started from a chat updates its parent's page).
Task notifications and side-session events don't start a new turn. Stop re-blocks only when new work
happened after its last block, so it never loops. Sub-agent hook calls (payload has agent_id) are
ignored: sub-agents never publish.
Reads the transcript incrementally (offset cached in ~/.claude/state). Silent on any error.
"""
import json, os, re, sys, tempfile, time
from datetime import datetime

INTERVAL = float(os.environ.get("STATUS_HEARTBEAT_MIN", "30")) * 60
HOME = os.path.expanduser("~")
SKIP_PREFIXES = (f"{HOME}/.claude/", "/tmp/", "/private/tmp/", "/var/folders/")
EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
SPAWN_TOOLS = {"Agent", "Task", "mcp__ccd_session__start_session", "mcp__ccd_session__hand_off_to_session"}
GIT_WORK = re.compile(r"\bgit\s+(?:-C\s+\S+\s+)?commit\b|\bgh\s+pr\s+(?:create|merge)\b")
PUBLISHED = re.compile(r"Published \S.* at (https://claude\.ai/(?:code/)?artifact/[\w-]+)")
STATUS = re.compile(r"status", re.I)
ARTIFACT_URL = re.compile(r"https://claude\.ai/(?:code/)?artifact/[\w-]+")
NOT_A_PROMPT = ("<local-command", "[Request interrupted", "<task-notification", "<side-sessions-event",
                "<ci-monitor-event")
FRESH = {"off": 0, "turn": 0, "pub": 0, "nudge": 0, "url": "", "brief": "", "work": False, "wts": 0, "fired": 0, "pending": ""}


def ts(e):
    try:
        return datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0


def text_of(content):
    if isinstance(content, str):
        return content
    out = []
    for c in content or []:
        if isinstance(c, dict):
            t = c.get("text") or c.get("content")
            out.append(t if isinstance(t, str) else text_of(t) if isinstance(t, list) else "")
    return "\n".join(out)


def scan(st, e):
    kind = e.get("type")
    msg = e.get("message") or {}
    content = msg.get("content")
    if kind == "user":
        results = isinstance(content, list) and any(
            isinstance(c, dict) and c.get("type") == "tool_result" for c in content)
        body = text_of(content)
        if results:
            ids = {c.get("tool_use_id") for c in content if isinstance(c, dict)}
            m = PUBLISHED.search(body)
            if m and st["pending"] in ids:
                st["url"], st["pending"] = m.group(1), ""
            return
        if e.get("isMeta") or e.get("isCompactSummary") or body.lstrip().startswith(NOT_A_PROMPT):
            return
        st["turn"], st["work"] = ts(e) or st["turn"], False
        urls = ARTIFACT_URL.findall(body)
        if urls and STATUS.search(body):
            st["brief"] = urls[-1]
    elif kind == "assistant" and isinstance(content, list):
        for c in content:
            if not isinstance(c, dict) or c.get("type") != "tool_use":
                continue
            name, inp = c.get("name"), c.get("input") or {}
            if name == "Artifact" and inp.get("action", "publish") == "publish" and not inp.get("asset"):
                if not STATUS.search(os.path.basename(inp.get("file_path") or "")):
                    continue  # a report or other artifact, not the status page
                st["pub"], st["work"] = ts(e) or time.time(), False
                if inp.get("url"):
                    st["url"] = inp["url"]
                else:
                    st["pending"] = c.get("id") or ""
            elif name in EDIT_TOOLS:
                p = os.path.realpath(inp.get("file_path") or inp.get("notebook_path") or "/tmp/x")
                if not p.startswith(SKIP_PREFIXES):
                    st["work"], st["wts"] = True, ts(e) or time.time()
            elif name in SPAWN_TOOLS or (name == "Bash" and GIT_WORK.search(inp.get("command") or "")):
                st["work"], st["wts"] = True, ts(e) or time.time()


def load(payload):
    path = payload.get("transcript_path") or ""
    sid = os.path.basename(payload.get("session_id") or "x")
    state_dir = os.path.expanduser("~/.claude/state")
    os.makedirs(state_dir, exist_ok=True)
    state_path = os.path.join(state_dir, f"status-heartbeat-{sid}.json")
    st = dict(FRESH)
    try:
        st.update(json.load(open(state_path)))
    except Exception:
        pass  # missing or torn state: rescan from the start
    if os.path.getsize(path) < st["off"]:
        st = dict(FRESH)
    with open(path, "rb") as f:
        f.seek(st["off"])
        chunk = f.read()
    end = chunk.rfind(b"\n") + 1
    for line in chunk[:end].splitlines():
        try:
            scan(st, json.loads(line))
        except Exception:
            continue
    st["off"] += end
    return st, state_dir, state_path


def save(st, state_dir, state_path):
    fd, tmp = tempfile.mkstemp(dir=state_dir)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(st, f)
        os.replace(tmp, state_path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def where(st):
    if st["url"]:
        return f"Republish the same page: {st['url']}."
    if st["brief"]:
        return (f"This chat reports to the page {st['brief']} (from its brief or prompt): read it, update "
                "only this work's lines, and republish to that url; on a conflict, merge onto the live version.")
    return ("No status page yet: publish one now (Artifact, a file named *status*.html) and reuse its link "
            "from then on.")


def main(payload, now=None):
    """Returns the hook's JSON output (a dict) or None."""
    if payload.get("agent_id"):
        return None
    if not os.path.exists(payload.get("transcript_path") or ""):
        return None
    now = now or time.time()
    st, state_dir, state_path = load(payload)
    out = None
    event = payload.get("hook_event_name") or "PostToolUse"
    if event == "Stop":
        has_page = st["url"] or st["brief"]
        long_turn = st["turn"] and now - st["turn"] >= INTERVAL
        if st["work"] and st["fired"] < st["wts"] and (has_page or long_turn):
            st["fired"] = st["wts"]
            out = {"decision": "block", "reason": (
                "[status-page] Work happened after the status page was last updated. Before ending: ship-check "
                "first if code changed, then update the page (finished items into Done, drop finished Needs you "
                f"steps, what is still running under Still open). {where(st)} No Artifact tool (cloud): put it in the "
                "PR description instead. Then a 1-2 line reply. Skip the republish only if nothing the founder "
                "would notice changed.")}
    elif st["turn"] and st["work"]:
        last = max(st["turn"], st["pub"], st["nudge"])
        if now - last >= INTERVAL:
            mins = int((now - max(st["turn"], st["pub"])) // 60)
            st["nudge"] = now
            out = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": (
                f"[status-page] {mins} min of work since the status page was last updated. Republish it now "
                "with progress: done items into Done, what is in flight (including side sessions and sub-agents "
                f"you started) under Still open. {where(st)} No chat text. No Artifact tool (cloud): update the "
                "PR description instead. Sub-agents: ignore this, return status to the parent.")}}
    save(st, state_dir, state_path)
    return out


if __name__ == "__main__":
    try:
        result = main(json.load(sys.stdin))
        if result:
            print(json.dumps(result))
    except Exception:
        sys.exit(0)
