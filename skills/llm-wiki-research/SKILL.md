---
name: llm-wiki-research
description: Research sprints, competitive deep dives, and auto-enrichment of stub wiki pages. Delegates web fetching to worker-source-fetcher. Files all findings back into the wiki.
when_to_use: Use for "research [topic]", "deep dive on [topic/company]", "auto-research", "enrich [entity]", "find more about [X]", "what do we know vs what's public about [X]", "competitive research on [company]", "research sprint". Does not handle routine ingest — use core llm-wiki-pm for that.
allowed-tools: Read Grep Write Bash WebFetch WebSearch
---

# LLM Wiki Research

Sub-skill of llm-wiki-pm. Handles research sprints, competitive deep dives, and auto-enrichment of stub entities. Delegates all URL fetching to `worker-source-fetcher` so privacy filtering and raw/ logging happen correctly.

**WebFetch note:** `WebFetch` is listed in allowed-tools for quick page previews (e.g., confirming a URL before delegation). For source capture (saving to raw/), always delegate to `worker-source-fetcher`. Never call WebFetch directly for source saving — privacy filtering and raw/ logging won't happen.

## Orient First

Orient per AGENTS.md before any writes:

1. Read `$WIKI/SCHEMA.md`
2. Read `$WIKI/index.md`
3. Read last 20-30 lines of `$WIKI/log.md`
4. Read `$WIKI/overview.md`

Research sprints may create many pages. Get user confirmation before creating 5+ pages.

## Wiki Path Resolution

```bash
WIKI=$(cat .wiki-path 2>/dev/null | tr -d '[:space:]')
WIKI=${WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}
```

## Worker Delegation

This skill uses `worker-source-fetcher` for all URL fetching. Never call WebFetch directly for source capture — always invoke the worker:

> "Use worker-source-fetcher to fetch [URL]"

This ensures privacy filtering and raw/ logging happen correctly. The worker returns:
`"OK: saved to raw/<subdir>/<slug>.md"` — use that path for synthesis.

---

## Operation 1: Research Sprint

**Trigger:** "research sprint on [topic]", "deep research on [topic]"

**① Define scope**

Confirm with user:
- What is the topic / question to answer?
- Target depth: surface / standard / deep
- Time budget (number of sources)

**② Wiki-first**

```bash
grep -r "<topic>" $WIKI --include="*.md" -l
```

Read all relevant pages. Surface: "Wiki has N relevant pages. Here's what we already know: [...]. Gaps: [...]."

**③ Research plan**

Present 3-5 specific sources to fetch — name each, why it's relevant, what question it answers. Typical: analyst reports, company pages, recent press, whitepapers, industry forums. Get user confirmation before fetching.

**④ Delegate fetching**

For each confirmed source: "Use worker-source-fetcher to fetch [URL]"

If a fetch fails (404, paywall, timeout), note it and continue. Collect all raw/ paths before writing.

**⑤ Synthesize**

Read all fetched raw files. Extract entities, claims, data points. Cross-reference against existing wiki pages. Distinguish:
- Confirmed (claim now in 2+ independent sources)
- New (single source, not yet corroborated)
- Contradicts wiki (surface the conflict explicitly)

**⑥ File findings**

Create/update wiki pages per core ingest discipline: inline provenance, coverage markers, confidence levels, min 2 outbound wikilinks, backlink audit.

Produce a synthesis page at `queries/research-<topic>-<YYYY-MM-DD>/README.md`:

```markdown
---
title: "Research Sprint: <Topic>"
created: YYYY-MM-DD
type: query
tags: [<relevant tags>]
sources: [<raw slugs fetched>]
---

## Scope
Question: [...]  Depth: [...]  Sources: N

## What We Knew
[Pre-sprint wiki state summary]

## What We Learned
[Net-new findings with inline citations]

## Confirmations
[Claims now corroborated by 2+ sources]

## Contradictions
[Conflicts with existing wiki pages — cite both sides]

## Still Unknown
[Gaps that fetching didn't resolve]

## Pages Created/Updated
- [[slug]]: [brief note]
```

**⑦ Surface delta**

What did we learn that we didn't know? What did it confirm? What's still unknown? Any contradictions with the wiki?

**⑧ Log**

```
## [YYYY-MM-DD] research-sprint | topic: <X> | sources: N | pages created/updated: N
```

---

## Operation 2: Competitive Deep Dive

**Trigger:** "competitive deep dive on [company]", "full competitive analysis of [company]"

**① Read existing coverage**

Read `$WIKI/entities/<company>.md` and related `comparisons/` pages. If `coverage: comprehensive`, ask: "Already marked comprehensive — update pass or fresh deep dive?"

**② Research plan**

Standard source set:
- Official website (product, pricing, about)
- Recent press (last 6-12 months)
- Job postings (signals: what they're building)
- Pricing page
- G2 / Gartner / Capterra reviews
- Analyst mentions (MQ, Wave, IDC)
- Crunchbase / LinkedIn (funding, headcount)

Get user confirmation before fetching.

**③ Delegate fetching**

"Use worker-source-fetcher to fetch [URL]" for each confirmed source.

**④ Update entity page**

Apply diff discipline (core §4): snapshot to `_archive/<company>-<date>.md` first, show diff before writing, update inline provenance on revised facts, sweep stale variants.

**⑤ Update comparison pages**

Update existing comparisons/ pages. Offer to create a new comparison page if the deep dive reveals strong differentiation.

**⑥ Flag confidence by source**

| Source type | Confidence |
|---|---|
| Official website, press releases | `verified` |
| Analyst reports, G2 reviews | `likely` |
| Forums, social media, unofficial blogs | `rumor` |

**⑦ Log**

```
## [YYYY-MM-DD] competitive-deep-dive | entity: <company> | sources: N | pages updated: N
```

---

## Operation 3: Auto-Research (Stub Enrichment)

**Trigger:** "auto-research [entity]", "enrich [entity]", "fill in [entity] page"

For entity pages with `coverage: stub`. Fast enrichment pass.

**① Read the stub** — what do we already know? What's in `gaps:`?

**② Search**

```
WebSearch: "[entity name]" recent news
WebSearch: "[entity name]" official website
WebSearch: "[entity name]" [primary domain, e.g. pricing / funding / product]
```

**③ Extract** — description, key facts, relationships to other wiki entities, recent events.

**④ Update stub page** with inline provenance `[source: url, date]`. Bump `coverage:` stub → partial if meaningful data found. Update `gaps:` and `sources:` frontmatter. Bump `updated:`.

Do NOT fabricate. If search returns nothing useful, say so. Leave `coverage: stub`.

**⑤ Log**

```
## [YYYY-MM-DD] auto-research | entity: <X> | coverage: stub→partial | sources: N
# or if nothing found:
## [YYYY-MM-DD] auto-research | entity: <X> | no public data found | coverage: stub (unchanged)
```

---

## Operation 4: Gap Research

**Trigger:** "research our gaps", "fill coverage gaps", "research stubs"

**① Scan for stubs**

```bash
grep -r "coverage: stub" $WIKI --include="*.md" -l
grep -rL "coverage:" $WIKI/entities $WIKI/concepts --include="*.md"
```

**② Present list** — ask user which to prioritize.

**③ Run Operation 3** on each selected stub in sequence. Surface result before moving to next: "Enriched [[entity]] — stub → partial. Found: [key facts]. Continue?"

**④ Report**

```
Gap research complete:
- N pages enriched (stub → partial)
- N pages still stub (insufficient public data)
- N pages skipped
```

**⑤ Log**

```
## [YYYY-MM-DD] gap-research | stubs scanned: N | enriched: N | still-stub: N
```

---

## Pitfalls

- **Orient first**: before any writes. Research sprints may touch many pages.
- **Delegate fetching**: always use `worker-source-fetcher` — never WebFetch directly for source saving.
- **Confirm before mass creates**: 5+ pages → user confirmation first.
- **Inline provenance**: every non-obvious claim needs `[source: slug, location]`.
- **Coverage markers**: bump `coverage:` after meaningful enrichment.
- **Confidence discipline**: verified / likely / rumor — label accordingly.
- **No fabrication**: if search returns nothing, say so.
- **Snapshot before destructive updates**: `_archive/<slug>-<date>.md` before deep dive overwrites.
- **Dedup**: grep before creating. Confirm update vs create.
- **Privacy**: customer names, deal sizes, 1:1 content → `private: true`.
- **Synthesis page**: research sprints always produce `queries/research-<topic>-<date>/README.md`.
