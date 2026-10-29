# Mac tune-up reference

Machine: MacBook Air, 8 GB RAM, 228 GB disk. The biggest memory users are always
the Claude app, Chrome and Claude Code sessions; some swap is normal.

## Automation already running (check it's alive before adding anything)

| Job | What it does |
|---|---|
| `com.elliotkelly.memory-guard` → `~/bin/memory-guard.py` | Every 2 min. Kills dev-tool processes (MCP servers, wrangler, esbuild, test workers) orphaned 10+ min. Notifies on critical pressure or swap > 6 GB, at most every 30 min. Log `~/Library/Logs/memory-guard.log` ("pressure=warning" lines are normal on 8 GB). |
| `com.elliotkelly.mac-health-watchdog` → `~/bin/mac-health-watchdog.sh` | Daily; runs `~/bin/disk-maintenance.sh`. |
| `~/bin/disk-maintenance.sh` | Removes idle worktrees (2 days), rebuildable deps in idle repos (3 days), offloads repos untouched 10 days to GitHub-only. Never touches unpushed work. `report`, `--dry-run`, `restore <repo>`, `list-offloaded`. Keep-list `~/Developer/.offload-keep`. Not in git. |
| `com.elliotkelly.chrome-cache-janitor` | Trims Chrome caches. |
| `com.unleashed.diskguard` → `~/.local/bin/disk-guard.sh` | Low-disk guard. |

## Known-OK oddities

- `vision.unleashed.ump-runner`, `ump-dashboard`, `ump-stocks` show exit 1 every few minutes. They're healthy: they report that the trading processes are already running.
- Spotlight indexing on `/` is disabled. That's deliberate (it saves CPU); don't re-enable it without asking.
- Claude Code worktrees under `<repo>/.claude/worktrees` are managed by the app's reuse pool; disk-maintenance handles idle ones.

## Cache verdicts

- npm / bun / uv caches, Xcode DerivedData: safe to clear and they regrow. Worth it only when disk is tight.
- `~/Library/Caches`: never wipe it whole (apps lose logins/state). Clear only named folders of tools you know (pip, Homebrew, an uninstalled app's folder).
- Claude app cache (`~/Library/Application Support/Claude/Cache`, about 1 GB, plus Code Cache): it's web cache for the app's pages. Clearing it gains space for days only and makes the app slower until it refills. Skip unless disk < 15 GB. Never clear `Partitions`: the browser-pane logins live there.
- Voice Memos: iCloud sync on this Mac is OFF on purpose. With it on, the Mac keeps a full copy (6.8 GB). The recordings live on the iPhone and in iCloud.
- Photos: iCloud Photos is off. If the library bloats, the stale `database/search` index is the likely cause (it was 4.3 GB). Don't edit inside the library yourself: give the founder the Photos repair step (quit Photos, hold ⌥⌘ while opening it, choose Repair), or ask before touching that folder.
- Docker (about 3.5 GB): KEEP. The unleashed-voice docker-compose stack, Studio's test-db and deploy scripts need it. While it's quit it costs disk only.
- WhatsApp (about 6 GB): the founder clears it via WhatsApp → Settings → Storage and data → Manage storage.

## Settings already applied (don't re-suggest)

- Chrome Memory Saver on Maximum and restore tabs on startup (Local State `performance_tuning.memory_saver_mode.aggressiveness=2`; backups `*.bak-2026-10-29`).
- Reduce transparency is on.
- The Claude app starts no MCP servers. Unused Cloudflare, Firebase and Ollama MCPs are removed. Everygen, Higgsfield and Indeed connectors are disconnected.
- Login items trimmed (Google Drive kept). Fathom, Paste, NordVPN and Postman are gone, and so are the NordVPN and BlueStacks daemons and the Zoom updater agents.
- Atlas runner: 60 s poll, backoff, reaps orphaned wrangler (atlas-live #7/#8). The Atlas Live task runner is switched off; turn it back on only if asked.

## Escalation ideas when the basics are clean

- Swap stays > 6 GB with few sessions → look for a leaking app (`top -o mem`, watch it grow) and restart that app.
- Uptime > 7 days → suggest a restart.
- A macOS update is waiting → the founder installs it (System Settings → General → Software Update).
- If the healthy floor is still missed with 2 sessions and few tabs, the hardware is the limit (8 GB). Say so plainly.
