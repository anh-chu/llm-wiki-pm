# LLM Wiki PM — Universal Agent Contract

Behavioral rules for all agents. Operation details live in `skills/llm-wiki-pm/SKILL.md` and sub-skill files. This file governs *how* agents behave, not *what* they do.

## Wiki Path Resolution

```bash
WIKI=$(cat .wiki-path 2>/dev/null | tr -d '[:space:]')
WIKI=${WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}
```

Always resolve this before any wiki operation. Never hardcode paths. If none of these resolve to a valid directory, surface: "No wiki path configured. Run `/llm-wiki-pm:set-wiki-path ~/path/to/wiki`."

## Orient Protocol (mandatory before writes)

Before any write (ingest, update, archive, supersede), complete the core skill's Orient steps ①-④ (read SCHEMA.md, index.md, recent log.md, overview.md) in the current session. Narrow read-only queries may skip it. Full detail: core `llm-wiki-pm` SKILL.md → "Orient Every Session".

## Source Attribution

Every non-obvious factual claim in wiki pages must carry an inline source marker:

`[source: raw-slug, location]`

Where `location` is a page number, section name, or timestamp (e.g. `[source: gartner-mq-2026, p.12]`).

The page's frontmatter `sources:` field lists all sources for the page. Inline markers anchor individual claims. Both are mandatory — frontmatter alone doesn't anchor which source backs which claim.

## Core Operations Summary

Operation procedures (Ingest, Query, Update, Lint, Crystallize) live in the core `llm-wiki-pm` SKILL.md → "Core Operations". This file governs only the cross-cutting behavioral constraints below.

## Behavioral Constraints

**No silent overwrites.** Show diff before writing. Confirm for changes touching 5+ pages or altering stated strategy.

**No schema drift.** New tags require a SCHEMA.md update before use. Tags not in taxonomy are a lint error.

**No orphan pages.** Min 2 outbound `[[wikilinks]]` per page. After creating a page, add inbound links from related pages.

**Snapshot before destructive ops.** Copy to `_archive/<slug>-<YYYY-MM-DD>.md` before overwrite, archive, or supersede.

**Verify writes.** Re-read after writing. If frontmatter is malformed or write failed, do not update index.md or log.md.

**No raw/ mutations.** Layer 1 sources are immutable. Corrections live in wiki pages.

**Privacy by default (allowlist).** Every page is private and excluded from exports unless it carries `shareable: true`. Do NOT add a `private:` flag — it is noise the tooling never reads. Leave customer names, deal sizes, and 1:1 content unflagged (they stay private automatically); add `shareable: true` only to genuinely public-safe pages.

**Supersede explicitly.** Materially replacing a page requires `supersedes:` / `superseded_by:` frontmatter + archive + link rewrite. Silent replacement is not allowed.

**Confirm mass updates.** 10+ pages touched → show list, get user sign-off before writing.

**Dedup ambient captures.** Grep wiki before offering to add a fact. If it already exists, offer to update — not create.

## Model Routing

| Task | Model |
|------|-------|
| File reads, grep, web fetches, writing pages, log appends | Sonnet (I/O worker) |
| Synthesis, crystallize, coverage audit, conflict resolution | Opus (reasoning) |

Workers write output ≥ 2K tokens to `/tmp/{task}-{YYYYMMDD}.md` and return short status + path.

## Skill Architecture

The plugin uses a modular sub-skill design. Each sub-skill is a separate SKILL.md with
scoped `when_to_use` triggers. The core skill (`llm-wiki-pm`) serves as the fallback for
any operation not handled by an installed sub-skill.

| Sub-skill | Handles | Core fallback |
|-----------|---------|---------------|
| `llm-wiki-brief` | Daily/weekly briefs, tag digests, coverage brief | §10, §11, §12 |
| `llm-wiki-prd` | PRD drafts, user stories, release notes | — |
| `llm-wiki-research` | Research sprints, competitive deep dives, stub enrichment | — |
| `llm-wiki-crm` | Relationship health, auto-enrichment, feature ask tracking | — |
| `llm-wiki-persona` | Communication persona pages, relationship maps | — |
| `llm-wiki-maintain` | Daily-maintenance loop (sweep all sources → ingest → brief → tidy), interactive/autonomous modes | run steps manually |

Sub-skills are additive. Install only what you need. The core skill works standalone.

## Agent Surfaces

This plugin ships Claude Code support:
- **Core skill**: `skills/llm-wiki-pm/SKILL.md`
- **Sub-skills**: `skills/llm-wiki-{brief,prd,research,crm,persona,maintain}/SKILL.md`
- **Workers**: `.claude/agents/` (indexer, fetcher, link-validator, lint, people-updater)
- **Role packs**: `.claude/roles/` (product-manager, researcher, executive, founder)

This file is the portable behavioral contract for any future agent surfaces.
