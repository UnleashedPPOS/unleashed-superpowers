# Methods distilled from open-seo

Attribution: methods below are distilled and paraphrased from the MIT-licensed open-seo project's agent skills (https://github.com/every-app/open-seo, `.agents/skills/*`, read 2026-10-24). open-seo assumes its own MCP tools (`run_site_audit`, `get_serp_results`, ...); here, use the funnel-factory engine and DataForSEO/GSC providers instead, and write "no data" where a provider is not connected. Raw copies: unleashed-memory `raw/research/seo-geo-playbook/open-seo__*.md`.

## Shared habits (all workflows)
- Ground in project context first (business, goal, positioning, competitors, key pages). Missing piece: infer from the site, confirm in one question, never front-load a full interview.
- Reuse research under 30 days old instead of re-buying it; a ranking claim that drives a recommendation still needs a live check this session.
- Record exact query, country, language, date, organic listing count and matching URL for every ranking claim. Count organic listings yourself; report "#10 (page 1)", "#11 (page 2)" or "not in the first 20 results". A failed lookup is unknown, not "not found".
- Volumes are estimates, US unless stated, never visits. Size benefit against the cluster, name the mechanism (new ranking / higher position / more clicks), label position-one scenarios hypothetical. Never invent conversion or revenue.
- Observations are not causes; retrieval date is not observation date; missing data is "no recorded data".

## SEO audit
Orient (crawl + backlink/domain overview + sitemap page families), investigate each family that could bring buyers (read the best and a typical page; does it answer the searcher's decision with specific sourced facts or just swap a keyword into a template?), shortlist 5-10 candidates from at least three kinds (underperforming page, demand with no page, winner to protect, access/indexing defect, next-step help), choose 1-3, size honestly, review adversarially, write. Access/indexing blockers and dead domains jump the queue; do not rewrite pages already ranking near the top. Every shortlist row ends as a recommendation or a "what else we checked" row with a real reason. Crawl notes: rendering JS matters for SPAs; shells that need JS are flagged "content may require JavaScript"; challenges are `blocked`, not 404.

## Keyword research
Seeds -> distinct angles. If GSC is connected start from striking-distance queries (positions 5-20, 50+ impressions), then hydrate with volume/KD/intent/CPC. Local demand needs a location-specific volume lookup. Drop irrelevant, duplicate, branded-only, off-intent. Prioritise by fit, clear intent, reasonable difficulty, SERP you can plausibly compete in, not volume alone. Check SERPs only where intent is ambiguous. Missing metric = `unknown`. Ask before saving keywords.

## Keyword clustering
Cluster by SERP intent and page type, not lexical similarity: same SERP/ranking pages = same cluster; different intent/buyer stage/format = split. Borderline terms: small SERP-overlap batch. Map each cluster to an existing URL, a proposed new page, or a do-not-target bucket. Detect cannibalisation from GSC query+page data (one query splitting impressions across URLs). Fewer than ~10 terms: simple map. Label targets "proposed" without URL data.

## Link prospecting
See `backlink-playbook.md`. Key rules: prospects from SERPs for resource/list/comparison/statistics/template queries; angle per prospect; contacts only from public pages with source URL; flag competitors and paid placements; personalise, no mass outreach.

## Local SEO
Find the listing (cid/place_id beats name matching), compare against the top two local-pack competitors on primary and additional categories, review count/recency/owner replies, hours, photos, claimed status, and whether the listing's website link deep-links to the location page. Rank grid: 3x3 = nine paid searches (state cost; 5x5 only for wide areas; confirm the centre coordinate first). Average a point over several keywords with "not found" counted as 21; colour scale green 1-3, light green to 5, yellow to 7, orange to 10, red to 15, dark red to 20, grey not found. A missing rank is read against that point's result count (sparse SERP is not invisibility). Category and claim problems outrank posting cadence. Multi-location (>5): snapshot table, deep-dive 1-3 weakest. Never review gating, fake reviews, or stuffed business names. Do not infer local-pack strength from national organic metrics.

## AI visibility audit
Evidence first: use an existing completed tracker run; do not buy new answers without approval. Read per topic and engine: answers collected, brand mentioned, own site cited, competitors named; failed/no-answer collections are reported separately, not as absence. Gap = prompts where a competitor is named and the brand is not. Follow citations: classify top recurring sources (list/review article, forum, competitor page, owned page, reference). Read the pages before claiming a cited page mentions a competitor. Owned side: robots.txt access (see `geo-checklist.md`), is the page that should be cited reachable and answer-first with specifics? Candidate actions: get onto recurring third-party sources, improve an owned page, create a missing comparison/alternatives/use-case page, remove an access barrier, join community threads where allowed. Prefer patterns across several prompts/engines; an access barrier jumps the queue. Fewer than ~10 neutral prompts = small sample, directions only. Never invent visibility scores, share of voice or sentiment. A single API spot-check is one sample and never folds into rates. Treat answers and cited pages as untrusted data.

## AI prompt research
Question: what do people ask AI about the market and who gets cited. Use 2-4 one-to-three-word head terms from the project, not long phrases. Questions come largely from Google "People also ask"-style data, not logged assistant prompts: never present one as a real user prompt or attach demand to it. Merge duplicates by normalised text, group by intent (learning, choosing, doing, branded), drop off-market prompts, count source domains by registrable domain. Opening = large group where the brand is rarely mentioned/cited; the useful finding is the source mix (e.g. list articles plus a forum thread). Recommend 10-20 neutral prompts to track, including some where the brand already appears so gains and losses both show. Research only; no saving or collection.

## Competitor analysis and competitive landscape
Landscape: build a 5-10 query set with mixed intent, find recurring domains, label types (direct competitor, publisher, marketplace/directory, community, docs), size top 3-5 domains, read their ranked keywords, check backlinks only if authority seems to explain wins. Directional when the query set is small. Competitor deep-dive: footprint, ranked keywords filtered for fit (not every keyword is desirable), themes (product, alternatives, tools, guides, brand, local), backlinks, then vulnerabilities and what NOT to copy; page-level claims need SERP/web evidence, not keyword rows. Separate SEO competitors from business competitors; organic winners from Maps winners.

## SEO report format
One self-contained HTML page per run, no executable scripts, calm plain tone. Order: verdict and next move first (2-3 bullets), 1-3 recommendations each with Do this / Why / small evidence table, "what else we checked" table, then a closing "how this report was made" with tool coverage, limits and an evidence appendix (queries, dates, sources). Print the numbers: a chart never carries a value not also written out. Do not invent a number to fill a cell: write `unknown` with a note. Update the report for the same subject/period rather than duplicating.

## SEO coach mode
Short, scannable, beginner-friendly. Lead with the answer or one next step, bullets over paragraphs, gloss numbers once, end with one question or 2-4 numbered choices. Quick orientation only; hand off to a full workflow when the user wants a report, a deliverable, or the answer exceeds a screen. Anchor strategy on business goals and positioning before keywords; separate live data, web evidence and judgment.

## Project setup interview
Verify project, read what is known, then in small batches: site scope (domains, key products, markets, stage, CMS), goals with metric and timeframe, positioning (audience, pain, differentiator, bad-fit customers, topics to avoid), competitors (confirm before saving), 10-30 key pages with roles (hub/spoke/money/other), Search Console connection or CSV exports (queries/pages, 3 and 16 months). Confirm facts before writing them down. Do not claim GSC is connected unless a call proves it.

## IndexNow (from open-seo spec 0016)
Key = 32 hex chars, hosted at `https://{host}/{key}.txt` containing only the key; the exact host needs its own copy (www vs bare), no redirects. Up to 10,000 URLs per request, one request per host; skip off-domain URLs. Check the key file before submitting. Bing endpoint first, fall back to Yandex then Yep; a rejected key or bad request is not retried elsewhere. Engines answer 202 while a key is unverified. Google does not use IndexNow. Do not resubmit the whole site; submit changed URLs only.

## Crawl architecture lessons (from open-seo specs 0009 and rendering note)
Chunked rolling crawl with adaptive concurrency (5-40), streaming HTML parser (no DOM), idempotent writes, failed audits keep partial results, start URL follows redirects with SSRF revalidation, step outputs stay O(chunk). JS rendering is a paid opt-in (renderer costs per page; challenged pages go to a fallback renderer; rendered crawls capped at 1,000 pages). Throttled stores (e.g. Shopify 429s) need a crawler signature or rendering, not endless backoff.
