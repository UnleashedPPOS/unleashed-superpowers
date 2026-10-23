# Reports and where things live

Verify with `ls scripts/` in `~/Developer/unleashed-funnel-factory` (GitHub UnleashedPPOS/unleashed-funnel-factory); names may have moved. The engine landed on branch `feat/seo-geo-site-auditor`; check whether its PR has merged before telling the founder it is live.

## Engine layout (funnel factory)
| Organ | Path |
|---|---|
| Site auditor | `src/lib/seo-geo/audit/site/**`, CLI `scripts/seo-audit.ts` |
| Provider seams (DataForSEO, Google Search Console, Bing Webmaster; env-gated, fail-closed, spend-capped) | `src/lib/seo-geo/providers/**` |
| IndexNow | `src/lib/seo-geo/indexnow/**`, CLI `scripts/indexnow.ts` |
| Playbook prompt builders | `src/lib/seo-geo/playbook/**`, CLI `scripts/seo-playbook.ts` |
| Weekly job | `scripts/seo-weekly.ts` |
| Backlink packs | `docs/backlinks/{unleashed-os,courtwise}.md` |

## Outputs
- Per run: `reports/seo/<site>/<YYYY-MM-DD>/` (JSON + self-contained HTML RAG scorecard, Top-10 issue table, "couldn't check" section).
- Weekly: Monday 07:00 Europe/London via systemd timer on `netcup-render`; rows in table `seo.site_audits`, files in `reports/seo/<site>/<date>/`.
- Console: https://factory.unleashed.vision/console/discovery, "Sites" tab.
- Research memory: user memory `research-seo-geo-playbook`; unleashed-memory wiki page `wiki/investigations/seo-geo-playbook.md` with `raw/research/seo-geo-playbook/report.html`.

## Providers (via vault only)
Run `vault list` first. Example: `vault run --keys DATAFORSEO_LOGIN,DATAFORSEO_PASSWORD -- npx tsx scripts/seo-audit.ts <origin>`. Keys: `DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`; `GSC_SERVICE_ACCOUNT_JSON` or `GSC_OAUTH_CLIENT_ID`/`GSC_OAUTH_CLIENT_SECRET`/`GSC_OAUTH_REFRESH_TOKEN`; `BING_WEBMASTER_API_KEY`. Absent = report "not connected". If a key is not in the vault, hand the founder deep links (credential-handoff rule), then wire it.

## Who owns which site's code
| Site | Code |
|---|---|
| unleashed.vision static SEO pages | os-mobile repo (UnleashedPPOS/unleashed-os-mobile) |
| courtwise.org | `~/Developer/courtwise-site` |
| Anything else | check which repo serves the origin before editing; the factory engine audits and reports, it never edits a site |

Fixes found by an audit go into the owning repo as a PR.
