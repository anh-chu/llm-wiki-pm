# LLM Wiki PM — Universal Agent Contract

Behavioral rules for all agents (Claude Code, Kiro, Gemini CLI, Cursor). Operation details live in `skills/llm-wiki-pm/SKILL.md`. This file governs *how* agents behave, not *what* they do.

## Wiki Path Resolution

```bash
WIKI=$(cat .wiki-path 2>/dev/null | tr -d '[:space:]')
WIKI=${WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}
```

Always resolve this before any wiki operation. Never hardcode paths. If none of these resolve to a valid directory, surface: "No wiki path configured. Run `/llm-wiki-pm:set-wiki-path ~/path/to/wiki`."

## Orient Protocol (mandatory before writes)

Before any write operation (ingest, update, archive, supersede), complete all four steps in the current session:

1. Read `$WIKI/SCHEMA.md` — domain scope, conventions, tag taxonomy
2. Read `$WIKI/index.md` — page catalog
3. Read last 20-30 lines of `$WIKI/log.md` — recent activity
4. Read `$WIKI/overview.md` — current synthesis state

**Orient gate:** if steps 1-4 are not complete in THIS session, refuse any write. Surface: "Need to orient first. Running now." Then orient, then proceed.

Read-only queries (single-page lookups) may skip orient.

## Source Attribution

Every non-obvious factual claim in wiki pages must carry an inline source marker:

`[source: raw-slug, location]`

Where `location` is a page number, section name, or timestamp (e.g. `[source: gartner-mq-2026, p.12]`).

The page's frontmatter `sources:` field lists all sources for the page. Inline markers anchor individual claims. Both are mandatory — frontmatter alone doesn't anchor which source backs which claim.

## Core Operations Summary

| Operation | Trigger | Key constraint |
|-----------|---------|----------------|
| **Ingest** | New source to add to wiki | Orient first. Surface takeaways before writing pages. Privacy filter on raw. Inline provenance on every claim. |
| **Query** | "What do we know about X?" | qmd first (semantic). Grep as fallback. Cite pages explicitly. |
| **Update** | New info revises existing claim | Snapshot to _archive/ before destructive write. Show diff. Sweep all stale variants. |
| **Lint** | Health check | Use worker-lint agent. Report only — no auto-fixes without user confirmation. |
| **Crystallize** | Meeting transcript or research chain | Produces decision-digest page under queries/. Confirm private: flag with user. |

## Behavioral Constraints

**No silent overwrites.** Show diff before writing. Confirm for changes touching 5+ pages or altering stated strategy.

**No schema drift.** New tags require a SCHEMA.md update before use. Tags not in taxonomy are a lint error.

**No orphan pages.** Min 2 outbound `[[wikilinks]]` per page. After creating a page, add inbound links from related pages.

**Snapshot before destructive ops.** Copy to `_archive/<slug>-<YYYY-MM-DD>.md` before overwrite, archive, or supersede.

**Verify writes.** Re-read after writing. If frontmatter is malformed or write failed, do not update index.md or log.md.

**No raw/ mutations.** Layer 1 sources are immutable. Corrections live in wiki pages.

**Privacy by default.** Customer names, deal sizes, 1:1 content → `private: true`. When in doubt, mark private.

**Supersede explicitly.** Materially replacing a page requires `supersedes:` / `superseded_by:` frontmatter + archive + link rewrite. Silent replacement is not allowed.

**Confirm mass updates.** 10+ pages touched → show list, get user sign-off before writing.

**Dedup ambient captures.** Grep wiki before offering to add a fact. If it already exists, offer to update — not create.

## Model Routing

| Task | Model |
|------|-------|
| File reads, grep, web fetches, writing pages, log appends | Sonnet (I/O worker) |
| Synthesis, crystallize, coverage audit, conflict resolution | Opus (reasoning) |

Workers write output ≥ 2K tokens to `/tmp/{task}-{YYYYMMDD}.md` and return short status + path.

## Agent Surfaces

This plugin ships support for:
- **Claude Code**: `skills/llm-wiki-pm/SKILL.md` + `.claude/agents/` workers + `.claude/roles/` packs
- **Kiro**: `.kiro/powers/llm-wiki-pm/POWER.md`
- **Gemini CLI**: `.gemini/commands/llm-wiki-pm.toml`

All surfaces follow this file's behavioral contract.
