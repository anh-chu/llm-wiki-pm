# Wiki Schema — PM

## Domain

Product management knowledge base. Scope:
- Competitive landscape (test automation, DevOps, AI dev tools)
- Customer relations (enterprise accounts, SE/sales insights)
- Strategy (TruePlatform, Kai/AI, migrations, pricing)
- Internal org (people, teams, decisions, OKRs)
- AI market intelligence (models, tools, vendors, trends)
- Roadmap and product health signals

Out of scope: code specifics (use Hindsight + code comments). Personal life.

## Conventions

- Filenames: lowercase, hyphens, no spaces. E.g. `tricentis.md`, `trueplatform-launch.md`
- Every wiki page starts with YAML frontmatter (below)
- `[[wikilinks]]` between pages, minimum 2 outbound per page
- Bump `updated:` date on any edit
- Every new page → add to `index.md` under correct section
- Every action → append to `log.md`
- No em-dashes. Natural human tone. No AI tells.

## Frontmatter

```yaml
---
title: Page Title
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: entity | concept | comparison | query | summary
tags: [from taxonomy below]
sources: [raw/articles/example.md, raw/transcripts/call-YYYY-MM-DD.md]
contradictions: []        # optional — pages with conflicting claims
supersedes: []            # optional — page slugs this page replaces
superseded_by: null       # optional — slug of the page that replaces this one
private: false            # optional — true = exclude from exports/shares
confidence: verified      # optional — verified | likely | rumor
---
```

## Tag Taxonomy

Every tag on a page must appear here. Add new tags here FIRST, then use.

### Entities
- `company` — external org (competitor, partner, customer)
- `product` — named product or SKU
- `person` — named individual (internal or external)
- `team` — org unit (sales, SE, data, eng)
- `model` — AI model (GPT-5, Claude, Llama, etc.)
- `vendor` — tool/platform provider

### Domains
- `competitive` — rival positioning, pricing, features
- `customer` — named account, segment, persona
- `strategy` — direction, positioning, bet
- `roadmap` — planned or shipped work
- `ai` — AI features, market, models
- `migration` — customer migration work
- `enterprise` — enterprise-specific
- `pricing` — pricing, packaging, monetization
- `gtm` — sales, marketing, SE enablement

### Meta
- `comparison` — side-by-side
- `timeline` — chronological synthesis
- `decision` — recorded decision + rationale
- `risk` — identified risk, mitigation
- `question` — open question to investigate
- `prediction` — forward-looking claim with date

### Katalon-specific
- `trueplatform` — TruePlatform (formerly TestOps)
- `studio` — Katalon Studio (not my scope but relevant)
- `kai` — Kai AI product
- `katalon-internal` — internal org/people

Rule: tag sprawl kills wikis. Max ~40 tags. Consolidate quarterly.

## Page Thresholds

- **Create** when entity/concept appears in 2+ sources OR is central to one source
- **Update** existing page for new info on covered ground
- **Don't create** for passing mentions, footnote name-drops, out-of-scope items
- **Split** when page > 200 lines — break by sub-topic with cross-links
- **Archive** when fully superseded — move to `_archive/`, remove from index

## Entity Pages

Fields:
- Overview (what it is, 1-2 paragraphs)
- Key facts (dates, numbers, positions)
- Relationships (`[[wikilinks]]` to related entities)
- Relevance to our work (why this matters for Katalon PM)
- Source references

## Concept Pages

Fields:
- Definition / framing
- Current state (what we know, when verified)
- Open questions
- Related concepts (`[[wikilinks]]`)
- Decisions or bets tied to this concept

## Comparison Pages

Fields:
- What is being compared, why
- Dimensions (table format)
- Verdict / synthesis
- Sources
- Implications for us

## Query Pages (filed answers)

Fields:
- Question
- Answer (synthesis)
- Pages drawn from
- Date asked
- Filed because: [reason it's worth keeping]

## Update Policy

Conflicting info:
1. Check dates — newer sources generally supersede
2. If genuinely contradictory, note both with dates + sources
3. Mark in frontmatter: `contradictions: [other-page]`
4. Flag in next lint for user review
5. Never silently overwrite

## Mass Updates

If an ingest or update touches 10+ pages, confirm scope with user before
writing. Show the list. Get sign-off.
## Supersession Policy

When a new page materially replaces an old one (not just revises it):

1. New page frontmatter: `supersedes: [old-slug]`
2. Old page frontmatter: `superseded_by: new-slug`
3. Don't delete the old page — keep for audit trail
4. Move old page to `_archive/` if fully replaced
5. Rewrite inbound `[[old-slug]]` links to `[[new-slug]]` (lint --auto-fix does this)
6. Log: `## [YYYY-MM-DD] supersede | old-slug → new-slug`

Revision (same page, new info) is NOT supersession — use Update flow instead.

## Privacy Policy

PM sources contain sensitive data: customer names, account IDs, deal sizes,
internal strategy, 1:1 content. Before ingesting:

1. Strip obvious PII (emails, phone numbers, customer employee names if not
   public) from raw source text if you're not comfortable with them in the wiki
2. Flag sensitive pages with `private: true` in frontmatter
3. Private pages stay in the wiki but are excluded from exports/shares
4. Customer names in competitive contexts: use internal codes
   (e.g. `customer-alpha`) if the page might ever leave your machine

Privacy filter checklist before every ingest:
- [ ] Any API keys, tokens, passwords in the source? → strip before saving to raw/
- [ ] Customer names tied to revenue/churn risk? → consider private: true
- [ ] Internal strategy that would harm if leaked? → private: true
- [ ] 1:1 content with named colleagues? → private: true

## Confidence Levels

Optional `confidence:` frontmatter field:

- `verified` — multiple independent sources, recently confirmed
- `likely` — single credible source, plausible
- `rumor` — single low-credibility source, unconfirmed, hearsay

Use sparingly — mostly for competitive intel and market claims where
source quality varies. Not needed for internal facts.
