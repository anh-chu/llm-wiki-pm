---
name: llm-wiki-crm
description: PM relationship CRM layer on top of the wiki. Relationship health, auto-enrichment via web search, account health tracking, and people profile maintenance. Does not replace Salesforce — tracks PM-specific context (product feedback, feature asks, strategic relationship, communication history).
when_to_use: Use for "relationship health", "account health", "who haven't I talked to", "enrich [person/company]", "auto-enrich", "CRM", "strategic accounts", "dormant accounts", "update [person] profile", "what does [company] want from us", "feature asks by account".
allowed-tools: Read Grep Write Bash WebSearch
---

# LLM Wiki CRM

CRM layer on top of the PM wiki. Tracks relationship health, account status, feature asks, and auto-enrichment for people and company entities. Complements Salesforce — this layer captures PM-specific context that CRMs don't: product feedback, feature asks, communication history, strategic relationship signals.

## When This Skill Activates

- "relationship health", "who haven't I talked to", "dormant accounts", "check relationships"
- "enrich [entity]", "auto-enrich [person/company]", "fill in [entity] details"
- "account health", "strategic accounts", "how are my accounts"
- "what do customers want", "feature asks", "what are accounts asking for", "customer asks"
- "log touchpoint with [person/company]", "update [entity] relationship", "set [entity] to strategic"
- "CRM", "key accounts", "contact cadence", "overdue contacts"

## New CRM Frontmatter Fields

These fields extend the core wiki SCHEMA.md. Add them to entity pages as relevant.
See `skills/llm-wiki-crm/templates/SCHEMA-crm-fields.md` for a merge-ready patch.

### Person Entity Additions

```yaml
relationship_tier: strategic | active | watch | dormant
last_touchpoint: YYYY-MM-DD
meeting_cadence: daily | weekly | biweekly | monthly | quarterly | ad-hoc
next_meeting: YYYY-MM-DD        # optional
influence_level: high | medium | low
enriched_at: YYYY-MM-DD         # when auto-enrichment last ran
```

### Company Entity Additions

```yaml
relationship_tier: strategic | active | watch | dormant
account_health: green | yellow | red
last_touchpoint: YYYY-MM-DD
key_asks: []                    # list of feature/product asks from this account
arr_tier: enterprise | mid-market | smb | prospect   # optional, no dollar figures
enriched_at: YYYY-MM-DD         # when auto-enrichment last ran
```

### Tier Definitions

| Tier | Meaning |
|------|---------|
| `strategic` | High-impact relationship. Flag if silent > 14 days. |
| `active` | Regular engagement. Flag if silent > 30 days. |
| `watch` | Relationship at risk or low-signal. Flag if silent > 60 days. |
| `dormant` | No active engagement. Informational only. |

### Account Health Definitions

| Value | Meaning |
|-------|---------|
| `green` | Healthy engagement, no known issues |
| `yellow` | Some friction — risk of churn, unresolved asks, reduced engagement |
| `red` | Needs immediate attention — escalation risk, silent, or major open issue |

## Wiki Path Resolution

```bash
WIKI=$(cat .wiki-path 2>/dev/null | tr -d '[:space:]')
WIKI=${WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}
```

## Operations

### 1. Relationship Health Check

**Trigger:** "relationship health", "who haven't I talked to", "dormant accounts", "check relationships"

① Scan all person and company entity pages for `last_touchpoint:` and `relationship_tier:`.
② Apply staleness thresholds (strategic >14d, active >30d, watch >60d, dormant = skip).
③ Surface grouped by tier:
   > "3 strategic contacts need attention: [[X]], [[Y]], [[Z]] (last contact: N days ago)"
④ For each flagged entity: last touchpoint, key_asks, account_health, next_meeting if set.
⑤ Offer to run Pre-Meeting Briefing (core skill §9) for any flagged entity.
⑥ Log: `## [date] crm-health | flagged: N strategic, N active`

---

### 2. Auto-Enrichment

**Trigger:** "enrich [entity]", "auto-enrich [person/company]", "fill in [entity] details"

**Company enrichment:**
① WebSearch: company name + "about", funding, headcount, key products, recent news
② Extract: founded year, HQ, employee count, funding stage, key products, recent press
③ Update entity page. Set `enriched_at: today`. Add inline: `[source: <url>, <date>]`
④ Bump `coverage:` stub → partial if meaningful data found
⑤ Flag time-sensitive data with `confidence_decay_days: 90`

**Person enrichment:**
① WebSearch: person name + company + role, LinkedIn (public), recent talks/posts
② Extract: current role, company, background, public positions on relevant topics
③ Update entity page. Only public information — never infer private details.
④ If person is `strategic` tier and no persona page exists, offer to create one.

---

### 3. Account Health Dashboard

**Trigger:** "account health", "strategic accounts", "how are my accounts"

① Scan company entity pages with `relationship_tier: strategic | active`.
② Aggregate: account_health distribution, key_asks frequency across accounts, last touchpoint age.
③ Output:
   - 🔴 Red accounts: N
   - 🟡 Yellow accounts: N
   - 🟢 Green accounts: N
   - Top feature asks: [feature] (N accounts), [feature] (N accounts)
④ Surface cross-account key_asks patterns — high-signal roadmap inputs.
⑤ Offer to file as `queries/account-health-<date>.md`.

---

### 4. Feature Ask Tracker

**Trigger:** "what do customers want", "feature asks", "what are accounts asking for"

① Grep all entity pages for `key_asks:` frontmatter.
② Aggregate: count asks per feature/theme across accounts.
③ Cross-reference with `roadmap`-tagged pages — is the ask already on roadmap?
④ Output table:

| Feature ask | Accounts requesting | On roadmap? |
|---|---|---|
| [feature] | N accounts | yes / no / unknown |

⑤ File as `queries/feature-asks-<date>.md`.

---

### 5. Update Relationship Fields

**Trigger:** "log touchpoint with [person/company]", "update [entity] relationship"

① Read entity page.
② Update: `last_touchpoint:` to today, `relationship_tier:` and `account_health:` if specified.
③ Prompt for notes to add to interaction history section.
④ If meeting just happened, offer to ingest transcript (hands off to core §2).

---

## Behavioral Notes

- **No dollar figures**: `arr_tier` uses tiers only. Never record ARR, deal sizes, or revenue figures.
- **Private by default**: entity pages with `relationship_tier` set — consider `private: true` for sensitive account intel.
- **Enrich only public data**: never infer private details (financials, internal decisions, personal info).
- **key_asks is a list**: normalize phrasing across accounts so aggregation works cleanly.
- **Log every CRM operation** with `crm-` prefix:
  - `## [date] crm-health | flagged: N strategic, N active`
  - `## [date] crm-enrich | <entity> | enriched_at: <date>`
  - `## [date] crm-touchpoint | <entity> | last_touchpoint: <date>`
  - `## [date] crm-feature-asks | filed: queries/feature-asks-<date>.md`
