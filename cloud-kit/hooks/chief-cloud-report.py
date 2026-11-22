#!/usr/bin/env python3
"""SessionStart + Stop + SessionEnd hook: a cloud chat reports in to Chief (S6).

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
"""
import json, os, re, socket, subprocess, sys, time
import urllib.parse
import urllib.request

DEFAULT_URL = "https://xeyvuubsaxvszjgwjjaf.supabase.co/functions/v1/chief-ledger-ingest"
TIMEOUT = 3.0
HEARTBEAT_S = 300
EVENTS = {"SessionStart": "run_start", "Stop": "heartbeat", "SessionEnd": "run_end"}
SECRET = re.compile(r"(sk-[A-Za-z0-9_-]{10,}|gh[pousr]_[A-Za-z0-9]{20,}|eyJ[A-Za-z0-9_-]{20,}|Bearer\s+\S+)")


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


def throttled(session, now):
    d = os.path.join(os.path.expanduser("~"), ".claude", "state")
    stamp = os.path.join(d, "chief-cloud-" + re.sub(r"[^A-Za-z0-9_-]", "_", session)[:80])
    try:
        if now - os.path.getmtime(stamp) < HEARTBEAT_S:
            return True
    except OSError:
        pass
    try:
        os.makedirs(d, exist_ok=True)
        open(stamp, "w").close()
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
    if kind == "heartbeat" and throttled(session, time.time()):
        return
    cwd = str(hook.get("cwd") or os.getcwd())
    event = {"event": kind, "session_id": session[:200], "runs_on": "cloud", "host": clip(socket.gethostname(), 120)}
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
