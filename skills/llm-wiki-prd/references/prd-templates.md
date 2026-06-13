# PRD Artifact Templates

Output structures for the three llm-wiki-prd operations. The SKILL.md stub gates
each operation's procedure; copy the matching template here when drafting.

All artifacts use `type: query`, list every consulted page in `sources:`, list
unbacked sections in `gaps:`, get added to `index.md` under `queries/`, and get a
`log.md` entry. See SKILL.md "Output Filing Conventions" for the canonical rule.

## PRD Draft

File to `$WIKI/queries/prd-<feature-slug>-<YYYY-MM-DD>/README.md`.

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

Example `gaps:` population:
```yaml
gaps:
  - "Competitive Context: no comparison page for <Competitor X>"
  - "User Personas: no customer entity page for Enterprise buyer"
```

Log: `## [YYYY-MM-DD] prd | prd-<feature-slug> | pages cited: [list] | gaps: [list]`

## User Stories

File to `$WIKI/queries/user-stories-<feature-slug>-<YYYY-MM-DD>.md`.

Story format: `As a [persona from wiki], I want [action] so that [outcome].`
Acceptance criteria per story in Given/When/Then form; flag any criterion that is
an assumption with no wiki backing.

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

Log: `## [YYYY-MM-DD] user-stories | user-stories-<feature-slug> | persona: [list] | gaps: [list]`

## Release Notes

File to `$WIKI/queries/release-notes-<YYYY-MM-DD>.md`.

Group by category. Keep user-facing copy clean — no wiki jargon, no `[[wikilinks]]`
in the final copy. Cite `[[pages]]` only in the internal-context section at the
bottom, so the artifact stays grounded while the user-facing sections read cleanly.

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

Log: `## [YYYY-MM-DD] release-notes | release-notes-<date> | range: YYYY-MM-DD to YYYY-MM-DD | items: N`
