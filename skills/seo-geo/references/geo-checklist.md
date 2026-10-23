# GEO / AEO checklist (getting named and cited in AI answers)

Recommendations are hypotheses grounded in evidence, not promises of citations. Verify each item on the live site; report what is blocked and what that rule actually controls.

## 1. AI-bot access (robots.txt)
Fetch `/robots.txt` on the exact host (www and bare domain separately). Know what each rule controls:

| Bot | Operator | Controls | Blocking it means |
|---|---|---|---|
| OAI-SearchBot | OpenAI | ChatGPT search index | Not surfaced in ChatGPT search: a real barrier |
| ChatGPT-User | OpenAI | Live fetches when a user asks | Cannot read your page on request |
| GPTBot | OpenAI | Model training crawl | Training opt-out; does not stop live answers |
| ClaudeBot | Anthropic | Training crawl | Training opt-out |
| Claude-SearchBot | Anthropic | Claude search results | Not surfaced in Claude search |
| PerplexityBot | Perplexity | Perplexity index | Not cited by Perplexity |
| Google-Extended | Google | Gemini training/grounding use | Opt-out of Gemini use; does not affect Google Search ranking |
| Applebot-Extended | Apple | Apple AI training use | Training opt-out |
| Bingbot | Microsoft | Bing index (feeds Copilot and others) | Loses Bing and downstream AI surfaces |

Default for visibility: allow OAI-SearchBot, ChatGPT-User, Claude-SearchBot, PerplexityBot, Bingbot. Training bots (GPTBot, ClaudeBot, Google-Extended, Applebot-Extended) are a business choice: ask the founder, default allow for brand visibility unless told otherwise. Never blanket `Disallow: /` for `User-agent: *` by accident. Also check CDN/WAF bot challenges that block these agents even when robots.txt allows them (the page must be reachable without login or JS-only rendering).

## 2. llms.txt
Optional convention, not a ranking factor; no major engine has confirmed it uses it. Cheap to add at `/llms.txt`: site name, one-line summary, links to key pages with one-line descriptions (pricing, services, about, FAQ). Say "unconfirmed benefit" if you recommend it.

## 3. Answer-first pages
The first 2-3 sentences of every page answer its main question directly. Specific facts, prices, comparisons, examples beat adjectives. Put a short FAQ block on money pages, with real buyer questions (see Big 5 in the playbook).

## 4. Entity and schema
JSON-LD that matches visible content: Organization (name, url, logo, sameAs), LocalBusiness/Service (address, area served, price range), FAQPage, Person (author), Product/Offer where real. Consistent name/address/phone across site, Google Business Profile and directories. Validate before shipping. Never mark up reviews or ratings that are not on the page and real.

## 5. Plain-text facts
Business name, service, location, pricing, hours, proof in plain HTML text (not only in images, sliders, PDFs or JS-rendered widgets). Rendered-vs-raw HTML: check what a non-JS crawler sees.

## 6. Off-platform citations
AI answers lean on third-party pages: "best X" list articles, review sites, directories, Reddit/forum threads, comparison pages, Wikipedia-style references. For each gap prompt, find which pages get cited instead of you, then get listed or answered there (see `backlink-playbook.md`). Community threads only where rules allow; no astroturfing.

## 7. Measure honestly
- Real: DataForSEO AI-assistant mention checks, tracked answers with dates, GSC. Cite run date, engines, market, sample size.
- The in-product AI Visibility Tracker is a "Simulated estimate".
- Small prompt samples (<10) are directions, not conclusions. Never convert prompt counts to traffic or revenue.
- Fresh IndexNow pings help Bing-fed surfaces only; Google ignores IndexNow.
