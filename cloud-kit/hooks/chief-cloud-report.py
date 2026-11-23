#!/usr/bin/env python3
"""SessionStart + prompt + Stop + Notification + SessionEnd hook: a cloud chat reports in to Chief (S6).

Posts run_start / heartbeat / run_end to the chief-ledger-ingest edge function (op "work") so the
chat shows in Chief as "In the cloud" with live status. The laptop has its own hook; this is the
cloud-kit one.

- Only acts when CHIEF_INGEST_CLOUD_TOKEN is set. Unset or empty: silent no-op, exit 0.
- The token is a write-only, revocable cloud token. The server pins runs_on to 'cloud'; this hook
  also sends runs_on='cloud' and can never claim laptop or server.
- The token is only ever sent as the Authorization header. It is never printed or logged.
- Short network timeout, every error swallowed, always exits 0, prints nothing: it can't block a session.
- Stop heartbeats are throttled to one per 5 minutes per session (stamp file in ~/.claude/state).
- Skips Chief's own runner sessions (CHIEF_RUNNER=1, CHIEF_JOB_ID) and CHIEF_LEDGER_SKIP=1.
CHIEF_INGEST_URL overrides the endpoint (tests): https only, or plain http to 127.0.0.1/localhost;
anything else falls back to the default so the token never goes to an arbitrary or cleartext host. Event shape: scripts/chief/work-lib.mjs in unleashed-os-mobile.

Chat register (Unity REGISTER): every event also carries chat_state (working | waiting | done) and, except on
SessionEnd, last_line (what the chat last said: 200 characters at most, one line, secrets scrubbed, never a user
message). UserPromptSubmit = working; Stop and Notification = waiting on the founder. Same state twice inside 5
minutes is skipped; a change of state always posts. Two-second timeout, silent on every failure.
"""
import json, os, re, socket, subprocess, sys, time
import urllib.parse
import urllib.request

DEFAULT_URL = "https://xeyvuubsaxvszjgwjjaf.supabase.co/functions/v1/chief-ledger-ingest"
TIMEOUT = 2.0
HEARTBEAT_S = 300
EVENTS = {
    "SessionStart": "run_start",
    "UserPromptSubmit": "heartbeat",
    "Stop": "heartbeat",
    "Notification": "heartbeat",
    "PostToolUse": "heartbeat",
    "SessionEnd": "run_end",
}
# Chat register state (Unity REGISTER): what the chat is doing right now. "idle" is never sent: Chief derives
# it when a chat has been silent for 24 hours.
CHAT_STATE = {"SessionStart": "working", "UserPromptSubmit": "working", "Stop": "waiting", "Notification": "waiting", "PostToolUse": "working", "SessionEnd": "done"}
LAST_LINE_MAX = 200
SECRET = re.compile(
    r"(sk-[A-Za-z0-9_-]{10,}|gsk_[A-Za-z0-9]{20,}|(?:sbp|sb_secret)_[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{6,}"
    r"|AKIA[0-9A-Z]{16}|(?:sk|rk)_live_[A-Za-z0-9]{8,}|xox[abprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----"
    r"|Bearer\s+\S+|[A-Za-z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)[A-Za-z0-9_]*\s*[=:]\s*\S+)",
    re.I,
)


def clip(v, n):
    if not isinstance(v, str) or not v.strip():
        return None
    return SECRET.sub("[redacted]", v.strip())[:n]


def git(cwd, *args):
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=2)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def repo_of(url):
    m = re.search(r"[/:]([^/:\s]+)/([^/\s]+?)(?:\.git)?/?$", url or "")
    return f"{m.group(1)}/{m.group(2)}" if m else None


def ingest_url(raw):
    try:
        u = urllib.parse.urlsplit(raw or "")
    except ValueError:
        return DEFAULT_URL
    if u.scheme == "https" and u.hostname:
        return raw
    if u.scheme == "http" and u.hostname in ("127.0.0.1", "localhost", "::1"):
        return raw
    return DEFAULT_URL


def last_line(path):
    """The last thing the chat said, one line, secrets scrubbed, 200 characters at most. No user messages."""
    if not isinstance(path, str) or not path:
        return None
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            size = f.tell()
            f.seek(max(0, size - 65536))
            tail = f.read().decode("utf-8", "ignore").splitlines()
    except Exception:
        return None
    for raw in reversed(tail):
        if '"assistant"' not in raw:
            continue
        try:
            o = json.loads(raw)
        except Exception:
            continue
        if o.get("type") != "assistant":
            continue
        content = (o.get("message") or {}).get("content")
        parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"] if isinstance(content, list) else []
        text = " ".join(" ".join(parts).split())
        if text:
            return clip(text, LAST_LINE_MAX)
    return None


def _stamp(session):
    d = os.path.join(os.path.expanduser("~"), ".claude", "state")
    return d, os.path.join(d, "chief-cloud-" + re.sub(r"[^A-Za-z0-9_-]", "_", session)[:80])


def recorded_state(session):
    try:
        return open(_stamp(session)[1]).read().strip()
    except OSError:
        return ""


def throttled(session, state, now):
    """Same state again within 5 minutes is skipped; a change of state always posts."""
    d, stamp = _stamp(session)
    try:
        if now - os.path.getmtime(stamp) < HEARTBEAT_S and open(stamp).read().strip() == state:
            return True
    except OSError:
        pass
    try:
        os.makedirs(d, exist_ok=True)
        with open(stamp, "w") as f:
            f.write(state)
    except OSError:
        pass
    return False


def main():
    token = os.environ.get("CHIEF_INGEST_CLOUD_TOKEN", "").strip()
    if not token:
        return
    env = os.environ
    if env.get("CHIEF_LEDGER_SKIP") == "1" or env.get("CHIEF_RUNNER") == "1" or env.get("CHIEF_JOB_ID"):
        return
    try:
        hook = json.load(sys.stdin)
    except Exception:
        return
    if not isinstance(hook, dict) or not hook.get("session_id"):
        return
    kind = EVENTS.get(str(hook.get("hook_event_name", "")))
    if not kind:
        return
    session = str(hook["session_id"])
    name = str(hook.get("hook_event_name", ""))
    state = CHAT_STATE.get(name, "working")
    # A tool ran: only worth a post when the chat was last reported as waiting (a permission prompt was
    # answered), so "waiting" never sticks on a busy chat. Every other tool call exits here, before any work.
    if name == "PostToolUse" and recorded_state(session) != "waiting":
        return
    if kind == "heartbeat" and throttled(session, state, time.time()):
        return
    # The git calls and the POST run in a detached child so the hook itself returns at once and never makes
    # Claude wait. CHIEF_HOOK_FOREGROUND=1 keeps it inline (tests).
    if env.get("CHIEF_HOOK_FOREGROUND") != "1" and hasattr(os, "fork"):
        try:
            if os.fork() != 0:
                return
            os.setsid()
            devnull = os.open(os.devnull, os.O_RDWR)
            for fd in (0, 1, 2):
                os.dup2(devnull, fd)
        except OSError:
            pass
    cwd = str(hook.get("cwd") or os.getcwd())
    event = {"event": kind, "session_id": session[:120], "runs_on": "cloud", "host": clip(socket.gethostname(), 120), "chat_state": state}
    if state != "done":
        event["last_line"] = last_line(hook.get("transcript_path"))
    branch = git(cwd, "rev-parse", "--abbrev-ref", "HEAD")
    if branch and branch != "HEAD":
        event["branch"] = clip(branch, 255)
    repo = repo_of(git(cwd, "remote", "get-url", "origin"))
    if repo:
        event["repo"] = clip(repo, 140)
    if isinstance(hook.get("model"), str):
        event["model"] = clip(hook["model"], 120)
    body = json.dumps({"op": "work", "event": {k: v for k, v in event.items() if v}}).encode()
    req = urllib.request.Request(
        ingest_url(env.get("CHIEF_INGEST_URL")),
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
    )
    urllib.request.urlopen(req, timeout=TIMEOUT).read(1024)


if __name__ == "__main__":
    try:
        main()
    except BaseException:
        pass
    sys.exit(0)
