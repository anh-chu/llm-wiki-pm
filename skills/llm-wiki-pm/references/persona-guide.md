# Persona Guide

How to build persona and relationship map pages.

## When to build a persona page

- User explicitly requests a communication profile or style analysis for a person.
- A person entity page exists with 3+ attributes about communication style or
  language patterns, suggesting a persona page would compound better.
- During entity promotion scan (§2 step ①②) you find communication-style content
  buried inside a concept page alongside other entities.

## Persona page workflow

Use `templates/persona.md` as the starting point. Slug: `<name>-persona.md`
under `entities/`.

1. Confirm which tiers have source data. Never generate sections with no data.
2. Ingest source material first (Slack threads, emails) via §2 Ingest before
   writing the page. Attribution matters.
3. Fill in only what the sources support. Use "No data" for tiers without coverage.
4. Write the cross-tier comparison table last, from the tier sections.
5. Link from the person entity page: add `[[name-persona]]` under a
   "Communication profile" heading.

## What makes a good persona page

- Grounded in actual messages, not stereotypes.
- Explicit about data gaps. A persona with 2 tiers of real data is better than
  one with 4 tiers of guesses.
- Short core traits section (3-5 sentences), not a wall of bullets.
- The comparison table surfaces patterns that aren't obvious tier-by-tier.

## Relationship map

File: `concepts/relationship-map.md`. Create when 3+ person entities exist.

Format:

```markdown
---
title: Relationship Map
type: concept
tags: [person, katalon-internal]
updated: YYYY-MM-DD
---

# Relationship Map

## Org Chart

| Name | Role | Reports to | Direct reports | Interaction frequency |
|------|------|------------|----------------|-----------------------|
| [[vu-lam]] | CEO | - | [[anh-chu]], ... | - |
| [[anh-chu]] | Lead PM | [[vu-lam]] | ... | daily (async Slack) |

## Cross-functional Relationships

| Name | Counterpart | Nature | Frequency |
|------|-------------|--------|-----------|
| [[anh-chu]] | [[data-team]] | roadmap input | weekly |
```

Update whenever a new person entity is added to the wiki. Link to it from
each person entity page.

## Interaction frequency values

- `daily`: regular async Slack or daily syncs
- `weekly`: recurring 1:1 or team meeting
- `project-based`: collaborates during specific initiatives only
- `ad-hoc`: no regular cadence

## Frontmatter for persona pages

```yaml
---
title: "Persona: Full Name"
type: persona
tags: [person, persona, katalon-internal]
sources: [entities/name.md, raw/internal/slack-channel-YYYY-MM-DD.md]
language_patterns:
  sentence_length: short
  capitalization: standard
  punctuation: minimal
tone_by_channel:
  slack_dm: "direct, no formalities"
  slack_channel: "concise, professional"
  email_internal: "structured, numbered lists"
  email_external: "formal, no contractions"
vocabulary_markers:
  hedging_level: low
  humor_style: dry
  signoff_patterns: ["Thanks,", "Best,"]
code_switching: ["Vietnamese casual in Slack DMs"]
private: true
---
```

Set `private: true` when the persona is built from 1:1 or internal content.
