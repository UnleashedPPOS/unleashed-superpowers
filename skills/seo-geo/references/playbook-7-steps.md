# The 7-step playbook (condensed, complete)

Source: "Optimise Your Website for AI Search & SEO with Claude" (https://www.youtube.com/watch?v=setxOzrPVkU), prompts supplied by the founder 2026-10-24. Data sources: Google Search Console + GA4, DataForSEO (volume, difficulty, SERP, competitors, AI-assistant mentions), web search/fetch, optional CMS connector. Paste-ready versions: `npx tsx scripts/seo-playbook.ts <origin> <step 2-7|all>`.

Principle: data beats opinion. Every recommendation tied to a real page and a real number. Never estimate a figure you could look up. Name the source and date range.

## Step 1: SEO project + custom instructions
Set up a standing project: you are the SEO advisor for the site. Read "About My Business" before every answer. Pull real numbers. Read the live page before recommending changes. Rank by impact vs effort. Define SEO terms in one sentence. Optimise for two readers: Google and AI assistants. Every recommendation ends with: what, where, how long, how I'll know it worked.

## Step 2: About My Business (persona: April Dunford, Obviously Awesome)
Fetch homepage, about, services, pricing, contact, case studies (from nav + sitemap). Extract: one-sentence what it does; who it serves; every product/service with price, format, inclusions; competitive alternatives; what is different (facts, not adjectives); proof; location/service area; how to buy/contact. Mark [MISSING] / [UNCLEAR] with the page, then numbered questions to clear them. Under one page; nothing invented.

## Step 3: Buyer-question gaps (persona: Marcus Sheridan, They Ask You Answer)
Big 5: cost, problems/risks, comparisons/alternatives, reviews/proof, best-of. Mark each answered / partly / not, with page. "AI read": what an assistant needs to recommend you for "best [service] in [location]" (clear service, location, pricing, proof, distinctive facts). Competitor read: top 3 ranking competitors and what they answer that you don't. Output table ranked by likelihood of costing a sale: Gap | Buyer question | Answered by (me/competitor/nobody) | Exact content to add | Page. Max 15 rows + 3 sentences on the biggest gap.

## Step 4: Full SEO + AI-search audit (persona: Aleyda Solis)
- Performance, last 3 months vs previous: clicks, impressions, CTR, avg position, organic sessions, conversions; top 20 queries/pages; pages losing clicks.
- Quick wins: queries at positions 5-20 with meaningful impressions; high-impression low-CTR pages.
- On-page/technical: every indexable page's title, meta, H1, word count, internal links in/out; robots.txt, sitemap, GSC indexing issues, broken links, orphan pages.
- GEO: do the first 2-3 sentences answer the page's main question; business name/service/location/price in plain text; FAQ content; structured data (Organization, LocalBusiness, Service, FAQPage, Person); author/about info; proof; robots.txt blocking GPTBot/ClaudeBot/PerplexityBot/Google-Extended; DataForSEO check whether AI assistants mention the business for the top 5 service queries and who they mention instead.
- Output: RAG scorecard (Performance, Quick wins, On-page, Technical, AI search) with one line of evidence each; Top 10 issues: Issue | Evidence | Impact | Effort | Fix; what could not be checked and why. No issue without evidence.
- Engine: `scripts/seo-audit.ts` covers the crawl-derivable parts; GSC/DataForSEO parts need those providers connected, else "not connected".

## Step 5: Strategy, money pages + topical authority (persona: Koray Tugberk Gubur)
Per money page: primary + 3-5 secondary keywords with volume/difficulty/intent (DataForSEO), current position (GSC), top 3 competitors and what they have. Missing money pages (comparison, alternatives, pricing, service-in-location) with real demand. Topical map: clusters by shared intent + SERP overlap; each = pillar + 4-8 supporting articles + the money page it links to; include questions people ask AI assistants. Score on business value, demand, difficulty vs site strength, already-ranking-nearby. 30-day plan, max 3 tasks/week. No data = "no data", never an estimate.

## Step 6: Implement Week 1 (persona: Rand Fishkin)
Per task: the paste-ready asset (title, meta, rewritten opening, FAQ block, JSON-LD, internal link text); click-by-click steps for the platform; how to check it worked and when; [CONFIRM] for anything unknown; dev-brief form if a developer makes the change.

## Step 7: Dashboard, refreshed every Monday 7am
Clicks, impressions, CTR, avg position, organic conversions (last 7d vs prev 7d vs 4 weeks ago); top 10 queries/pages; biggest movers; AI-assistant mentions; 30-day plan progress; "This week's 3 jobs". Alert at top if clicks/impressions/conversions fall >20% WoW with likely cause + evidence. Engine: `scripts/seo-weekly.ts` (Monday 07:00 Europe/London).

## Tips
Fix Step-2 gaps first (missing prices/location/proof hurt Google and AI answers at once). Never act on an unsourced number. One week at a time. Judge on trend, not day three.
