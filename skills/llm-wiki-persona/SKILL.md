---
name: llm-wiki-persona
description: Build communication persona pages and relationship maps for people in the PM wiki. Profiles how a person communicates across channels (chat, email), grounded in real message samples, plus org-chart relationship mapping.
when_to_use: Use for "build a persona for [person]", "communication profile", "style analysis", "how does [person] communicate", "persona page", "relationship map", "org chart", "map relationships", or after promoting a person entity that has 3+ communication-style attributes. For relationship/CRM context (tier, touchpoint, feature asks) use llm-wiki-crm instead; for factual enrichment use llm-wiki-research.
allowed-tools: Read Grep Write Bash
---

# LLM Wiki Persona

Communication persona pages and relationship maps for the PM wiki. Profiles *how*
a person communicates — grounded in real message samples, never stereotypes.

For ingest, query, update, and all other wiki operations, the core `llm-wiki-pm`
skill handles those. This skill is persona/relationship-only.

## Wiki Path Resolution

```bash
WIKI=$(cat .wiki-path 2>/dev/null | tr -d '[:space:]')
WIKI=${WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}
```

## Orient

Before writing a persona page, complete the core orient steps (read SCHEMA.md,
index.md, last 20-30 lines of log.md). Persona pages are wiki writes — they need
SCHEMA compliance, min 2 outbound `[[wikilinks]]`, and a log entry.

## When to build a persona page

- User explicitly requests a communication profile or style analysis for a person.
- A person entity page exists with 3+ attributes about communication style or
  language patterns, suggesting a persona page would compound better.
- During the core skill's entity-promotion scan you find communication-style
  content buried inside a concept page alongside other entities.

## Persona page workflow

Use `${CLAUDE_PLUGIN_ROOT}/skills/llm-wiki-pm/templates/persona.md` as the
starting point. Slug: `<name>-persona.md` under `entities/`.

① **Confirm data sources**: ask user which communication channels have actual
   source material. Don't fabricate channels you have no data for. Use whatever
   channels apply to this person's stack — common examples: private chat
   (Slack/Teams/Discord DM), public chat channel, internal email, external email.

② **Gather source material**: proactively search connected comms tools first
   (chat search, email search, meeting notes) for the person's name and
   email/handle, THEN confirm channels with the user. Don't ask the user to hand
   you material you can retrieve yourself. Ingest the threads via the core skill's
   §2 Ingest flow before writing the persona page. A persona built only from
   secondhand mentions on other wiki pages is not a persona — pull primary
   communication samples.

③ **Write persona page** at `entities/<name>-persona.md`:
   - Type: `persona`. Link to `[[<name>]]` entity in frontmatter `sources:`.
   - Core traits summary (3-5 sentences, no bullet spray).
   - One section per communication channel the person uses (substitute their
     actual stack — see the persona template for example channels). Don't
     force-fit vendor labels you have no data for. Fields per channel: formality,
     sentence length, humor, sign-off, notes.
   - Cross-channel comparison table at the bottom, written last from the channel
     sections. Use "No data" for channels without coverage.
   - Set `private: true` when the persona is built from 1:1 or internal content.

④ **Link persona to person entity**: add `[[<name>-persona]]` to the person
   entity page under Relationships or a "Communication profile" section.

⑤ **Log**: `## [YYYY-MM-DD] persona | <name>-persona | channels: [list]`

## What makes a good persona page

- Grounded in actual messages, not stereotypes.
- Explicit about data gaps. A persona with 2 channels of real data is better than
  one with 4 channels of guesses.
- Short core traits section (3-5 sentences), not a wall of bullets.
- The comparison table surfaces patterns that aren't obvious channel-by-channel.

## Relationship map

File: `concepts/relationship-map.md`. Create when 3+ person entities exist.

```markdown
---
title: Relationship Map
type: concept
tags: [person, internal]
updated: YYYY-MM-DD
---

# Relationship Map

## Org Chart

| Name | Role | Reports to | Direct reports | Interaction frequency |
|------|------|------------|----------------|-----------------------|
| [[ceo-name]] | CEO | - | [[lead-pm]], ... | - |
| [[lead-pm]] | Lead PM | [[ceo-name]] | ... | daily (async chat) |

## Cross-functional Relationships

| Name | Counterpart | Nature | Frequency |
|------|-------------|--------|-----------|
| [[lead-pm]] | [[data-team]] | roadmap input | weekly |
```

Update whenever a new person entity is added. Link to it from each person entity page.

Interaction frequency values:
- `daily`: regular async chat or daily syncs
- `weekly`: recurring 1:1 or team meeting
- `project-based`: collaborates during specific initiatives only
- `ad-hoc`: no regular cadence

## Persona page frontmatter

```yaml
---
title: "Persona: Full Name"
type: persona
tags: [person, persona, internal]
sources: [entities/name.md, raw/internal/<tool>-channel-YYYY-MM-DD.md]
language_patterns:
  sentence_length: short
  capitalization: standard
  punctuation: minimal
tone_by_channel:        # one key per channel the person uses; examples below
  private_chat: "direct, no formalities"
  public_chat: "concise, professional"
  email_internal: "structured, numbered lists"
  email_external: "formal, no contractions"
vocabulary_markers:
  hedging_level: low
  humor_style: dry
  signoff_patterns: ["Thanks,", "Best,"]
code_switching: []      # e.g. ["second language in casual chat DMs"]
private: true
---
```

## Behavioral Constraints (per AGENTS.md)

- **No writes without orient.** Persona pages require full orient + SCHEMA.md compliance.
- **No fabricated channels.** Only profile channels with real source material.
- **Privacy.** Personas from 1:1/internal content are `private: true`.
- **Human tone.** No em-dashes. No AI tells.
