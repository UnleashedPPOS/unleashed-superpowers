"""Shared logic for the heavy-job gate (bin/heavy-run), the PreToolUse rewrite hook
(heavy-gate.py), the brake ledger hook (heavy-ledger-hook.py) and ~/bin/memory-guard.py.

Why: the 8 GB Mac freezes when several Claude chats run jest/tsc/eslint at once.
memory-guard's brake kills live heavy jobs at critical pressure; this module gives
every chat a wait-your-turn gate (K slots) and makes sure a killed job is re-run.

State lives in ~/.local/share/memory-guard (override: MEMORY_GUARD_STATE_DIR):
  gate/slot-N.lock     flock'd by heavy-run for the life of the job (stale-lock safe:
                       the kernel drops the lock when the holder dies)
  gate/queue/*.t       FIFO tickets for waiting jobs
  brake-ledger.jsonl   append-only: kill / done / expired events

Config (env wins over ~/.local/share/memory-guard/heavy-run.conf, KEY=VALUE lines):
  HEAVY_RUN_SLOTS (2)  HEAVY_RUN_SWAP_MB (4500)  HEAVY_RUN_MAX_WORKERS (2)
  HEAVY_RUN_WAIT_BUDGET (100 s, 0 = wait forever)  HEAVY_RUN_POLL_S (2)
  HEAVY_RUN_RETRIES (2)  HEAVY_RUN_RETRY_COOLDOWN_S (150)  HEAVY_RUN_TICKET_TTL_S (120)
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import shlex
import subprocess
import time
import uuid
from pathlib import Path

DEFAULTS = {
    "HEAVY_RUN_SLOTS": "2",
    "HEAVY_RUN_SWAP_MB": "4500",
    "HEAVY_RUN_MAX_WORKERS": "2",
    "HEAVY_RUN_WAIT_BUDGET": "100",
    "HEAVY_RUN_POLL_S": "2",
    "HEAVY_RUN_RETRIES": "2",
    "HEAVY_RUN_RETRY_COOLDOWN_S": "150",
    "HEAVY_RUN_TICKET_TTL_S": "120",
}
LEDGER_EXPIRY_S = 48 * 3600


def state_dir() -> Path:
    return Path(os.environ.get("MEMORY_GUARD_STATE_DIR") or (Path.home() / ".local/share/memory-guard"))


def log_path() -> Path:
    return Path(os.environ.get("MEMORY_GUARD_LOG") or (Path.home() / "Library/Logs/memory-guard.log"))


def log(msg: str) -> None:
    try:
        p = log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as fh:
            fh.write(f"{time.strftime('%F %T')} {msg}\n")
    except OSError:
        pass


def heavy_run_bin() -> str:
    return os.environ.get("HEAVY_RUN_BIN") or str(Path.home() / "bin/heavy-run")


def cfg(name: str) -> float:
    if name in os.environ:
        raw = os.environ[name]
    else:
        raw = None
        try:
            for line in (state_dir() / "heavy-run.conf").read_text().splitlines():
                key, _, val = line.partition("=")
                if key.strip() == name:
                    raw = val.strip()
        except OSError:
            pass
    try:
        return float(raw if raw is not None else DEFAULTS[name])
    except ValueError:
        return float(DEFAULTS[name])


# ---------------------------------------------------------------- pressure

def _sysctl(name: str) -> str:
    try:
        return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def pressure_and_swap() -> tuple[int, float]:
    """(pressure level 1/2/4, swap used MB). HEAVY_RUN_PRESSURE_FILE ("level swap_mb") is a test knob."""
    fake = os.environ.get("HEAVY_RUN_PRESSURE_FILE")
    if fake:
        try:
            level, swap = Path(fake).read_text().split()[:2]
            return int(level), float(swap)
        except (OSError, ValueError):
            return 1, 0.0
    try:
        level = int(_sysctl("kern.memorystatus_vm_pressure_level").strip() or 1)
    except ValueError:
        level = 1
    m = re.search(r"used = ([0-9.]+)M", _sysctl("vm.swapusage"))
    return level, float(m.group(1)) if m else 0.0


# ---------------------------------------------------------------- slots

def gate_dir() -> Path:
    return state_dir() / "gate"


def read_record(fd: int) -> dict:
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        return json.loads(os.read(fd, 65536).decode() or "{}")
    except (OSError, ValueError):
        return {}


def running_jobs(k: int) -> list:
    """Records of jobs holding a slot right now (a slot counts as held only while its flock is held)."""
    out = []
    for i in range(k):
        path = gate_dir() / f"slot-{i}.lock"
        try:
            fd = os.open(path, os.O_RDWR)
        except OSError:
            continue
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                out.append(read_record(fd) or {"slot": i})
        finally:
            os.close(fd)
    return out


def try_acquire(k: int):
    """Take the first free slot. Returns (slot index, fd) or None."""
    gate_dir().mkdir(parents=True, exist_ok=True)
    for i in range(k):
        fd = os.open(gate_dir() / f"slot-{i}.lock", os.O_RDWR | os.O_CREAT, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return i, fd
        except OSError:
            os.close(fd)
    return None


def write_record(fd: int, record: dict) -> None:
    try:
        os.ftruncate(fd, 0)
        os.lseek(fd, 0, os.SEEK_SET)
        os.write(fd, json.dumps(record).encode())
    except OSError:
        pass


def gate_records() -> list:
    """Records of running heavy-run jobs (used by the brake to map a process back to its job)."""
    return running_jobs(int(max(cfg("HEAVY_RUN_SLOTS"), 8)))


# ---------------------------------------------------------------- queue

def queue_dir() -> Path:
    return gate_dir() / "queue"


def job_key(cwd: str, cmd: str) -> str:
    return hashlib.sha1(f"{cwd}\0{cmd}".encode()).hexdigest()[:10]


def _live_tickets() -> list:
    ttl = cfg("HEAVY_RUN_TICKET_TTL_S")
    now = time.time()
    live = []
    try:
        names = sorted(os.listdir(queue_dir()))
    except OSError:
        return live
    for name in names:
        p = queue_dir() / name
        try:
            if now - p.stat().st_mtime > ttl:
                p.unlink()  # waiter died (no refresh within the TTL): stale ticket
            else:
                live.append(name)
        except OSError:
            pass
    return live


def join_queue(key: str) -> str:
    """Join (or re-join, keeping the original place) the FIFO queue. Returns the ticket name."""
    queue_dir().mkdir(parents=True, exist_ok=True)
    for name in _live_tickets():
        if name.endswith(f"-{key}.t"):
            return name
    name = f"{time.time_ns():020d}-{key}.t"
    (queue_dir() / name).touch()
    return name


def refresh(ticket: str) -> None:
    try:
        os.utime(queue_dir() / ticket)
    except OSError:
        (queue_dir()).mkdir(parents=True, exist_ok=True)
        (queue_dir() / ticket).touch()


def position(ticket: str) -> int:
    live = _live_tickets()
    return live.index(ticket) + 1 if ticket in live else len(live) + 1


def leave_queue(ticket: str) -> None:
    try:
        (queue_dir() / ticket).unlink()
    except OSError:
        pass


def gate_open(k: int) -> tuple[bool, str]:
    """May a job start now? Always yes when nothing else is running (so a high baseline swap can't starve
    the queue); otherwise only while pressure is below critical and swap is under the line."""
    running = running_jobs(k)
    if not running:
        return True, ""
    level, swap = pressure_and_swap()
    if level >= 4:
        return False, f"memory pressure critical, {len(running)} heavy job(s) running"
    if swap > cfg("HEAVY_RUN_SWAP_MB"):
        return False, f"swap {swap:.0f} MB over the {cfg('HEAVY_RUN_SWAP_MB'):.0f} MB line, {len(running)} heavy job(s) running"
    return True, ""


def acquire(cmd_label: str, cwd: str, budget: float, say=None):
    """Wait for a slot. Returns (slot, fd) or None when the wait budget ran out (place in line is kept
    for HEAVY_RUN_TICKET_TTL_S so a re-run of the same command keeps its turn)."""
    k = int(cfg("HEAVY_RUN_SLOTS"))
    poll = max(cfg("HEAVY_RUN_POLL_S"), 0.05)
    ticket = join_queue(job_key(cwd, cmd_label))
    start = last_say = time.time()
    announced = False
    while True:
        refresh(ticket)
        why = ""
        if position(ticket) == 1:
            ok, why = gate_open(k)
            if ok:
                got = try_acquire(k)
                if got:
                    leave_queue(ticket)
                    return got
                why = f"all {k} heavy slots busy"
        else:
            why = f"{position(ticket) - 1} job(s) ahead of you"
        now = time.time()
        if budget > 0 and now - start >= budget:
            return None
        if say and (not announced or now - last_say >= 30):
            say(f"heavy-run: waiting your turn ({why}); you are #{position(ticket)} in line")
            announced, last_say = True, now
        time.sleep(poll)


# ---------------------------------------------------------------- classification

KINDS = [
    ("jest", re.compile(r"(?<![\w-])jest(?![\w-])")),
    ("tsc", re.compile(r"(?<![\w-])tsc(?![\w-])|typescript/bin/tsc")),
    ("eslint", re.compile(r"(?<![\w-])eslint(?![\w-])|rtk lint")),
    ("vitest", re.compile(r"(?<![\w-])vitest")),
    ("expo-export", re.compile(r"expo(/bin/cli)? export|react-native bundle")),
    ("next-build", re.compile(r"next build")),
    ("playwright", re.compile(r"playwright test")),
    ("deno", re.compile(r"deno (test|check)")),
    ("webpack", re.compile(r"webpack|metro")),
]
SCRIPT = re.compile(r"^(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?([\w:.-]+)")


def kind_of(cmd: str) -> str:
    m = SCRIPT.match(cmd.strip())
    if m:
        return "script:" + m.group(1)
    for name, rx in KINDS:
        if rx.search(cmd):
            return name
    return "other"


WORKER_FLAGS = re.compile(r"(^|\s)(--maxWorkers\S*|-w\s*\S+|--runInBand|-i|--watch\S*|--watchAll)(\s|$)")
JEST_WORD = re.compile(r"(?:^|[\s/])jest$")


def cap_workers(argv: list) -> list:
    """Append --maxWorkers=N to a direct jest invocation that has no worker flag (never to npm scripts)."""
    if not argv or not any(JEST_WORD.search(a) for a in argv[:4]):
        return argv
    if argv[0] in ("npm", "pnpm", "yarn", "bun") and (len(argv) < 2 or argv[1] in ("test", "run", "t")):
        return argv
    if WORKER_FLAGS.search(" " + " ".join(argv[1:]) + " "):
        return argv
    return argv + [f"--maxWorkers={int(cfg('HEAVY_RUN_MAX_WORKERS'))}"]


# ---------------------------------------------------------------- ledger

def ledger_path() -> Path:
    return state_dir() / "brake-ledger.jsonl"


def append_event(event: dict) -> None:
    line = (json.dumps(event, separators=(",", ":")) + "\n").encode()
    try:
        state_dir().mkdir(parents=True, exist_ok=True)
        fd = os.open(ledger_path(), os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
        try:
            os.write(fd, line)  # one write: O_APPEND lines stay whole across processes
        finally:
            os.close(fd)
    except OSError:
        pass


def worktree_of(cwd: str) -> str:
    try:
        top = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=3).stdout.strip()
        if top:
            return os.path.realpath(top)
    except (OSError, subprocess.TimeoutExpired):
        pass
    return os.path.realpath(cwd) if cwd else ""


def record_kill(cwd: str, command: str, pid: int, rss_mb: float, job_rss_mb: float,
                heavy_run_pid=None, kind=None) -> dict:
    entry = {"event": "kill", "id": uuid.uuid4().hex[:8], "time": int(time.time()),
             "iso": time.strftime("%F %T"), "cwd": cwd, "worktree": worktree_of(cwd),
             "command": command[:300], "kind": kind or kind_of(command), "pid": pid,
             "rss_mb": round(rss_mb), "job_rss_mb": round(job_rss_mb), "heavy_run_pid": heavy_run_pid}
    append_event(entry)
    return entry


def read_events() -> list:
    out = []
    try:
        with ledger_path().open(errors="replace") as fh:
            for line in fh:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    except OSError:
        pass
    return out


def open_entries(now=None, expire: bool = True) -> list:
    """Kills nobody has re-run yet. Entries older than 48 h expire (event + log line)."""
    now = now or time.time()
    events = read_events()
    closed = {e.get("id") for e in events if e.get("event") in ("done", "expired")}
    out = []
    for e in events:
        if e.get("event") != "kill" or e.get("id") in closed:
            continue
        if now - e.get("time", 0) > LEDGER_EXPIRY_S:
            if expire:
                append_event({"event": "expired", "id": e["id"], "time": int(now)})
                log(f"brake ledger: expired un-rerun kill id={e['id']} worktree={e.get('worktree')} cmd={e.get('command', '')[:80]}")
            continue
        out.append(e)
    return out


def mark_done(cwd: str, command: str, by_pid=None) -> int:
    """A heavy-run in this worktree exited 0: close the open kills it re-ran."""
    wt = worktree_of(cwd)
    kind, n = kind_of(command), 0
    for e in open_entries(expire=False):
        if e.get("worktree") != wt:
            continue
        if e.get("command") == command[:300] or (kind != "other" and e.get("kind") == kind) \
                or (kind != "other" and kind_of(e.get("command", "")) == kind):
            append_event({"event": "done", "id": e["id"], "time": int(time.time()), "by": command[:200], "pid": by_pid})
            n += 1
    return n


def killed_since(heavy_run_pid: int, since: float) -> bool:
    return any(e.get("event") == "kill" and e.get("heavy_run_pid") == heavy_run_pid and e.get("time", 0) >= int(since)
               for e in read_events())


def owns(entry: dict, chat_cwd: str) -> bool:
    """A chat owns a kill when its cwd is the entry's worktree or inside it (or resolves to the same repo)."""
    wt = entry.get("worktree") or ""
    if not wt or not chat_cwd:
        return False
    c = os.path.realpath(chat_cwd)
    return c == wt or c.startswith(wt + "/") or worktree_of(c) == wt


# ---------------------------------------------------------------- command rewriting

_TOOLS = r"(?:jest|tsc|eslint|vitest)"
_RUNNER = r"(?:(?:npx|bunx|pnpm\s+exec|pnpm\s+dlx|yarn|bun\s+x)\s+(?:-\S+\s+)*)?"
_BINDIR = r"(?:(?:\.?/)?(?:[\w.@-]+/)*node_modules/\.bin/)?"
HEAVY_RES = [
    re.compile(rf"^{_RUNNER}{_BINDIR}{_TOOLS}(?=\s|$)"),
    re.compile(r"^(?:node|bun|deno)\s+(?:-\S+\s+)*\S*(?:/jest(?:\.js)?|jest/bin/\S+|typescript/bin/tsc|/eslint\S*|/vitest\S*)(?=\s|$)"),
    re.compile(r"^(?:npx\s+|bunx\s+)?expo\s+export\b"),
    re.compile(r"^(?:npx\s+|bunx\s+)?next\s+build\b"),
    re.compile(r"^(?:npx\s+|bunx\s+)?playwright\s+test\b"),
    re.compile(r"^(?:bun|deno)\s+test\b"),
    re.compile(r"^deno\s+check\b"),
    re.compile(r"^(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:test|tests|lint|typecheck|type-check|tsc|build|check|ci|build:check|test:\S+|lint:\S+)(?=\s|$)"),
]
NOT_HEAVY = re.compile(r"(?:^|\s)(?:--help|-h|--version|-v|-V)(?=\s|$)")
_LEAD = re.compile(
    r"\s*(?:(?:then|do|else|elif|if|while|until|!|time|exec|command|nohup|env|nice(?:\s+-n\s*-?\d+)?)(?=\s)"
    r"|[A-Za-z_]\w*=(?:\"[^\"]*\"|'[^']*'|[^\s;&|]*)(?=\s))\s*")
_HR = re.compile(r"^(?:\S*/)?heavy-run(?=\s|$)")
_VAULT = re.compile(r"^(?:\S*/)?vault\s+run\b")
_SHC = re.compile(r"^(?:ba|z)?sh\s+(?:-\w+\s+)*-\w*c\s+(['\"])(.*)\1\s*$", re.S)


def is_heavy(text: str) -> bool:
    text = text.strip()
    return not NOT_HEAVY.search(text) and any(rx.search(text) for rx in HEAVY_RES)


def segments(cmd: str):
    """Top-level shell command segments as (start, end) offsets; None when unsafe to parse
    (heredoc, unbalanced quote). Quoted text, $VAR{...} and redirects are not split."""
    segs, start, i, n, q = [], 0, 0, len(cmd), None
    while i < n:
        c = cmd[i]
        if q:
            if c == "\\" and q == '"':
                i += 2
                continue
            if c == q:
                q = None
            i += 1
            continue
        if c == "\\":
            i += 2
            continue
        if c in "'\"":
            q = c
            i += 1
            continue
        if cmd.startswith("<<", i) and not cmd.startswith("<<<", i):
            return None
        if c == "#" and (i == 0 or cmd[i - 1] in " \t\n;&|("):
            j = cmd.find("\n", i)
            i = n if j < 0 else j
            continue
        if c == "&" and ((i > 0 and cmd[i - 1] in "<>") or cmd[i + 1:i + 2] == ">"):
            i += 1
            continue
        if c in ";\n|&(){`" and c not in "{}":
            segs.append((start, i))
            i += 1
            if c in "|&" and cmd[i:i + 1] == c:
                i += 1
            start = i
            continue
        i += 1
    if q:
        return None
    segs.append((start, n))
    return segs


def _insert_points(cmd: str, base: int = 0, depth: int = 0) -> list:
    segs = segments(cmd)
    if segs is None or depth > 3:
        return []
    points = []
    for s, e in segs:
        text, pos = cmd[s:e], 0
        while True:
            m = _LEAD.match(text, pos)
            if not m or m.end() == pos:
                break
            pos = m.end()
        rest = text[pos:]
        if not rest.strip() or _HR.match(rest):
            continue
        if _VAULT.match(rest):
            j = rest.find(" -- ")
            if j >= 0:
                points += _insert_points(rest[j + 4:], base + s + pos + j + 4, depth + 1)
            continue
        m = _SHC.match(rest)
        if m:
            if _insert_points(m.group(2), 0, depth + 1):
                points.append(base + s + pos)
            continue
        target = re.sub(r"^rtk\s+", "", rest.lstrip())
        if is_heavy(target):
            points.append(base + s + pos + (len(rest) - len(rest.lstrip())))
    return points


HEREDOC_HEAVY = re.compile(r"(?m)^\s*(?:npx\s+|bunx\s+)?(?:jest|tsc|eslint|vitest)\b|^\s*(?:npm|bun|yarn|pnpm)\s+(?:run\s+)?(?:test|lint|build|typecheck)\b")


def wrap_prefix(budget) -> str:
    return f"{heavy_run_bin()} --budget={int(budget)} "


def rewrite_command(cmd: str, budget: float = 100):
    """Returns (new_command, None) when heavy commands were wrapped, (None, instruction) when rewriting
    isn't safe but the command looks heavy, or (None, None) to leave it alone."""
    if not cmd or not os.path.exists(heavy_run_bin()):
        return None, None
    if segments(cmd) is None:
        if "<<" in cmd and HEREDOC_HEAVY.search(cmd):
            return None, ("heavy-run gate: this command mixes a heredoc with a heavy job (jest/tsc/eslint/build). "
                          f"Put the heavy command on its own call, wrapped: {heavy_run_bin()} <command>")
        return None, None
    points = sorted(set(_insert_points(cmd)), reverse=True)
    if not points:
        return None, None
    out = cmd
    for p in points:
        out = out[:p] + wrap_prefix(budget) + out[p:]
    return out, None
