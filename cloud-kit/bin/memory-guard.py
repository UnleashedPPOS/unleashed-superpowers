#!/usr/bin/env python3
"""memory-guard: keep the 8 GB Mac from freezing under heavy multi-session work.

Runs every 60 s from launchd (com.elliotkelly.memory-guard).

1. Reaps orphaned dev-tool processes: tool servers (MCP), wrangler, esbuild,
   test workers, etc. whose parent died (reparented to launchd, ppid 1) and
   that have stayed orphaned for 10+ minutes (tracked across runs). These are
   leftovers from closed Claude sessions or crashed tools.
   Only node/npm/npx/bun/tilth/esbuild processes whose program or script
   matches ORPHAN_PATTERNS are touched. launchd jobs and apps are never killed.
2. Watches macOS memory pressure. Warning is logged; critical pressure or swap
   over 6 GB sends one notification (at most every 30 min) naming the biggest
   memory users. It never quits your apps.

Usage: memory-guard.py [--dry-run]
Log: ~/Library/Logs/memory-guard.log
"""
from __future__ import annotations

import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

_HERE = os.path.dirname(os.path.realpath(__file__))
for _cand in (_HERE, os.path.join(_HERE, "..", "hooks")):
    if os.path.exists(os.path.join(_cand, "heavy_lib.py")):
        sys.path.insert(0, _cand)
        break
try:
    import heavy_lib  # shared ledger + gate records (installed next to this script)
except ImportError:  # degrade: the brake still works, it just can't write the ledger
    heavy_lib = None

LOG = Path(os.environ.get("MEMORY_GUARD_LOG") or (Path.home() / "Library/Logs/memory-guard.log"))
ERR_LOG = Path.home() / "Library/Logs/memory-guard.err.log"
STATE_DIR = Path(os.environ.get("MEMORY_GUARD_STATE_DIR") or (Path.home() / ".local/share/memory-guard"))
NOTIFY_STAMP = STATE_DIR / "last-notify"
ORPHANS_SEEN = STATE_DIR / "orphans-seen.json"
try:
    MIN_ORPHAN_AGE_S = int(os.environ.get("MEMORY_GUARD_MIN_AGE", 10 * 60))
except ValueError:
    MIN_ORPHAN_AGE_S = 10 * 60
NOTIFY_EVERY_S = 30 * 60
SWAP_ALERT_MB = 6000
LOG_MAX_LINES = 3000

# Only processes run by these programs are candidates; editors, shells,
# `claude`, `tail` etc. are never touched even if their args mention a pattern.
REAP_PROGRAMS = {"node", "npm", "npx", "bun", "tilth", "esbuild"}
# Matched against the first three argv tokens (program + script/subcommand).
ORPHAN_PATTERNS = [
    r"wrangler-dist/cli\.js",
    r"@playwright/mcp",
    r"playwright-mcp",
    r"mcp-server-",
    r"server-sequential-thinking",
    r"context-mode/.+/start\.mjs",
    r"^npm exec \S*mcp",
    r"^esbuild$",
    r"tsserver\.js",
    r"vitest/dist/(workers|child)",
    r"jest-worker",
]
ORPHAN_RE = re.compile("|".join(f"(?:{p})" for p in ORPHAN_PATTERNS))

APP_GROUPS = [
    (re.compile(r"Google Chrome"), "Chrome"),
    (re.compile(r"Claude Helper|^Claude$"), "Claude app"),
    (re.compile(r"^claude"), "Claude Code sessions"),
    (re.compile(r"node"), "Node tools"),
    (re.compile(r"Simulator|SimRender"), "iOS Simulator"),
    (re.compile(r"com\.docker|Docker|qemu"), "Docker"),
    (re.compile(r"Xcode"), "Xcode"),
    (re.compile(r"[Pp]ython"), "Python jobs"),
]
PRESSURE_NAMES = {1: "normal", 2: "warning", 4: "critical"}


def log(msg: str) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a") as fh:
            fh.write(f"{time.strftime('%F %T')} {msg}\n")
    except OSError:
        pass


def trim(path: Path) -> None:
    try:
        lines = path.read_text(errors="replace").splitlines()
        if len(lines) > LOG_MAX_LINES:
            path.write_text("\n".join(lines[-(LOG_MAX_LINES // 2):]) + "\n")
    except OSError:
        pass


def run(argv: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(argv, capture_output=True, text=True, errors="replace",
                              timeout=20, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None


def out(argv: list[str]) -> str:
    result = run(argv)
    return result.stdout if result else ""


def launchd_job_pids() -> set[int]:
    """PIDs launchd runs as jobs (also ppid 1, but never orphans)."""
    pids = set()
    for line in out(["launchctl", "list"]).splitlines()[1:]:
        first = line.split("\t", 1)[0]
        if first.isdigit():
            pids.add(int(first))
    return pids


def is_reap_candidate(command: str) -> bool:
    tokens = command.split()
    if not tokens or os.path.basename(tokens[0]) not in REAP_PROGRAMS:
        return False
    program = os.path.basename(tokens[0])
    if program == "tilth":
        return "--mcp" in tokens
    # Skip interpreter flags (node --max-old-space-size=… script.js) to reach the script.
    args = [t for t in tokens[1:] if not t.startswith("-")]
    # The script (node foo.js) or, for npm/npx, the subcommand + package.
    head = " ".join([program, *args[:2 if program in {"npm", "npx"} else 1]])
    return bool(ORPHAN_RE.search(head))


def orphan_candidates() -> dict[str, tuple[int, str]]:
    """ppid-1 dev-tool processes, keyed by 'pid@start-time' so pid reuse can't alias."""
    job_pids = launchd_job_pids()
    found: dict[str, tuple[int, str]] = {}
    for line in out(["ps", "-axo", "pid=,ppid=,lstart=,command="]).splitlines():
        parts = line.split(None, 7)
        if len(parts) < 8 or parts[1] != "1" or not parts[0].isdigit():
            continue
        pid, command = int(parts[0]), parts[7]
        if pid in job_pids or not is_reap_candidate(command):
            continue
        found[f"{pid}@{' '.join(parts[2:7])}"] = (pid, command)
    return found


def load_seen() -> dict[str, float]:
    try:
        data = json.loads(ORPHANS_SEEN.read_text())
        return {k: float(v) for k, v in data.items()} if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def save_seen(seen: dict[str, float]) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        ORPHANS_SEEN.write_text(json.dumps(seen))
    except OSError:
        pass


def reap_orphans(dry_run: bool) -> int:
    now = time.time()
    candidates = orphan_candidates()
    previous = load_seen()
    # First-seen time per orphan; entries for exited processes drop out.
    seen = {key: previous.get(key, now) for key in candidates}
    if not dry_run:
        save_seen(seen)
    signalled: dict[str, int] = {}
    for key, (pid, command) in candidates.items():
        orphaned_for = now - seen[key]
        if orphaned_for < MIN_ORPHAN_AGE_S:
            continue
        if dry_run:
            log(f"would reap orphan pid={pid} orphaned={orphaned_for:.0f}s cmd={command[:140]}")
            continue
        try:
            os.kill(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError) as exc:
            log(f"could not reap pid={pid}: {exc.__class__.__name__}")
            continue
        signalled[key] = pid
        log(f"reaped orphan pid={pid} orphaned={orphaned_for:.0f}s cmd={command[:140]}")
    if signalled:
        time.sleep(3)
        # SIGKILL only the exact processes (same pid AND start time) that ignored SIGTERM.
        still_there = orphan_candidates()
        for key, pid in signalled.items():
            if key in still_there:
                try:
                    os.kill(pid, signal.SIGKILL)
                    log(f"force-killed pid={pid} (ignored SIGTERM)")
                except (ProcessLookupError, PermissionError):
                    pass
    return len(signalled)


def pressure_level() -> int:
    try:
        return int(out(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]).strip() or 1)
    except ValueError:
        return 1


def swap_used_mb() -> float:
    match = re.search(r"used = ([0-9.]+)M", out(["sysctl", "-n", "vm.swapusage"]))
    return float(match.group(1)) if match else 0.0


def top_memory_users(limit: int = 3) -> list[tuple[str, float]]:
    """Group memory footprint (incl. compressed) by app, biggest first."""
    totals: dict[str, float] = {}
    units = {"B": 1 / 1048576, "K": 1 / 1024, "M": 1, "G": 1024}
    for line in out(["top", "-l", "1", "-o", "mem", "-n", "300", "-stats", "mem,command"]).splitlines():
        match = re.match(r"\s*([0-9.]+)([BKMG])[+-]?\s+(.+)$", line)
        if not match:
            continue
        mb = float(match.group(1)) * units[match.group(2)]
        command = match.group(3).strip()
        name = next((label for regex, label in APP_GROUPS if regex.search(command)), command)
        totals[name] = totals.get(name, 0) + mb
    return sorted(totals.items(), key=lambda item: -item[1])[:limit]


def notify(title: str, body: str) -> bool:
    safe_body = body.replace("\\", "/").replace('"', "'")
    result = run(["osascript", "-e",
                  f'display notification "{safe_body}" with title "{title}" sound name "Funk"'])
    return bool(result and result.returncode == 0)


def should_notify() -> bool:
    try:
        return time.time() - NOTIFY_STAMP.stat().st_mtime > NOTIFY_EVERY_S
    except OSError:
        return True


def send_alert(title: str, body: str) -> None:
    if notify(title, body):
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            NOTIFY_STAMP.touch()
        except OSError:
            pass
    else:
        log("notification failed to send")


# Brake (added 2026-11-21 after a forced restart: live jest/tsc from several
# Claude sessions reached 16 GB on an 8 GB Mac). Under critical pressure or
# swap over BRAKE_SWAP_MB, kill LIVE heavy dev jobs (biggest first) until about
# BRAKE_FREE_MB is freed. Apps, editors, Claude, MCP servers, xcodebuild and
# EAS builds are never touched. Each killed job goes in the brake ledger; the owning chat is told to re-run it.
BRAKE_SWAP_MB = 5000
BRAKE_FREE_MB = 900  # biggest single job seen 897 MB, biggest event total 1656 MB
BRAKE_MAX_KILLS_PER_CYCLE = 1  # kill one job, then re-check next cycle
BRAKE_PATTERNS = re.compile(
    r"jest-worker|/jest(\.js)?\b|jest/bin|\bjest\b|/tsc\b|typescript/bin/tsc|tsserver\.js"
    r"|vitest|eslint|expo(/bin/cli)? export|expo-router.*export|metro|webpack|next build|next-server"
    r"|deno (test|check)|playwright test|bun test|react-native bundle|tsx watch"
)
BUILD_SPARE = re.compile(r"export|metro|react-native bundle|/tmp/.*eas-build|eas-build-local")
BRAKE_NEVER = re.compile(r"xcodebuild|eas-cli|eas build|EAS_BUILD|Claude\.app|/claude\b|mcp|heavy-run")


def etime_s(text: str) -> int:
    """ps etime ([[dd-]hh:]mm:ss) -> seconds."""
    days, _, rest = text.rpartition("-")
    try:
        secs = 0
        for n in [int(x) for x in rest.split(":")]:
            secs = secs * 60 + n
        return secs + (int(days) * 86400 if days else 0)
    except ValueError:
        return 0


def ps_table() -> dict:
    """pid -> (ppid, rss_mb, command, age_s)."""
    table = {}
    for line in out(["ps", "-axo", "pid=,ppid=,rss=,etime=,command="]).splitlines():
        parts = line.split(None, 4)
        if len(parts) < 5 or not all(p.isdigit() for p in parts[:3]):
            continue
        table[int(parts[0])] = (int(parts[1]), int(parts[2]) / 1024, parts[4], etime_s(parts[3]))
    return table


def pid_cwd(pid: int) -> str:
    for line in out(["lsof", "-a", "-d", "cwd", "-p", str(pid), "-Fn"]).splitlines():
        if line.startswith("n"):
            return line[1:]
    return ""


def brake(dry_run: bool, critical: bool = True) -> int:
    """Kill whole heavy JOBS (a jest run = parent + workers). Never on swap alone with fewer than 2 jobs
    (killing a lone job just makes it start again and die again); the oldest job is spared when there are
    2+, the biggest of the rest goes first, and at most BRAKE_MAX_KILLS_PER_CYCLE die per run. Jobs waiting
    in the heavy-run gate are not processes of these programs, so they are never touched."""
    table = ps_table()
    heavy = set()
    for pid, (_ppid, _rss, command, _age) in table.items():
        prog = os.path.basename(command.split()[0])
        if prog not in {"node", "bun", "deno", "npx", "npm"} and "node" not in prog:
            continue
        if BRAKE_NEVER.search(command) or not BRAKE_PATTERNS.search(command):
            continue
        # A local EAS build bundles JS with expo export:embed / metro; touch
        # ~/.local/share/memory-guard/build-active while it runs to spare those.
        if (STATE_DIR / "build-active").exists() and BUILD_SPARE.search(command):
            continue
        heavy.add(pid)

    def root(pid: int) -> int:
        while table[pid][0] in heavy:
            pid = table[pid][0]
        return pid

    jobs: dict = {}
    for pid in heavy:
        jobs.setdefault(root(pid), []).append(pid)
    records = heavy_lib.gate_records() if heavy_lib else []

    def find_rec(root_pid: int):
        # Map the job back to a heavy-run slot (record.child is the job or an ancestor of it).
        cur = root_pid
        while cur in table:
            rec = next((r for r in records if r.get("child") == cur), None)
            if rec:
                return rec
            cur = table[cur][0]
            if cur <= 1:
                break
        return None

    recs = {r: find_rec(r) for r in jobs}
    # Only jobs started by heavy-run count as "jobs" for the lone-job rule and the oldest-spared rule;
    # long-running servers (tsserver, next-server, metro) stay killable at critical pressure only.
    gated = [r for r in jobs if recs[r]]
    if not critical and len(gated) < 2:
        return 0
    pool = jobs if critical else {r: jobs[r] for r in gated}
    ranked = sorted(pool.items(), key=lambda kv: -sum(table[p][1] for p in kv[1]))
    if len(gated) >= 2:
        oldest = max(gated, key=lambda r: table[r][3])
        ranked = [kv for kv in ranked if kv[0] != oldest]
    freed, killed = 0.0, 0
    for root_pid, members in ranked:
        if freed >= BRAKE_FREE_MB or killed >= BRAKE_MAX_KILLS_PER_CYCLE:
            break
        size = sum(table[p][1] for p in members)
        rec = recs[root_pid]
        command = (rec or {}).get("cmd") or table[root_pid][2]
        cwd = (rec or {}).get("cwd") or pid_cwd(root_pid)
        if dry_run:
            log(f"brake would kill job root={root_pid} procs={len(members)} {size:.0f}MB cwd={cwd} cmd={command[:100]}")
        else:
            for pid in [root_pid] + [p for p in members if p != root_pid]:
                try:
                    os.kill(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    continue
            log(f"brake killed job root={root_pid} procs={len(members)} {size:.0f}MB cwd={cwd} cmd={command[:100]}")
            if heavy_lib:
                heavy_lib.record_kill(cwd, command, root_pid, table[root_pid][1], size,
                                      (rec or {}).get("pid"), heavy_lib.kind_of(table[root_pid][2]) if not rec else None)
        freed += size
        killed += 1
    return killed


def main() -> None:
    dry_run = "--dry-run" in sys.argv
    reaped = reap_orphans(dry_run)
    level = pressure_level()
    swap = swap_used_mb()
    if level >= 4 or swap > BRAKE_SWAP_MB:
        braked = brake(dry_run, critical=level >= 4)
        if braked and not dry_run:
            send_alert("Memory brake", f"Stopped {braked} heavy test/build jobs to keep the Mac alive.")
    if level >= 2 or swap > SWAP_ALERT_MB:
        users = top_memory_users()
        summary = ", ".join(f"{name} {mb / 1024:.1f}GB" for name, mb in users)
        log(f"pressure={PRESSURE_NAMES.get(level, level)} swap={swap:.0f}MB reaped={reaped} top: {summary}")
        if not dry_run and should_notify():
            if level >= 4:
                send_alert("Memory critical — close something now",
                           f"Biggest: {summary}. Close tabs or a Claude session.")
            elif swap > SWAP_ALERT_MB:
                send_alert("Memory is getting tight", f"Swap {swap / 1024:.1f}GB. Biggest: {summary}.")
    elif reaped:
        log(f"pressure=normal swap={swap:.0f}MB reaped={reaped}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001 - keep running every interval; record why
        log(f"error: {exc.__class__.__name__}: {exc}")
    finally:
        trim(LOG)
        trim(ERR_LOG)
