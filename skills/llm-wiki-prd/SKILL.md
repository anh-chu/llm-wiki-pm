---
name: llm-wiki-prd
description: Generate PRDs, user stories, and release notes grounded in wiki knowledge. Reads entities, concepts, decisions, and customer pages as source material.
when_to_use: Use for "write a PRD", "draft PRD for [feature]", "create user stories", "write user stories for [feature]", "generate release notes", "draft release notes", "write acceptance criteria". Only activates for artifact generation — not for wiki operations.
allowed-tools: Read Grep Write Bash
---

# LLM Wiki PRD

Sub-skill of llm-wiki-pm. Generates PM artifacts (PRDs, user stories, release notes) from wiki knowledge. The wiki is the only source of truth. Never fabricates product context.

## When This Skill Activates

- "write a PRD", "draft PRD for [feature/topic]"
- "create user stories", "write user stories for [feature]", "acceptance criteria"
- "generate release notes", "draft release notes", "what shipped"

Does not activate for wiki operations (ingest, update, lint, query). Those route to llm-wiki-pm.

## Orient Before Any Artifact

Per AGENTS.md, orient before any write. PRD generation requires knowing what pages exist to avoid duplication and ensure grounding.

**Orient steps (mandatory):**

```bash
WIKI=$(cat .wiki-path 2>/dev/null | tr -d '[:space:]')
WIKI=${WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}
```

① Read `$WIKI/SCHEMA.md` — tag taxonomy, domain scope
② Read `$WIKI/index.md` — what pages exist (prevents duplicate artifacts, identifies grounding material)
③ Read last 20-30 lines of `$WIKI/log.md` — recent activity
④ Read `$WIKI/overview.md` — current synthesis state

**Orient gate (enforced):** if steps ①-④ are not complete in this session, refuse any write. Surface: "Need to orient first. Running now." Then orient, then proceed.

## Key Constraint

Never invent product context. If the wiki has no page for a claimed feature, customer segment, or competitive context, say so and offer to create a stub first:

> "No wiki page found for [X]. Draft with that gap flagged, or create a stub page first?"

Every factual claim in a generated artifact must cite `[[page]]` from the wiki. No citation = no claim.

---

## Operations

### 1. PRD Draft

**Trigger:** "write a PRD", "draft PRD for [feature/topic]"

**① Ground in wiki**

Grep wiki for the feature/topic:

```bash
grep -ri "<feature>" "$WIKI" --include="*.md" -l
```

Read all relevant pages:
- Entity pages (`entities/`) for companies, products, teams involved
- Concept pages (`concepts/`) for strategy, themes, frameworks
- Comparison pages (`comparisons/`) for competitive context
- Customer pages for pain points and use cases
- Decision pages (`tags: decision`) for prior choices
- Roadmap pages (`tags: roadmap`) for proposed direction
- Open question pages (`tags: question`) in `queries/`

**② Surface gaps before drafting**

If key sections have no wiki backing, flag before writing:

> "Missing wiki coverage for: [X, Y, Z]. Draft with gaps flagged, or research first?"

Common gaps to check:
- No customer page for the target persona
- No comparison/competitive page for the market context
- No concept page for the core problem
- No decision page for the key architectural or strategic choices

Do not draft silently when major sections would be fabricated. Ask.

**③ Draft PRD**

File to `$WIKI/queries/prd-<feature-slug>-<YYYY-MM-DD>/README.md`.

Structure:

```markdown
---
title: "PRD: <Feature Name>"
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: query
tags: [roadmap, decision]
sources: [<list of wiki pages cited>]
gaps: [<list of sections with no wiki backing>]
coverage: partial
---

# PRD: <Feature Name>

## Problem Statement
<!-- From customer pages, concept pages. Cite: [[page]] -->

## Goals & Success Metrics
<!-- From strategy/roadmap pages, decision pages. Cite: [[page]] -->

## User Personas
<!-- From customer entity pages. Cite: [[page]] -->

## Competitive Context
<!-- From comparison/competitive pages. Cite: [[page]] -->

## Proposed Solution
<!-- From roadmap/concept pages. Cite: [[page]] -->

## Out of Scope
<!-- Call out explicitly. Note if absence of wiki pages is why something is out of scope. -->

## Open Questions
<!-- From open question-tagged pages. Cite: [[queries/open-question-slug]] -->
```

**④ Cite sources inline**

Every factual claim cites its wiki source: "Per [[concept/ai-market-position]], the primary pain point is..."

No citation = claim must be moved to Open Questions or flagged as a gap.

**⑤ Flag coverage gaps in frontmatter**

Populate the `gaps:` field with sections that had no wiki backing. This surfaces during Coverage Audit (§12 of llm-wiki-pm).

Example:
```yaml
gaps:
  - "Competitive Context: no comparison page for <Competitor X>"
  - "User Personas: no customer entity page for Enterprise buyer"
```

**⑥ Update navigation**

- Add to `$WIKI/index.md` under `queries/` section
- Append to `$WIKI/log.md`:
  ```
  ## [YYYY-MM-DD] prd | prd-<feature-slug> | pages cited: [list] | gaps: [list]
  ```

---

### 2. User Stories

**Trigger:** "create user stories", "write user stories for [feature]", "acceptance criteria"

**① Grep wiki for feature context**

Same search as PRD step ①. Read entity, concept, roadmap, and customer pages for the feature.

**② Read customer persona pages**

```bash
grep -ri "persona" "$WIKI/entities" --include="*.md" -l
```

Read `entities/<name>-persona.md` for each relevant customer segment. These provide the "As a [persona]" framing. If no customer pages exist, flag it:

> "No customer entity pages found. Stories will use generic personas. Create customer pages first for grounded framing?"

**③ Generate stories**

Format:
```
As a [persona from wiki], I want [action] so that [outcome].
```

One story per distinct user need. Group by persona if multiple.

**④ Add acceptance criteria**

Per story, Given/When/Then format:

```
Given [precondition]
When [action]
Then [expected outcome]
And [additional assertion if needed]
```

Base criteria on wiki facts where possible. Flag criteria that are assumptions (no wiki backing).

**⑤ File the output**

Save to `$WIKI/queries/user-stories-<feature-slug>-<YYYY-MM-DD>.md`:

```markdown
---
title: "User Stories: <Feature Name>"
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: query
tags: [roadmap]
sources: [<wiki pages cited>]
gaps: [<assumptions with no wiki backing>]
coverage: partial
---

# User Stories: <Feature Name>

## [Persona Name] — [[entities/persona-page]]

### Story 1
As a [persona], I want [action] so that [outcome].

**Acceptance Criteria**
- Given [X]
- When [Y]
- Then [Z]

[source: [[wiki-page]]]
```

**⑥ Link back from concept or roadmap page**

After filing, add a backlink from the relevant concept or roadmap page:

> "User stories filed at [[queries/user-stories-<feature-slug>-<date>]]"

Append to `$WIKI/log.md`:
```
## [YYYY-MM-DD] user-stories | user-stories-<feature-slug> | persona: [list] | gaps: [list]
```

---

### 3. Release Notes

**Trigger:** "generate release notes", "draft release notes", "what shipped"

**① Identify the date range**

If the user does not specify a date range, ask:

> "What date range should I cover? (e.g., since last release on YYYY-MM-DD, or past N weeks)"

If the user says "last release", check `$WIKI/log.md` for a previous `release-notes` entry to find the prior cutoff.

**② Read log.md entries for the range**

```bash
grep -A5 "^## \[2" "$WIKI/log.md"
```

Filter for:
- Pages created or updated with `tags: roadmap`
- `decision` log entries
- Any `supersedes:` changes (signals deprecations)
- Any `type: query` entries from crystallize or PRD flows

**③ Read the actual pages touched**

Log summaries are brief. For each significant entry, read the full page to extract substance. Do not write release notes from log summaries alone.

**④ Draft release notes**

Group by category. Keep user-facing copy clean — no wiki jargon, no `[[wikilinks]]` in the final copy, no internal page references visible to users.

```markdown
---
title: "Release Notes: <date or version>"
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: query
tags: [roadmap]
sources: [<wiki pages referenced during drafting>]
---

# Release Notes: <date or version>

## New Features
- <Feature>: <one-sentence description of user value>

## Improvements
- <What changed>: <why it matters>

## Fixes
- <What was broken>: <what it does now>

## Deprecations
- <What is going away>: <migration path or replacement>

---
_Internal PM context: [links to relevant wiki pages for internal reference]_
```

The `_Internal PM context_` section at the bottom is for PM use — cite `[[pages]]` there so the artifact stays grounded but the user-facing sections read cleanly.

**⑤ File the output**

Save to `$WIKI/queries/release-notes-<YYYY-MM-DD>.md`.

Append to `$WIKI/log.md`:
```
## [YYYY-MM-DD] release-notes | release-notes-<date> | range: YYYY-MM-DD to YYYY-MM-DD | items: N
```

---

## Output Filing Conventions

| Artifact | Path |
|----------|------|
| PRD | `$WIKI/queries/prd-<feature-slug>-<YYYY-MM-DD>/README.md` |
| User Stories | `$WIKI/queries/user-stories-<feature-slug>-<YYYY-MM-DD>.md` |
| Release Notes | `$WIKI/queries/release-notes-<YYYY-MM-DD>.md` |

All artifacts:
- `type: query` in frontmatter
- `sources:` lists all wiki pages consulted
- `gaps:` lists sections with no wiki backing
- Added to `index.md` under the `queries/` section
- Logged in `log.md`

---

## Behavioral Constraints

Inherited from AGENTS.md. The following apply specifically to artifact generation:

**No fabrication.** Every claim must cite a wiki page. If no page exists, the claim goes to gaps or open questions.

**No silent gaps.** If a major PRD section has no wiki backing, surface it before drafting and populate `gaps:` in frontmatter.

**Orient first.** Read SCHEMA.md, index.md, log.md tail, overview.md before generating any artifact.

**No wiki jargon in user-facing copy.** Release notes and PRDs shared externally should read naturally. Internal citations go in frontmatter `sources:` and an internal-only section.

**No orphan artifacts.** After filing, add the artifact to `index.md` and link back from any relevant concept or roadmap page it references.

**Verify writes.** Re-read after writing. If frontmatter is malformed, do not update index.md or log.md.

---

## Pitfalls

- **Grounding first, drafting second.** Resist the pull to draft immediately. The grep + page reads are not optional.
- **Gaps are information.** A PRD with explicit gaps is more useful than one with confident fabrications.
- **Log summaries lie by omission.** For release notes, read the actual pages — not just the log lines.
- **Persona pages are pre-work.** Without `entities/<name>-persona.md` pages, user stories default to generic framing.
- **Release note scope creep.** Only include items with wiki backing. Don't pad from memory.
