---
name: research-memory
description: "Save research once in the Unleashed memory, then update it instead of redoing it. Use before and after any research, investigation, market scan, competitor review, 'what are people saying', last30days, YouTube transcript or report.html job, and when the founder says 'research', 'look into', 'find out what's new' or 'save it to memory'. SKIP for a code lookup inside one repo."
---

# Research memory

**Announce at start:** "I'm using the research-memory skill to check what we already know."

## Thesis
Founder 2026-10-02: "get it saved in the Unleashed memory so you don't need to research again, or you just need to update the research." Research is a cached asset: check before, file after, every time. The canonical store is the repo UnleashedPPOS/unleashed-memory.

## When this fires
- Before any research task (to find what exists) and after it (to file it).

## Mandatory checklist

### Pass 1: before researching
1. Read memory `index-research.md`, then `research-*.md` in the memory dir; in unleashed-memory run `bin/search.sh <terms>` and `bin/ask.sh "<question>"`.
2. Found: read it and its linked report; update only what is stale or missing, with the update date. Don't start from scratch.

### Pass 2: research
1. Broad "what are people saying / what's new": the last30days skill (Reddit, X, YouTube, HN, Polymarket, web).
2. YouTube transcripts: cloud sandboxes block youtube.com. `yt-dlp --skip-download --write-auto-subs` runs on the Mac (local-ops list), results get pushed, analysis happens in the cloud.

### Pass 3: file it (every time)
1. Raw sources → `raw/research/<topic>/` in unleashed-memory, captured in full.
2. A self-contained `report.html` of ALL findings beside the raw sources.
3. Summary → `wiki/investigations/<topic>.md`; update `index.md` and `log.md`; push to main (follow that repo's CLAUDE.md ingest workflow).
4. Memory file `research-<topic>.md` (type: reference): date, one-paragraph conclusion, headline numbers, report path or PR link, what is unverified, when to refresh.
5. One line in memory `index-research.md` (not MEMORY.md).
6. Cloud session with no Mac memory dir: push to unleashed-memory; if that fails, put the full findings in the PR body or an issue and say so.

## Anti-pattern flags
- "Let me research X from scratch" without checking the index.
- Findings left only in a chat transcript.

## Integration with other skills
- `/learnings` for corrections; this skill for facts about the world.

## Red flags
| Thought | Reality |
|---|---|
| "It's quicker to search again" | It isn't, and the founder pays twice. |
| "The summary is enough" | Raw sources in full plus report.html, every time. |

## Reference
- unleashed-memory `CLAUDE.md` (ingest doctrine).
