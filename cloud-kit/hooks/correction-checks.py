#!/usr/bin/env python3
"""Founder corrections enforced as checks (registry: corrections.json, engine: corrections_lib.py).

Founder 2026-11-16: corrections typed into Claude should become verifiers, checks, skills and
hooks, because many are never learned and he repeats himself. One script, four events:

  PreToolUse        Bash / Edit / Write / MultiEdit / NotebookEdit: "block" checks deny the call,
                    "ask" checks ask first (credentials, OpenRouter outside the OS app, banned
                    providers, "X for Y" brand copy, empty commits, test-account deletes ...).
  PostToolUse       "warn" checks on the same input add a nudge (commit message format), and text
                    written next to a tool call while working gets one nudge per turn (narration).
  Stop              "block" checks on the final reply (time estimates, unverified links, status in
                    chat when a page exists, permission questions, deferral talk, credentials ...).
                    Never blocks twice in a row (stop_hook_active), so it cannot loop.
  UserPromptSubmit  "context" checks on the founder's message (a pasted credential).

Sub-agents (payload has agent_id) get the PreToolUse guards only. Silent on any error.
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import corrections_lib as lib  # noqa: E402

MAX_READ = 8 << 20
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
NOT_A_PROMPT = ("<local-command", "[Request interrupted", "<task-notification", "<side-sessions-event",
                "<ci-monitor-event")
ARTIFACT_URL = re.compile(r"https://claude\.ai/(?:code/)?artifact/[\w-]+")


def tool_surface(name, inp):
    """(surface, text, path) for a tool call, or None."""
    if not isinstance(inp, dict):
        return None
    if name == "Bash":
        return "bash", inp.get("command") or "", ""
    if name in EDIT_TOOLS:
        if name == "MultiEdit":
            text = "\n".join(e.get("new_string") or "" for e in inp.get("edits") or [] if isinstance(e, dict))
        else:
            text = inp.get("content") or inp.get("new_string") or inp.get("new_source") or ""
        return "write", text, inp.get("file_path") or inp.get("notebook_path") or ""
    return None


def read_entries(path):
    if not path or not os.path.exists(path):
        return []
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        f.seek(max(0, size - MAX_READ))
        lines = f.read().split(b"\n")
    if size > MAX_READ:
        lines = lines[1:]
    out = []
    for raw in lines:
        if raw.strip():
            try:
                out.append(json.loads(raw))
            except Exception:
                continue
    return out


def text_of(content):
    if isinstance(content, str):
        return content
    parts = []
    for c in content or []:
        if isinstance(c, dict):
            t = c.get("text") if c.get("type") == "text" else c.get("content")
            parts.append(t if isinstance(t, str) else text_of(t) if isinstance(t, list) else "")
    return "\n".join(parts)


def is_prompt(e):
    if e.get("type") != "user" or e.get("isMeta") or e.get("isCompactSummary"):
        return False
    content = (e.get("message") or {}).get("content")
    if isinstance(content, list) and any(isinstance(c, dict) and c.get("type") == "tool_result" for c in content):
        return False
    return not text_of(content).lstrip().startswith(NOT_A_PROMPT)


def session_facts(entries):
    """URLs seen in tool calls/results, whether a status page exists, and the final reply text."""
    seen, page = set(), False
    for e in entries:
        msg = e.get("message") or {}
        content = msg.get("content")
        if e.get("type") == "user":
            body = text_of(content)
            if is_prompt(e):
                if ARTIFACT_URL.search(body) and re.search(r"status", body, re.I):
                    page = True  # a side session briefed with its parent's status page
                continue
            seen.update(lib.URL.findall(body))
        elif e.get("type") == "assistant" and isinstance(content, list):
            for c in content:
                if isinstance(c, dict) and c.get("type") == "tool_use":
                    inp = c.get("input") or {}
                    seen.update(lib.URL.findall(json.dumps(inp)))
                    if (c.get("name") == "Artifact" and inp.get("action", "publish") == "publish"
                            and not inp.get("asset") and "status" in os.path.basename(inp.get("file_path") or "").lower()):
                        page = True
    return seen, page


def final_reply(entries):
    """Text the assistant wrote after its last tool call in the current turn."""
    parts = []
    for e in reversed(entries):
        if is_prompt(e):
            break
        if e.get("type") == "user":
            break  # a tool result: everything after it is the reply
        content = (e.get("message") or {}).get("content")
        if e.get("type") == "assistant" and isinstance(content, list):
            if any(isinstance(c, dict) and c.get("type") == "tool_use" for c in content):
                break
            parts.append("\n".join(c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"))
    return "\n".join(reversed(parts)).strip()


def turn_text_with_tool(entries, tool_use_id):
    """(prompt marker, text of the assistant message that made this tool call)."""
    mid, marker = None, ""
    for e in entries:
        if is_prompt(e):
            marker = e.get("uuid") or e.get("timestamp") or marker
    for e in reversed(entries):
        content = (e.get("message") or {}).get("content")
        if e.get("type") == "assistant" and isinstance(content, list):
            ids = [c.get("id") for c in content if isinstance(c, dict) and c.get("type") == "tool_use"]
            if ids and (not tool_use_id or tool_use_id in ids):
                mid = (e.get("message") or {}).get("id") or e.get("uuid")
                break
        if is_prompt(e):
            break
    if not mid:
        return marker, ""
    texts = []
    for e in entries:
        msg = e.get("message") or {}
        if e.get("type") == "assistant" and (msg.get("id") or e.get("uuid")) == mid and isinstance(msg.get("content"), list):
            texts += [c.get("text", "") for c in msg["content"] if isinstance(c, dict) and c.get("type") == "text"]
    return marker, "\n".join(texts).strip()


def state_path(payload, name):
    d = os.path.expanduser("~/.claude/state")
    os.makedirs(d, exist_ok=True)
    sid = os.path.basename(str(payload.get("session_id") or "x")) or "x"
    return os.path.join(d, f"{name}-{sid}.json")


def pre_tool(payload):
    s = tool_surface(payload.get("tool_name"), payload.get("tool_input"))
    if not s:
        return None
    surface, text, path = s
    hits = lib.evaluate(surface, text, {"path": path, "cwd": payload.get("cwd") or ""}, actions=("block", "ask"))
    lib.log_hits(hits, surface)
    if not hits:
        return None
    decision = "deny" if any(e.get("action") == "block" for e, _ in hits) else "ask"
    reason = ("[correction-check] This call repeats a mistake the founder has corrected before:\n" + lib.describe(hits) +
              "\nFix the call. Only if this case is genuinely fine, add `correction-ok: <id>` to the command or text.")
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": decision,
                                   "permissionDecisionReason": reason}}


def post_tool(payload):
    notes = []
    s = tool_surface(payload.get("tool_name"), payload.get("tool_input"))
    if s:
        surface, text, path = s
        hits = lib.evaluate(surface, text, {"path": path, "cwd": payload.get("cwd") or ""}, actions=("warn",))
        lib.log_hits(hits, surface)
        if hits:
            notes.append(lib.describe(hits))
    if not payload.get("agent_id"):
        entries = read_entries(payload.get("transcript_path"))
        marker, text = turn_text_with_tool(entries, payload.get("tool_use_id"))
        if text and marker:
            sp = state_path(payload, "narration-nudge")
            try:
                with open(sp) as f:
                    last = json.load(f).get("turn")
            except Exception:
                last = None
            if last != marker:
                hits = lib.evaluate("turn", text, {})
                lib.log_hits(hits, "turn")
                if hits:
                    with open(sp, "w") as f:
                        json.dump({"turn": marker}, f)
                    notes.append(lib.describe(hits))
    if not notes:
        return None
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                   "additionalContext": "[correction-check]\n" + "\n".join(notes)}}


def stop(payload):
    if payload.get("stop_hook_active") or payload.get("agent_id"):
        return None
    entries = read_entries(payload.get("transcript_path"))
    text = final_reply(entries) or (payload.get("last_assistant_message") or "")
    if not text:
        return None
    seen, page = session_facts(entries)
    hits = lib.evaluate("reply", text, {"seen_urls": seen, "page_published": page}, actions=("block",))
    lib.log_hits(hits, "reply")
    if not hits:
        return None
    return {"decision": "block", "reason": (
        "[correction-check] The reply repeats something the founder has corrected before:\n" + lib.describe(hits) +
        "\nRewrite the reply without it (this check won't fire again on the rewrite). A link is fine once you've "
        "opened it this session (curl/WebFetch) or it's a known dashboard deep link.")}


def prompt(payload):
    hits = lib.evaluate("prompt", payload.get("prompt") or "", {})
    lib.log_hits(hits, "prompt")
    if not hits:
        return None
    return {"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                   "additionalContext": "[correction-check]\n" + lib.describe(hits)}}


HANDLERS = {"PreToolUse": pre_tool, "PostToolUse": post_tool, "Stop": stop, "UserPromptSubmit": prompt}


def main(payload):
    handler = HANDLERS.get(payload.get("hook_event_name") or "")
    return handler(payload) if handler else None


def installed_in_settings():
    """True when ~/.claude/settings.json already runs the cloud-kit copy (so the plugin copy stays quiet)."""
    try:
        with open(os.path.expanduser("~/.claude/settings.json")) as f:
            return "/.claude/hooks/correction-checks.py" in f.read()
    except Exception:
        return False


if __name__ == "__main__":
    try:
        if "--plugin" in sys.argv[1:] and installed_in_settings():
            sys.exit(0)  # cloud-kit install registered it in settings.json; don't run twice
        out = main(json.load(sys.stdin))
        if out:
            print(json.dumps(out))
    except Exception:
        sys.exit(0)
