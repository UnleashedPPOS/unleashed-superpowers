---
name: document-feature-module
description: Produce reference-quality documentation for a feature module in Unleashed OS. Enforces the senior-engineer + senior-designer lenses, source-grounded accuracy, verb-first copy patterns, and the multi-file structure proven on the Vision module.
---

# Document a Feature Module

Use this skill when a feature area needs reference-quality docs — either new from scratch, or a refactor where existing docs have drifted from reality.

The output is a `docs/feature-modules/<area>/` folder (or a flat `.md` with the same sections if the area is small) that a new contributor — or an AI agent — can trust without cross-checking the source.

## The golden rule

**Every factual claim resolves to a grepable symbol in the current codebase.** Prop signatures, type names, hook names, query keys, env var names, rate limit numbers, secret names, table names, RLS policies — all of it. If you can't grep it, don't write it. This is how we avoid the "fictitious-export" class of bug (docs claiming `GoalCategory` union / `categoryConfig` const exist when they don't) that earned the Vision module a BLOCK on first review.

## Two lenses every section must pass

### Senior Engineer lens

For each section, ask:
- Does every code claim resolve to a real symbol I can grep?
- Are invariants justified with a **Why:** line — what breaks if I change this?
- Are extension points specific (file + function + the exact change I'd make), not vague?
- Is the failure mode for each piece documented (rate limit hit? offline? auth expired? Suno hung?)
- Are perf characteristics named (debounce ms, query staleTime, edge function timeout, Deepgram round-trip)?
- Are *Why:* lines present on any "do-not-touch" item so edge cases can be judged rather than blindly followed?

### Senior Designer lens

For each section, ask:
- Is the user-facing label consistent across docs, UI, copy, and marketing? (See **Naming** section below.)
- Are empty states, loading copy, and error toasts spec'd verbatim?
- Are the visual/interaction primitives identified (cards `rounded-2xl`, buttons `rounded-xl`, mic-button placement, toast deduplication IDs)?
- Are accessibility rules explicit (`aria-label` on interactive controls, `DialogTitle` for Radix screen-reader compliance, focus management, keyboard map)?
- Do empty-state CTAs and error toasts follow the verb-pattern conventions below?

Both lenses pass → section can ship. Either fails → section isn't done.

## Copy & logic patterns (apply globally)

Consistent verb structure stops AI agents (and humans) from drifting when they write new UI. Enforce these across every doc:

| Where | Pattern | Example |
|---|---|---|
| Action labels / CTAs | **Verb-first imperative** | "Add new idea", "Generate image", "Talk it out" — never "New idea", "Image", "Talk" |
| Toast on success | **Past-tense + exclamation** | "Idea added!", "Reflection saved!", "Your vision song is ready!" |
| Toast on failure | **Present-tense, no exclamation** | "Failed to save vision", "Failed to generate song" |
| Loading copy | **Gerund + ellipsis** | "Creating your song...", "Generating...", "Enhancing with AI..." |
| "X for Y" vs "X to Y" | **"for"** when X serves Y; **"to"** when X transitions into Y | "A button for saving" · "A goal to a mission" — don't mix |
| Mic button aria-label | **Verb-toggle pair** | `isListening ? "Stop recording" : "Start recording"` |

If a doc section references UI copy that doesn't match these patterns, either the doc is wrong or the UI is — resolve it before shipping.

## Required sections

Produce a `README.md` that links to each of the following. Every section must pass both lenses.

### 1. README.md
- At-a-glance table: Area · Routes · Purpose (1 line each)
- Navigation guide: "If you want to… read this" → each sub-file
- Quick reference: absolute file paths to pages, components, hooks, edge functions, tables
- If UI label ≠ internal name: include a **Naming** callout at the top (see section 2)

### 2. Naming (folded into README when relevant)

**REQUIRED whenever the user-facing label differs from the internal name.** Examples from Vision:
- UI label: "Vision" · Table: `vision_north_star` · Hook: `useNorthStar` · Voice tool: `set_north_star`

The Naming section must:
- State the split explicitly: "In the UI call it X; in the code call it Y"
- List every internal layer that stays Y (table, hook, voice tool, LLM prompt, code comments)
- Include a grep cheat sheet of which strings a rename should and shouldn't touch
- Explain the decision (usually: UI copy is for users, internal names have API/DB coupling that would cost more to break than the consistency is worth)

### 3. architecture.md
- ASCII data-flow diagram from page → hook → table → edge function
- Query-key registry: every `queryKey` used by the module, with its invalidation triggers
- Voice/AI stack table: which hook (Deepgram/Web-Speech/Deepgram-inline) serves which surface, with *Why* where a non-standard choice appears
- Module boundaries: what's in-scope, what this module *relies on* from other modules

### 4. components.md
One contract per component:
- Props (exact types, copied from source — not paraphrased)
- What the component owns (local state) vs what it lifts (callbacks)
- Reuse notes (can this be lifted to another page without changes?)
- Any violations or load-bearing quirks documented inline

### 5. hooks-and-data.md
- Every hook: query key, return shape, mutations exposed, debounce/stale config
- Every table: columns, RLS policies (or a note that it relies on RLS-only filtering)
- Type-file status (if `supabase gen types` hasn't been run recently, flag the `(supabase as any)` casts that result)

### 6. edge-functions.md
For each function:
- Verified secret names (grep the source — do **not** copy from old docs, which is how `GEMINI_API_KEY` vs `GOOGLE_AI_API_KEY` drift creeps in)
- Rate limits (in-memory or DB-backed — state which)
- Spend caps (`checkAndRecordSpend` provider + daily $ limit)
- App Check enforcement mode (`enforce: true | false`)
- Prompt sanitization (`MAX_PROMPT_LEN`, `sanitizeUntrusted`)
- Input/output shape
- Known failure modes

### 7. behavior-and-rules.md
- Numbered **invariants** (each with *Why:* — what breaks without this)
- **Do-not-touch list** (each with *Why:*, so future-you can judge edge cases)
- Copy conventions (reference the verb-pattern table above; list any module-specific copy)
- Voice-first rules: every text input surfaced; ✅ if mic, ❌ if gap, ⚠️ if non-standard
- Accessibility rules: aria-labels, dialog titles, focus, keyboard

### 8. future.md
- Known gaps, priority-tiered (High / Medium / Low)
- Extension points (specific: "add string to `item_type`", "edit `DEFAULT_CATEGORIES` in `useCategories.ts`")
- Deprecated patterns (with a "do not replicate in new code" note)
- Decisions intentionally deferred (with *Why:* — this is someone's reasoned choice, not an oversight)
- Roadmap signals
- Monitoring / alerting TODOs
- **"If you're adding a major feature here" checklist** — enumerates which of these 8 files to update
- **Voice Coverage Matrix** — produced via the `voice-coverage-audit` skill (see that skill for format)

### Optional sub-topic files
If a single topic bloats one of the core files, split it out: `ai-coaches.md`, `<feature>-song.md`, etc. The README's navigation guide lists them alongside the core 8.

## Authoring workflow

1. **Read the source first.** Read every file you'll reference before writing about it. Resist writing from memory or prior docs.
2. **Write README.md last.** Navigation and quick reference are easier to assemble once the sub-files exist.
3. **Every code reference gets verified by grep.** If you wrote "`useVision` returns `{ northStar, goals }`", grep `useVision.ts` and confirm. If the return shape differs, the doc is wrong, not the code.
4. **Apply both lenses to each section before marking it done.** Treat lens failures as blocking.
5. **Capture all Naming splits proactively.** Search the repo for the user-facing term — if it diverges from the internal name even once, the Naming section is required.
6. **Run the Voice Coverage Matrix as part of future.md.** Don't defer it — the matrix often reveals documentation gaps in the other sections (a missing component, an undocumented edge function).

## Maintenance contract (docs stay synced on every change)

This skill applies to BOTH initial builds AND ongoing edits. Every time you touch a file under `src/` or `supabase/` that maps to a documented module, you re-apply the relevant subset of this skill:

- **New component / hook / edge function** → add its contract to the matching sub-file; update README quick-reference; add a row to the Voice Coverage Matrix if it's user-reachable.
- **Renamed symbol** → grep docs for the old name; update every hit; add/update a Naming-section entry if the UI label changed.
- **Bug fix** → if the fix changes documented behavior (an invariant, a rate limit, a failure mode), update the corresponding invariant/failure-mode lines and revise the relevant known-gap entry in `future.md`.
- **Removal** → delete the contract from its sub-file; remove the matrix row (don't leave it as a Gap); drop any "extension points" that relied on it; move it to "Deprecated patterns" only if the pattern must not be reused.
- **Changed prop / return shape / secret name / rate limit** → update the exact line in the sub-file; these are the highest-drift fields and the most common source of fictitious-export bugs.

A code change without the matching doc update counts as **incomplete** per `CLAUDE.md` workflow rule #7.

## Output gate (module isn't "documented" until all pass)

- [ ] Both lenses pass on every section
- [ ] Every code reference resolves to a grepable symbol
- [ ] Naming section exists wherever UI label ≠ internal name
- [ ] Copy conventions follow the verb-pattern table
- [ ] future.md includes a Voice Coverage Matrix section
- [ ] README navigation links every sub-file
- [ ] "If you're adding a major feature here" checklist enumerates all 8 files (or the correct subset if the module is flat)

## Reference

- **Proven exemplar:** `docs/feature-modules/vision/` — the Vision module retrofit (BLOCK → green) is the reference implementation of this skill. When in doubt, compare your draft against a Vision file with the same purpose.
- **Complementary skill:** `voice-coverage-audit` — the matrix section of future.md is produced by that skill.
