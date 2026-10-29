#!/usr/bin/env python3
"""mac-tuneup diagnose: one read-only snapshot of why the Mac is slow or full.

Changes nothing. Prints a short report: memory, swap, CPU hogs, memory hogs
grouped by app, Claude sessions, orphaned tool processes, background jobs
that are failing, disk free and the biggest reclaimable folders.

Usage: diagnose.py [--fast]   (--fast skips folder sizing)
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
FAST = "--fast" in sys.argv

# (label, path, note). Notes say what clearing costs; see REFERENCE.md.
SIZE_TARGETS = [
    ("Trash", "~/.Trash", "empty it (founder does this)"),
    ("User caches", "~/Library/Caches", "safe, regrows"),
    ("npm cache", "~/.npm/_cacache", "safe: npm cache clean --force"),
    ("bun cache", "~/.bun/install/cache", "safe: bun pm cache rm"),
    ("uv cache", "~/.cache/uv", "safe: uv cache clean"),
    ("pip cache", "~/Library/Caches/pip", "safe"),
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


def sh(cmd: str, timeout: int = 30) -> str:
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, text=True,
                              errors="replace", timeout=timeout).stdout
    except subprocess.TimeoutExpired:
        return ""


def size_gb(path: str) -> float | None:
    full = os.path.expanduser(path)
    if not os.path.exists(full):
        return None
    out = sh(f'du -sk "{full}" 2>/dev/null', timeout=90).split()
    return int(out[0]) / 1048576 if out and out[0].isdigit() else None


def load_guard():
    """Reuse memory-guard's grouping and orphan matcher instead of duplicating them."""
    path = HOME / "bin/memory-guard.py"
    if not path.exists():
        return None
    spec = importlib.util.spec_from_file_location("memory_guard", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def section(title: str) -> None:
    print(f"\n== {title}")


def main() -> None:
    guard = load_guard()

    section("Memory")
    free = re.search(r"(\d+)%", sh("memory_pressure | tail -1"))
    swap = re.search(r"used = ([0-9.]+)M", sh("sysctl -n vm.swapusage"))
    level = sh("sysctl -n kern.memorystatus_vm_pressure_level").strip()
    print(f"free {free.group(1) if free else '?'}% · swap {float(swap.group(1)) / 1024 if swap else 0:.1f} GB"
          f" · pressure {({'1': 'normal', '2': 'WARNING', '4': 'CRITICAL'}).get(level, level)}")
    print("healthy: free >= 30%, swap < 4 GB")
    if guard:
        print("biggest: " + ", ".join(f"{n} {mb / 1024:.1f} GB" for n, mb in guard.top_memory_users(6)))

    section("CPU (top 6, %)")
    for line in sh("ps -Ao pcpu,comm -r").splitlines()[1:7]:
        pct, _, cmd = line.strip().partition(" ")
        print(f"{pct:>5}  {os.path.basename(cmd.strip())[:60]}")
    print(sh("uptime").strip())

    section("Claude + Chrome")
    claude_sessions = len([l for l in sh("ps -Ao comm").splitlines() if l.strip().endswith("/claude")])
    renderers = len([l for l in sh("ps -Ao comm").splitlines() if "Google Chrome Helper" in l and "Renderer)" in l])
    print(f"Claude Code sessions running: {claude_sessions} (aim for 2-3 on 8 GB)")
    print(f"Chrome tab/renderer processes: {renderers}")
    if guard:
        orphans = guard.orphan_candidates()
        print(f"orphaned tool processes (memory-guard reaps after 10 min): {len(orphans)}")

    section("Background jobs with a failing last exit")
    failing = []
    for line in sh("launchctl list").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) == 3 and not parts[2].startswith("com.apple") and parts[1] not in ("0", "-"):
            failing.append(f"{parts[2]} (exit {parts[1]})")
    print("\n".join(failing) or "none")
    log = HOME / "Library/Logs/memory-guard.log"
    if log.exists():
        tail = log.read_text(errors="replace").splitlines()[-3:]
        print("memory-guard last lines:\n  " + "\n  ".join(tail or ["(empty)"]))

    section("Disk")
    df = sh("df -k /").splitlines()[1].split()
    print(f"free {int(df[3]) / 1048576:.1f} GB of {int(df[1]) / 1048576:.0f} GB (healthy: > 25 GB)")
    snaps = len([l for l in sh("tmutil listlocalsnapshots / 2>/dev/null").splitlines() if "com.apple" in l])
    print(f"Time Machine local snapshots: {snaps}")
    update = sh("softwareupdate -l 2>&1", timeout=60)
    print("macOS update waiting: " + ("yes" if "Label:" in update else "no"))
    if FAST:
        return
    section("Biggest folders (GB)")
    rows = [(size_gb(p), label, note) for label, p, note in SIZE_TARGETS]
    for gb, label, note in sorted((r for r in rows if r[0] is not None), key=lambda r: -r[0]):
        if gb >= 0.3:
            print(f"{gb:6.1f}  {label:<24} {note}")


if __name__ == "__main__":
    main()
