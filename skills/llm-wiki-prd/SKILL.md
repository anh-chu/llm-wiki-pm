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

Output structures for all three operations live in
`references/prd-templates.md` — copy the matching template when drafting.

### 1. PRD Draft

**Trigger:** "write a PRD", "draft PRD for [feature/topic]"

① **Ground in wiki** — `grep -ri "<feature>" "$WIKI" --include="*.md" -l`, then read
   every relevant page: entities, concepts, comparisons, customer pages, and
   `decision`/`roadmap`/`question`-tagged pages.
② **Surface gaps before drafting** — if a major section has no wiki backing
   (target persona, competitive context, core problem, key decisions), flag it and
   ask; never draft a fabricated section silently:
   > "Missing wiki coverage for: [X, Y, Z]. Draft with gaps flagged, or research first?"
③ **Draft** to `$WIKI/queries/prd-<feature-slug>-<YYYY-MM-DD>/README.md` using the
   PRD template (`references/prd-templates.md`).
④ **Cite inline** — every factual claim cites its source ("Per [[page]]..."); an
   uncited claim moves to Open Questions or `gaps:`.
⑤ **Populate `gaps:`** with unbacked sections — this surfaces in Coverage Audit.
⑥ **Update navigation** — add to `index.md` under `queries/`, append the `prd` log line.

### 2. User Stories

**Trigger:** "create user stories", "write user stories for [feature]", "acceptance criteria"

① **Ground in wiki** — same search as PRD ①.
② **Read persona pages** — `grep -ri "persona" "$WIKI/entities" -l`; read each
   relevant `entities/<name>-persona.md` for "As a [persona]" framing. If none exist:
   > "No customer entity pages found. Stories will use generic personas. Create customer pages first for grounded framing?"
③ **Generate stories** — `As a [persona], I want [action] so that [outcome].` One
   per distinct need, grouped by persona.
④ **Add acceptance criteria** — Given/When/Then per story; flag any criterion
   that's an assumption with no wiki backing.
⑤ **File** to `$WIKI/queries/user-stories-<feature-slug>-<YYYY-MM-DD>.md` using the
   template; append the `user-stories` log line.
⑥ **Link back** from the relevant concept/roadmap page.

### 3. Release Notes

**Trigger:** "generate release notes", "draft release notes", "what shipped"

① **Date range** — if unspecified, ask; "last release" → find the prior
   `release-notes` entry in `log.md` for the cutoff.
② **Read `log.md` for the range** — filter for `roadmap` pages, `decision` entries,
   `supersedes:` changes (deprecations), and crystallize/PRD `query` entries.
③ **Read the actual pages** — log summaries are thin; pull substance from the pages,
   never write release notes from log lines alone.
④ **Draft** by category using the template. User-facing copy stays clean — no wiki
   jargon or `[[wikilinks]]`; citations go only in the internal-context section.
⑤ **File** to `$WIKI/queries/release-notes-<YYYY-MM-DD>.md`; append the
   `release-notes` log line.

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
