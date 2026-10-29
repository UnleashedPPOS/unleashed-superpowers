#!/usr/bin/env python3
"""mac-tuneup diagnose: one read-only snapshot of why the Mac is slow or full.

Changes nothing. Prints a short report: memory, swap, CPU hogs, memory hogs
grouped by app, Claude sessions, orphaned tool processes, background jobs
that are failing, disk free and the biggest reclaimable folders.

Usage: diagnose.py [--fast]   (--fast skips folder sizing and the update check)
"""
from __future__ import annotations

import importlib.util
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
FAST = "--fast" in sys.argv
# launchd jobs get a bare PATH; the macOS tools live in sbin.
os.environ["PATH"] = "/usr/sbin:/usr/bin:/sbin:/bin:" + os.environ.get("PATH", "")

# Jobs whose non-zero exit is expected (see REFERENCE.md "Known-OK oddities").
KNOWN_OK_JOBS = {"vision.unleashed.ump-runner", "vision.unleashed.ump-dashboard", "vision.unleashed.ump-stocks"}

# (label, path, note). Notes say what clearing costs; see REFERENCE.md.
SIZE_TARGETS = [
    ("Trash", "~/.Trash", "founder empties it"),
    ("User caches", "~/Library/Caches", "clear named app folders only"),
    ("npm cache", "~/.npm/_cacache", "safe: npm cache clean --force"),
    ("bun cache", "~/.bun/install/cache", "safe: bun pm cache rm"),
    ("uv cache", "~/.cache/uv", "safe: uv cache clean"),
    ("Xcode DerivedData", "~/Library/Developer/Xcode/DerivedData", "safe, rebuilds"),
    ("Xcode archives", "~/Library/Developer/Xcode/Archives", "ask: old app builds"),
    ("iOS DeviceSupport", "~/Library/Developer/Xcode/iOS DeviceSupport", "safe, re-downloads"),
    ("Simulators", "~/Library/Developer/CoreSimulator/Devices", "xcrun simctl delete unavailable"),
    ("Android SDK", "~/Library/Android/sdk", "ask: emulator images"),
    ("Docker", "~/Library/Containers/com.docker.docker", "KEEP (voice stack, studio test-db)"),
    ("Claude app cache", "~/Library/Application Support/Claude/Cache", "pointless: regrows in days"),
    ("Claude app partitions", "~/Library/Application Support/Claude/Partitions", "browser-pane logins live here"),
    ("Claude chat history", "~/.claude/projects", "keep (archived by chat-archive job)"),
    ("Voice Memos", "~/Library/Group Containers/group.com.apple.VoiceMemos.shared", "sync is off on purpose"),
    ("Photos library", "~/Pictures/Photos Library.photoslibrary", "iCloud Photos off"),
    ("WhatsApp", "~/Library/Group Containers/group.net.whatsapp.WhatsApp.shared", "WhatsApp > Storage > Manage"),
    ("Downloads", "~/Downloads", "ask before trashing"),
    ("Developer (code)", "~/Developer", "disk-maintenance.sh report"),
]


def run(argv: list[str], timeout: int = 30) -> str | None:
    """stdout of argv, or None if it could not run or timed out."""
    try:
        return subprocess.run(argv, capture_output=True, text=True, errors="replace",
                              timeout=timeout, check=False).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None


def sh(argv: list[str], timeout: int = 30) -> str:
    return run(argv, timeout) or ""


def size_gb(path: str) -> float | str | None:
    """Folder size in GB, None if missing, 'timed out' if du gave up."""
    full = os.path.expanduser(path)
    if not os.path.exists(full):
        return None
    out = run(["du", "-sk", full], timeout=90)
    if out is None:
        return "timed out"
    first = out.split()[:1]
    return int(first[0]) / 1048576 if first and first[0].isdigit() else "unreadable"


def load_guard():
    """Reuse memory-guard's grouping and orphan matcher instead of duplicating them."""
    path = HOME / "bin/memory-guard.py"
    if not path.exists():
        return None
    try:
        spec = importlib.util.spec_from_file_location("memory_guard", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as exc:  # noqa: BLE001 - a broken guard must not kill the report
        print(f"(memory-guard.py failed to load: {exc.__class__.__name__}; its checks are skipped)")
        return None


def section(title: str) -> None:
    print(f"\n== {title}")


def update_status() -> str:
    out = run(["softwareupdate", "-l"], timeout=60)
    if out is None:
        return "unknown (check timed out)"
    if "Label:" in out:
        return "yes"
    return "no" if "No new software available" in out else "unknown"


def main() -> None:
    guard = load_guard()

    section("Memory")
    free = re.search(r"(\d+)%", sh(["memory_pressure"]))
    swap = re.search(r"used = ([0-9.]+)M", sh(["sysctl", "-n", "vm.swapusage"]))
    level = sh(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"]).strip()
    print(f"free {free.group(1) if free else '?'}% · swap {float(swap.group(1)) / 1024 if swap else 0:.1f} GB"
          f" · pressure {({'1': 'normal', '2': 'WARNING', '4': 'CRITICAL'}).get(level, level or '?')}")
    print("healthy: free >= 30%, swap < 4 GB")
    if guard:
        print("biggest: " + ", ".join(f"{n} {mb / 1024:.1f} GB" for n, mb in guard.top_memory_users(6)))

    section("CPU (top 6, % averaged over the last minute)")
    for line in sh(["ps", "-Ao", "pcpu,comm", "-r"]).splitlines()[1:7]:
        pct, _, cmd = line.strip().partition(" ")
        print(f"{pct:>5}  {os.path.basename(cmd.strip())[:60]}")
    print(sh(["uptime"]).strip())

    section("Claude + Chrome")
    commands = sh(["ps", "-Ao", "comm"]).splitlines()
    claude_sessions = sum(1 for c in commands if c.strip().endswith("/claude"))
    renderers = sum(1 for c in commands if "Google Chrome Helper" in c and "Renderer)" in c)
    print(f"Claude Code sessions running: {claude_sessions}, including this one (aim for 2-3 on 8 GB)")
    print(f"Chrome tab/renderer processes: {renderers}")
    if guard:
        print(f"orphaned tool processes (memory-guard reaps after 10 min): {len(guard.orphan_candidates())}")

    section("Background jobs with a failing last exit")
    failing = []
    for line in sh(["launchctl", "list"]).splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) == 3 and not parts[2].startswith("com.apple") and parts[1] not in ("0", "-"):
            tag = " (known-OK)" if parts[2] in KNOWN_OK_JOBS else ""
            failing.append(f"{parts[2]} (exit {parts[1]}){tag}")
    print("\n".join(failing) or "none")
    log = HOME / "Library/Logs/memory-guard.log"
    if log.exists():
        tail = log.read_text(errors="replace").splitlines()[-3:]
        print("memory-guard last lines:\n  " + "\n  ".join(tail or ["(empty)"]))

    section("Disk")
    usage = shutil.disk_usage("/")
    print(f"free {usage.free / 2**30:.1f} GB of {usage.total / 2**30:.0f} GB (healthy: > 25 GB)")
    snaps = sum(1 for l in sh(["tmutil", "listlocalsnapshots", "/"]).splitlines() if "com.apple" in l)
    print(f"Time Machine local snapshots: {snaps}")
    if FAST:
        return
    print(f"macOS update waiting: {update_status()}")
    section("Biggest folders (GB)")
    rows = [(size_gb(p), label, note) for label, p, note in SIZE_TARGETS]
    for gb, label, note in sorted((r for r in rows if isinstance(r[0], float)), key=lambda r: -r[0]):
        if gb >= 0.3:
            print(f"{gb:6.1f}  {label:<24} {note}")
    for status, label, _ in rows:
        if isinstance(status, str):
            print(f"{status:>9}  {label} (size not measured)")


if __name__ == "__main__":
    main()
