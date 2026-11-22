---
name: council
description: "The saved roster of every council the founder has run, with a decisions log. Use when the founder says council, the council, get the council on this, AI-native council, the lawyers, 4 lawyers, lawyer panel, UI council, cloud QA council, or persona or lens review. One Opus agent plays all seats by default. SKIP for a single reviewer, /ship-check, and the Knowledge Hub Council Mode feature."
---

# Council (saved roster + decisions log)

**Announce at start:** "I'm using the council skill: <panel name>, <one agent | one agent per seat>."

## Thesis
Each chat used to invent its council, so seats drifted. This skill is the one roster. Pick a named panel below, use its seats exactly, then log the verdict in `decisions.md` (same folder). Never invent a seat; add it to the panel here first. Researched 22 Nov 2026 from chats and memory dated 15 Oct to 22 Nov.

## When this fires
The founder names a council or panel, asks for several viewpoints, or a legal, pricing, pay, UI or AI-design call needs a second opinion.

## How to run
1. **Default: ONE Opus agent plays every seat** of the chosen panel (`opus-thinker`, `model: opus`, never Fable). Each seat answers in 2 to 4 lines: position, what it checks, veto yes/no. Then a **Dissent** block, separate from the verdict. Under 300 words back to the parent.
2. **One agent per seat ONLY for legal, money or irreversible calls** (agreements, privacy, terms, pay and commission, pricing sent to customers, deletes, sends, deploys that cannot be undone). Each seat is its own Opus sub-agent, runs read-only and returns a graded finding list.
3. **Any legal change** (agreement, policy, privacy, terms, recording, minors, data): run the **4-lawyer panel** below, one agent per lawyer, BEFORE merge or deploy. This is the rule `feedback-legal-changes-need-lawyer-panel` points to.
4. State the question in one line, give each seat the same facts, no leading. A seat may veto only inside its own "vetoes" list.
5. Log the verdict, dissent and link in `decisions.md`. Before a new council on an old question, read its log row and only revisit what changed.
6. Output: verdict first, dissent second, then the build. No "X for Y" brand lines (drop that ask from any prompt). Founder wording stays simple; no jargon.

## Panels

### 1. Business council (Council of 10)
Business lenses for offer, outreach, pricing and positioning calls. Seats are readings of each person's public views, a second opinion, not their words. Only Hormozi and Gary Vee exist as real data in the Brain (`rag.chunks` by `clone_slug`); say so when quoting.
| Seat | Job / checks | Vetoes |
|---|---|---|
| Hormozi | Offer strength, value equation, guarantees, price vs outcome | Weak or unclear offer |
| Musk | First-principles cost, delete steps, speed | Needless complexity |
| Jobs | Simplicity, taste, one clear thing | Cluttered or confusing product |
| Bezos | Customer obsession, working backwards, one-way vs two-way doors | Irreversible move without a customer need |
| Naval | Leverage, specific knowledge, long-term compounding | Work that does not scale |
| Blakely | Story, bootstrapping, scrappy first sale | Over-building before a sale |
| Gary Vee | Distribution, attention, volume of real outreach | No plan to reach people |
| Thiel | Monopoly angle, wedge, contrarian truth | Me-too positioning |
| MrBeast | Hook, retention, make the viewer or user feel it | Boring first 5 seconds |
| Brunson | Funnel, ladder, one next step, story-led sell | Missing next rung |
Used for: ecosystem (7 Nov), partner pay (7 Nov), landing and 349 drafts (6 Nov), avatar hunt (2 Nov), outreach rewrite and demo-offer rounds (8 to 9 Nov). Sources: memory `research-ecosystem-council`, `research-partner-pay-council`, `research-council-landing-drafts`, `research-avatar-hunt`; session jsonl `ce40b8ab`.
**Pricing sub-panel (add-on, 8 Nov, proposed not confirmed adopted):** Patrick Campbell (tiers), Nathan Barry (creator and coach pricing), Ramit Sethi (price feel), plus a working PT with 15 clients who would never pay. Add only for pricing questions.

### 2. Creator council (pricing and partner pay)
18 Brain clones as recorded 16 Oct (count not re-checked), plus a platform economist and an App Store / payments engineer, up to 3 rounds. Used for coach monetisation, partner commission, buyout multiple, setter and rep pay, fair-use overage, value gauges, multi-location pricing, setup-fee timing, recording rep meetings, the pricing ladder. Seats: each clone answers from its Brain passages (state passage count); Jay Shetty and Vinh Giang check money terms are clear and in writing up front, no golden handcuffs; Noah Kagan checks onboarding clarity as the retention lever; economist checks unit economics and platform fees; payments engineer checks Apple/Play cut, VAT, refunds, payout timing. Vetoes: unclear terms (Shetty, Giang), anything that breaks the maths (economist), anything the stores or Stripe cannot do (engineer). Founder decision overrides council caps. Sources: memory `research-partner-pay-council`, `research-rep-pay-flat`, `research-coach-community-monetisation`, `research-value-gauges`; unleashed-memory `wiki/investigations/`. Merge note: this absorbs the 16 Oct "single-AI council of 4 fictional experts" and "plans council" from the pricing bible, which were the same job with fewer seats.

### 3. 4-lawyer panel (hostile lawyers, LEGAL: one agent per lawyer, Opus, read-only)
Each lawyer grades findings Blocker / Important / Nit and gives exact replacement wording. Rounds R1 to R4 live in `findings-register.ts` (`/admin/legal-research`, unleashed-affiliate). Inputs: a diff plus the full files. Never merge or deploy legal text before all four report.
| Seat | Job / checks | Vetoes |
|---|---|---|
| L1 Agency law | Commercial Agents Regs 1993 (reg 3 duties, reg 4 information, regs 6 to 12 commission, reg 13 written terms, reg 15 notice, regs 17 to 18 indemnity, reg 19 no derogation); unilateral commission variation | Terms that breach the Regs |
| L2 Fairness, status, minors | CRA 2015 Part 2, UCTA 1977, Interfoto; worker status (Uber v Aslam, Pimlico Plumbers, Autoclenz, IR35); under-18 enforceability and guardian consent; children's data (UK GDPR, AADC) | Unfair or unincorporated terms, worker-status risk, minors without consent |
| L3 Drafting consistency | Dangling cross-refs, undefined terms, transition rules, version/hash pipeline, code matches text | Text and code that disagree |
| L4 Claimant's counsel | Strongest claim for a disgruntled rep: Wandsworth v D'Silva, Bateman v Asda, Braganza, Cavendish v Makdessi, estoppel from sales copy, ASA/CMA/ICO; then fixes that defeat each claim | Any claim left undefended |
Variants (same four, swap the lens set): consumer law (CRA, DMCC Act 2024, CCRs); UK GDPR / PECR (20 Nov); ASA/CAP and platform ad rules (17 Nov); DPIA. Sources: unleashed-affiliate `findings-register.ts`; side-session-notes `lawyer-panel-*`; `~/Developer/lawyer-pack-2026-10-27`.

### 4. AI-native council of 15
Council of 10 plus five AI-native seats, for AI product design and audits (16 Nov; 72-item ledger in `project-ai-native-audit-ledger`). Apply to Chief and the events radar when asked.
| Seat | Job / checks | Vetoes |
|---|---|---|
| Karpathy | Software 3.0, context as RAM, autonomy slider | Autonomy with no human override |
| Simon Willison | Lethal trifecta, Rule of Two | Private data + untrusted input + exfil path |
| Boris Cherny | Agent verifies its own work, short shared CLAUDE.md | Unverified agent output |
| Hamel Husain | Look at the data, error analysis, evals | Shipping with no evals |
| Harrison Chase | Context engineering, memory, traces | No traces, no memory design |
Verdict 16 Nov: AI had tools but no owner context and no evals; fix = Owner Context + look-at-data + corrections-as-data. Founder note: keep seat wording plain, no jargon. Memory/evals work needs the highest bar (`feedback-ai-memory-evals-highest-bar`).

### 5. UI and QA council (settings, newcomer, cloud QA)
Judges screens and video frames; most weight on settings, profile and the paywall. Rule: simpler = staged, not removed; every option stays one tap away.
| Seat | Job / checks | Vetoes |
|---|---|---|
| Newcomer | First-time user: do I know what to tap | Confusing first screen |
| ADHD user | Overload, too many choices, clear next step | Busy or intimidating screen |
| Non-technical user | Plain words, no jargon | Jargon labels |
| Payment sceptic | Is the trial free, is "continue free" visible, trust | Unclear charge |
| Coach | A coach setting this up for clients | Hidden client controls |
| Designer | Elegance, consistency, spacing, empty states | Cut-off text, uneven tiles |
| Senior engineer (QA add-on) | Performance, scroll smoothness, correctness | Jank, broken flow |
| QA lead (QA add-on) | Everything intended happens, edge states | Untested path |
Sources: `CLOUD-QA-BRIEF.md` §3 (unleashed-memory `_mirrored/unleashedos/docs/qa/`), session jsonl `49eb4ea0` (16 and 21 Nov). Merged: the settings council and cloud QA council share four seats; Coach and Designer are as the founder described them (22 Nov), their exact wording was not recorded. Signal consolidation (10 Nov, jsonl `016b74d8`) used three sonnet-builder design seats (architecture and UX, member simplicity, a third lens left as a placeholder): fold into this panel's Newcomer/ADHD/Designer seats.

### 6. Studio and Clips audit council
Three read-only Opus seats (20 Nov, jsonl `3ea4c28f`): **Functionality** (flow correctness, does upload work); **Usability / first look / elegance** (zero state, clutter, UI); **Output quality + Unleashed Studio web** (what the render produces). Vetoes: a flow that silently does nothing; a list that buries the main action; poor output.

### 7. App-description persona council
Personas who judge how Unleashed OS is described (15 to 16 Nov, jsonl `b7ba35cf`, PR #868): five founders who have raised money and built consumer apps; a 22-year-old with ADHD who has never heard of it; an ordinary 30-year-old; a men's/life coach; a gym owner; a charity or shelter worker; a grant reviewer. Each says what they think it is, what makes them download, use or fund it, and what confuses them. Gate: the Slop Monster check must score 5. Approved wording lives in memory `reference-unleashed-positioning`; no "X for Y" lines.

### 8. Lighthouse and ops council
Systems and logins calls (22 Nov, jsonl `840ac9ce`): **AI-native systems architect** (one source of truth, build on existing), **Reliability / ops engineer** (alerts, failure modes), **Facebook/Meta account-safety specialist** (no logins from servers, avoid flags), **ADHD solo-founder advocate** (fewest steps), **CFO** (cost, Lighthouse session only). One agent, under 300 words: per-question recommendation, dissent, build.

### 9. Founder-story and video council
For scripts and bios (18 Nov, jsonl `fa8d1ecb`; brief `scratchpad/video/brief.md`). Seats were "the council" on the 60 s, 3 min and 5 min scripts: use the Business council plus story coaches. Exact roster not recorded. Facts: memory `user-founder-story`; pick facts that position him, first person, never invented testimonials.

## Merges and not-councils
- Merged: pricing bible's "single-AI council of 4" and "plans council" into panel 2; `/start` pages, Facebook groups post and demo-offer reviews into panel 1; settings and cloud QA into panel 5; Signal design seats into panel 5.
- Not councils here: Money Printer ten-persona audit and Persona League (trading), logo redesign "become the council" (one-off, seats not recorded), pitch-deck five founder personas (use panel 7's founders), Knowledge Hub Council Mode (product feature, `council-mode-is-scaffolding-not-shipped`).

## Standing rules from verdicts
A verdict that should hold in every chat becomes a line here (and a check where one can be written), not only a feature (founder 22 Nov 2026: "some of these aspects should be just built into skills… some rule"). The always-loaded rule `working-style.md` points here.
1. **One next move first.** Founder-facing output (pages, the Chief's Home, plans) leads with one next move, never a pile and never a count of open items. Source: Chief council 22 Nov (Jobs veto).
2. **Hand-offs come ready.** Every needs-you item carries the exact link, the steps, the paste-back, a ready starter and a phone or laptop tag, and closes only when checked. Lives in `cloud-kit/rules/user-handoffs.md` and skill `founder-handoffs`.
3. **Heads-up opens every plan and brief.** Risks, spend and decisions taken come before the steps.
4. **Saved the same turn.** Anything published or decided is saved to unleashed-memory in the turn it happens (rule `research-memory`).
5. **Count what was done, no guilt words.** User-facing copy never shows overdue counts, missed streaks or "you haven't". Rest is logged as a choice.
6. **Real people first.** A growth or launch plan starts with a contact with a real person (a call, a reply, a post), before any more software. Source: Thiel and Hormozi dissent, 22 Nov.
7. **Private messages, untrusted input and a way to send never meet in one agent turn.** Drafts are batched for a human yes; no inbox ingestion with a send path. Source: Willison veto, 22 Nov.
8. **Every Claude session reports to the Chief** (start, state, needs-you, end) through a hook once the chat register is live; until then the handoff file is the record.
9. **No member-facing switch-on for an AI feature without an eval on real data** (the Chief's carry needs its 50 real dictations). Source: Husain veto, 22 Nov.

## Integration
`/ship-check` stays the code gate; legal text also goes through panel 3 first. `red-team` falsifies claims; a council weighs choices. Memory `feedback-legal-changes-need-lawyer-panel` and `reference-council-roster-skill` point here.

## Red flags
| Thought | Reality |
|---|---|
| "I'll make up seats for this one" | Use a panel here or add the seat here first |
| "It's only a small policy edit" | Any legal text goes through panel 3 |
| "The council agreed, so ship" | Money and legal calls still need the founder's yes |
| "Skip the log" | No row in `decisions.md`, no council |
