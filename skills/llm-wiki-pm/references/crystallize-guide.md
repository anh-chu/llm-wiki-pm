# Crystallize Guide

Crystallization is the highest-leverage ingest pattern for PM work. It takes
a transcript, a multi-source research thread, or a completed exploration and
distills it into a structured digest page that compounds with the wiki.

Without this, transcripts just become entity-page updates and the "decision
+ action item" structure is lost.

## When to Crystallize

**Always:**
- 1:1 transcripts (Vu Lam monthly, direct reports)
- Customer call notes
- Internal strategy meetings with decisions
- Multi-source research threads you led (competitive deep-dive over a week)
- Major query answers that synthesized 5+ pages

**Optionally:**
- Long Slack threads with clear conclusions
- Post-mortem write-ups
- Conference/event debriefs

**Don't crystallize:**
- Single-article ingests (normal ingest is enough)
- Throwaway questions (don't file trivial lookups)

## Structure

```markdown
---
title: "Crystallize: <Topic or Meeting>"
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: query
tags: [decision, timeline, <domain tags>]
sources: [raw/transcripts/<slug>.md]
private: true      # default true for 1:1s, customer calls, internal meetings
---

# Crystallize: <Topic>

## Context
_1-2 sentences: what happened, when, who was involved_

## Decisions
- **<decision>** — rationale, owner, date confirmed
- …

## Action Items
| Owner | Action | Due | Status |
|---|---|---|---|
| Anh | Draft pricing proposal | 2026-04-25 | pending |
| Vu | Approve migration budget | 2026-04-30 | pending |

## Open Questions
- _Things we don't know yet, who should answer_

## Lessons / Patterns
- _Reusable insights extractable as standalone facts_
- _Link to existing [[concept]] pages or propose new ones_

## Links
- [[vu-lam]]
- [[trueplatform-launch]]
- [[pricing-strategy]]
```

## Crystallize Workflow

After ingesting a transcript into `raw/transcripts/`:

① **Read the transcript with intent** — not just "what's in here", but:
   - What decisions were made or confirmed?
   - What action items emerged? Who owns them?
   - What patterns repeat from past meetings?
   - What contradicts or updates existing wiki claims?

② **Draft the crystallize page** in `queries/crystallize-<topic>-<date>.md`

③ **Extract lessons as separate pages** if they're reusable:
   - A new framework → `concepts/<framework>.md`
   - A pattern observation → update existing concept page with new evidence
   - A decision with broad implications → `concepts/<decision>.md`

④ **Link heavily**:
   - Crystallize page → affected entities/concepts
   - Affected entities/concepts → back to crystallize page as a new source
   - Update `overview.md` if the crystallize shifted the big picture

⑤ **Update affected pages**:
   - Entity pages: add the meeting as a source, note new facts
   - Concept pages: reinforce or challenge, bump confidence
   - Roadmap pages: add action items or decisions

⑥ **Log**:
   ```
   ## [YYYY-MM-DD] crystallize | <topic>
   - queries/crystallize-<topic>-<date>.md
   - Affected: entities/vu-lam.md, concepts/pricing-strategy.md, ...
   ```

## Example: 1:1 with Vu Lam

Source: `raw/transcripts/vu-lam-1-1-2026-04.md`

Crystallize output: `queries/crystallize-vu-lam-2026-04.md`

```markdown
## Context
Monthly strategy 1:1 with Vu Lam, 45 min. Topics: TruePlatform launch slip,
Kai pricing signals from customer alpha, Q3 headcount.

## Decisions
- **TruePlatform GA pushed to June 15** — enterprise migration risk,
  confirmed by Vu, communicated to customer-alpha next week
- **Kai pricing stays usage-based for pilot** — revisit at 10-customer mark

## Action Items
| Anh | Write customer-alpha comms | 2026-04-22 | pending |
| Anh | Draft Kai pricing FAQ | 2026-04-29 | pending |
| Vu | Approve SE headcount req | 2026-05-01 | pending |

## Open Questions
- Kai seat-based vs usage-based at scale — need data team modeling
- TruePlatform pricing parity with Studio — decision by May

## Lessons
- Migration risk undercounted when customer runs N+1 versions in parallel
  → update [[enterprise-migration-playbook]]

## Links
- [[vu-lam]]
- [[trueplatform-launch]]
- [[kai]]
- [[customer-alpha]]
- [[enterprise-migration-playbook]]
```

Then update:
- `entities/vu-lam.md` — add 2026-04 1:1 as source, bump `updated`
- `concepts/trueplatform-launch.md` — note GA slip decision
- `concepts/kai-pricing.md` — reinforce usage-based pilot decision
- `overview.md` — if launch slip shifts quarter-view

## Crystallize vs Regular Ingest

| | Regular Ingest | Crystallize |
|---|---|---|
| Output | Source summary + entity updates | Structured digest + source summary + entity updates |
| Structure | Free-form | Context / Decisions / Actions / Questions / Lessons |
| When | Articles, reports, docs | Transcripts, research chains, major syntheses |
| Filed under | Entities, concepts | `queries/crystallize-*` |
| Privacy default | Page-by-page | Usually `private: true` |

## Querying Crystallize Pages

`grep -l "^type: query" queries/ | xargs grep "^title: .Crystallize"` lists
all crystallize pages. Useful for "what did we decide about X over the last
6 months?" queries.

Dataview query in Obsidian:

````markdown
```dataview
TABLE updated, sources
FROM "queries"
WHERE contains(tags, "decision") AND startswith(title, "Crystallize")
SORT updated DESC
```
````
