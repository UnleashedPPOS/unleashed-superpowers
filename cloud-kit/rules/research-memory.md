# Research is saved once, then updated — never redone (HARD RULE, 2026-10-02)

Cloud session: the Mac memory dir does not exist. Clone UnleashedPPOS/unleashed-memory and push there; if that fails, put the full findings in the PR body (or a GitHub issue) and say so. yt-dlp steps go on the founder's local-ops list.

Founder: "when I ask you to do research… get it saved in the Unleashed memory so you don't need to research again, or you just need to update the research."

## Before researching
1. Check memory for an existing `research-<topic>` file (read memory `index-research.md`, then `~/.claude/projects/-Users-elliotkelly-Developer/memory/research-*.md`).
2. If found: read it, open its linked report, and only UPDATE what's stale or missing (note the date of the update). Don't start from scratch.

## After researching (every time)
1. CANONICAL STORE = repo UnleashedPPOS/unleashed-memory (founder 2026-10-02: "it was supposed to be saving in UnleashedMemories"). Follow its CLAUDE.md ingest workflow: raw sources → `raw/research/<topic>/`, summary → `wiki/investigations/<topic>.md`, update `index.md` + `log.md`, push to main. A working copy may also live in the product repo.
1b. Always produce a self-contained `report.html` of ALL findings for the founder to browse, saved alongside the raw sources.
2. A memory file `research-<topic>.md` (type: reference): date, one-paragraph conclusion, headline numbers, the report path/PR link, what's still unverified, and when it should be refreshed.
3. One line in memory `index-research.md` (not MEMORY.md).

## Tools
- Broad "what are people saying / what's new" research: the last30days skill (github.com/mvanhorn/last30days-skill — Reddit, X, YouTube, HN, Polymarket, web).
- YouTube transcripts: cloud sandboxes block youtube.com → run `yt-dlp --skip-download --write-auto-subs` locally (on the Mac) (light, text only), push results, analyse in the cloud.
