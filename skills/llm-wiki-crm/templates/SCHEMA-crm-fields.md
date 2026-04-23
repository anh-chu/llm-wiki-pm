# SCHEMA-crm-fields — CRM Layer Patch

This file is NOT a standalone SCHEMA.md replacement. It is a patch reference.

Merge the fields and tags below into the relevant sections of your wiki's
existing `SCHEMA.md`. Do not overwrite your SCHEMA.md — append or insert
at the appropriate locations.

---

## Merge Instructions

1. Open your wiki's `SCHEMA.md`
2. Find the `## Frontmatter` section
3. Under `# Person entity pages only:`, add the person fields below
4. After the person fields block, add the company fields block under `# Company entity pages only:`
5. Find `## Tag Taxonomy` → `### Domains`, add the new tags
6. Save. Run lint to confirm no schema drift.

---

## Person Entity Frontmatter Additions

Add under `# Person entity pages only:` in your SCHEMA.md:

```yaml
# CRM fields — person entities (llm-wiki-crm):
relationship_tier: null     # strategic | active | watch | dormant
last_touchpoint: null       # YYYY-MM-DD — date of last meaningful contact
meeting_cadence: null       # daily | weekly | biweekly | monthly | quarterly | ad-hoc
next_meeting: null          # YYYY-MM-DD — optional, next scheduled touchpoint
influence_level: null       # high | medium | low — influence on decisions or roadmap
enriched_at: null           # YYYY-MM-DD — when auto-enrichment last ran
```

**Field notes:**
- `relationship_tier`: governs staleness thresholds. Strategic = flag at 14d, active = 30d, watch = 60d, dormant = informational.
- `last_touchpoint`: any meaningful contact — meeting, call, substantive async thread. Update after every touchpoint.
- `meeting_cadence`: intended cadence, not observed. Useful for flagging when actual gaps exceed the plan.
- `next_meeting`: clear after the meeting occurs; set `last_touchpoint` instead.
- `influence_level`: PM judgment — how much does this person shape product decisions, roadmap buy-in, or renewal?
- `enriched_at`: set automatically by auto-enrichment. Tracks when public profile data was last refreshed.

---

## Company Entity Frontmatter Additions

Add a `# Company entity pages only:` block in your SCHEMA.md frontmatter section:

```yaml
# CRM fields — company entities (llm-wiki-crm):
relationship_tier: null     # strategic | active | watch | dormant
account_health: null        # green | yellow | red
last_touchpoint: null       # YYYY-MM-DD — last meaningful contact with anyone at this account
key_asks: []                # list of feature/product asks from this account
arr_tier: null              # enterprise | mid-market | smb | prospect (no dollar figures)
enriched_at: null           # YYYY-MM-DD — when auto-enrichment last ran
```

**Field notes:**
- `relationship_tier`: same tiers as person entities. Reflects PM's overall relationship with the account.
- `account_health`: green = engaged and healthy, yellow = friction or risk signals, red = needs immediate attention.
- `last_touchpoint`: most recent contact with anyone at the account.
- `key_asks`: YAML list. Normalize phrasing across accounts so Feature Ask Tracker (§4) aggregates correctly. Example: `["SSO support", "audit logs", "better CI/CD integration"]`
- `arr_tier`: tier only — never record dollar figures, ARR amounts, or deal sizes.
- `enriched_at`: set by auto-enrichment. Tracks when company profile was last refreshed from public sources.

---

## Tag Taxonomy Additions

Add to `### Domains` in your SCHEMA.md tag taxonomy:

```
- `crm`, relationship management, touchpoint tracking, account health
- `account-health`, account status synthesis (green/yellow/red rollups)
- `feature-ask`, customer-requested features, aggregated ask tracking
- `touchpoint`, discrete interaction log or contact record
```

**Usage guidance:**
- Tag entity pages with `crm` when they carry CRM frontmatter fields.
- Tag filed account health dashboards (`queries/account-health-<date>.md`) with `account-health`.
- Tag filed feature ask reports (`queries/feature-asks-<date>.md`) with `feature-ask`.
- `touchpoint` is for discrete interaction log pages if filing separately; for most cases, `last_touchpoint:` frontmatter is sufficient.

---

## Full Example: Person Entity with CRM Fields

```yaml
---
title: Jane Smith
created: 2026-01-10
updated: 2026-04-20
type: entity
tags: [person, customer, crm]
sources: [raw/transcripts/qbr-acme-2026-04.md]
confidence: verified
coverage: partial
gaps: ["no visibility into renewal timeline"]
private: true
reports_to: null
direct_reports: []
peers: []
interaction_frequency: monthly
relationship_tier: strategic
last_touchpoint: 2026-04-18
meeting_cadence: monthly
next_meeting: 2026-05-15
influence_level: high
enriched_at: 2026-03-01
---
```

## Full Example: Company Entity with CRM Fields

```yaml
---
title: Acme Corp
created: 2025-11-02
updated: 2026-04-20
type: entity
tags: [company, customer, crm]
sources: [raw/transcripts/qbr-acme-2026-04.md]
confidence: verified
coverage: partial
gaps: ["competitive alternatives being evaluated unknown"]
private: true
relationship_tier: strategic
account_health: yellow
last_touchpoint: 2026-04-18
key_asks: ["SSO support", "audit logs", "better CI/CD integration"]
arr_tier: enterprise
enriched_at: 2026-02-14
---
```
