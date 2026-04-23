---
name: llm-wiki-brief
description: Structured daily/weekly briefs, tag digests, and check-ins from the PM wiki. Richer output than core catch-me-up.
when_to_use: Use for "daily brief", "weekly brief", "weekly checkin", "what happened this week", "what's new", "[tag] digest", "summarize [tag] pages", "what changed in [topic]", "brief me on [tag]". Core llm-wiki-pm handles these as fallback if this skill is not installed.
allowed-tools: Read Grep Bash
---

# LLM Wiki Brief

Structured briefs, digests, and check-ins from the PM wiki. Richer, more structured output than the §10/§11 fallbacks in the core llm-wiki-pm skill.

For ingest, update, query, lint, and all other wiki operations — the core `llm-wiki-pm` skill handles those. This skill is brief-only.

## When This Skill Activates

- "daily brief", "what happened today", "what happened yesterday"
- "weekly brief", "weekly checkin", "what happened this week", "week in review", "catch me up on the week"
- "[tag] digest", "brief me on [tag]", "summarize [tag] pages", "what's new in [topic]", "what changed in [competitive/customer/strategy/etc]"
- "what's thin", "what needs more work", "coverage brief"

## Wiki Path Resolution

```bash
WIKI=$(cat .wiki-path 2>/dev/null | tr -d '[:space:]')
WIKI=${WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}
```

## Orient (lightweight)

This skill is read-only by default. Before any brief:
1. Read `$WIKI/_status.md` if it exists — surface any pre-computed warnings immediately
2. Read last 20-30 lines of `$WIKI/log.md` — know what's recent before summarizing

Full orient (AGENTS.md 4-step protocol) only required if filing output as a wiki page.

---

## Operations

### 1. Daily Brief

**Triggers:** "daily brief", "what happened today", "what happened yesterday"

① Resolve `$WIKI`. Read `$WIKI/_status.md` if present.

② Read `$WIKI/log.md`. Filter entries from the last 24-48 hours. Parse:
   - Pages created (`ingest`, `create`)
   - Pages updated (`update`)
   - Decisions logged (`decision`)
   - Open questions added (`query`, `question`)

③ For decision and question entries, read the referenced page to pull the one-line summary or question text.

④ Output format — structured, scannable, no prose padding:

```markdown
## Daily Brief — YYYY-MM-DD

### New Pages
- [[slug]] — one-line description

### Updated Pages
- [[slug]] — what changed (one phrase)

### Decisions Logged
- [[slug]]: decision text (YYYY-MM-DD)

### Open Questions Added
- [[slug]]: question text

### Warnings
- (staleness, coverage flags, lock state from _status.md)
```

If 24h window is empty, expand to 48h and note it. If still empty, offer weekly brief.

**Log:** Read-only — do not append to log.md unless user asks to file output.

---

### 2. Weekly Brief / Check-in

**Triggers:** "weekly brief", "weekly checkin", "what happened this week", "week in review", "what did I miss"

① Resolve `$WIKI`. Read `$WIKI/_status.md` if present.

② Read `$WIKI/log.md`. Filter entries from last 7 days (default; user can specify N days).

③ Aggregate counts: pages created, updated, decisions logged, questions added vs resolved.

④ Identify top 3 areas of activity: grep mentioned slugs' frontmatter tags, count by tag frequency.

⑤ Lightweight staleness check on `overview.md` and `index.md`: if `updated:` older than 14 days AND log shows writes this week, surface warning.

⑥ Coverage gaps: grep for `coverage: stub` pages created this week only — not all stubs, just new ones.

⑦ Output format:

```markdown
## Weekly Brief — Week of YYYY-MM-DD

### Summary
- Pages created: N | updated: N | decisions: N | open questions: N added, N resolved

### Top Activity Areas
1. [tag] — N entries, top pages: [[a]], [[b]]
2. [tag] — N entries, top pages: [[c]]
3. [tag] — N entries, top pages: [[d]]

### Decisions This Week
- [[slug]]: decision text (YYYY-MM-DD)

### Open Questions Added
- [[slug]]: question text

### Staleness Flags
- [[overview.md]] last updated YYYY-MM-DD — may need refresh

### Coverage Gaps from This Week
- [[slug]] created as stub — gaps: X, Y

### Warnings
- (from _status.md)
```

⑧ Offer to file as `queries/weekly-brief-YYYY-MM-DD.md`. If yes, run full orient per AGENTS.md before writing.

**Log:** `## [YYYY-MM-DD] brief | weekly | last 7 days | filed: yes/no` — only if filing.

---

### 3. Tag Digest

**Triggers:** "[tag] digest", "brief me on [tag]", "summarize [tag] pages", "what's new in [tag]"

① Resolve `$WIKI`. Check tag exists in `$WIKI/SCHEMA.md` taxonomy. If not: "Tag '[x]' not in taxonomy. Did you mean: [closest matches]?"

② Grep for matching pages:
   ```bash
   grep -rl "tags:.*\b<tag>\b" $WIKI/entities $WIKI/concepts $WIKI/comparisons --include="*.md"
   ```

③ Sort by `updated:` desc. Read each page: title, type, updated, coverage, confidence, 2-3 sentence summary.

④ Cross-reference with log.md: grep each slug in last 30 days. Note recent activity.

⑤ Identify themes: recurring entities/concepts, what changed recently, open questions (question-tagged pages with matching tag), patterns, gaps.

⑥ Output format:

```markdown
## [Tag] Digest — YYYY-MM-DD
N pages tagged [tag]

### Key Themes
- [Theme]: [2-3 sentence synthesis]
  Sources: [[page-a]], [[page-b]]

### Recently Updated (last 14 days)
- [[slug]] (YYYY-MM-DD): what changed

### Open Questions
- [[query-slug]]: question text

### Notable Patterns
- [Pattern observed across pages]

### Coverage Notes
- [[slug]]: stub — gaps: X, Y
```

⑦ Offer to file as `queries/[tag]-digest-YYYY-MM-DD.md`. If yes, full orient before writing.

**Log:** `## [YYYY-MM-DD] digest | tag: <tag> | N pages | filed: yes/no` — only if filing.

---

### 4. Coverage Brief

**Triggers:** "what's thin", "what needs more work", "coverage brief"

① Scan `coverage:` frontmatter across `entities/`, `concepts/`, `comparisons/`. Count: stub, partial, comprehensive, missing.

② For stub/partial pages, collect `tags:` and `gaps:`. Group by primary tag.

③ Output format:

```markdown
## Coverage Brief — YYYY-MM-DD

### Summary
- Stub: N | Partial: N | Comprehensive: N | No marker: N

### Stubs by Domain
**[competitive]** — N stubs
- [[slug-a]], [[slug-b]]
- Top gaps: X, Y

**[customer]** — N stubs
- [[slug-c]]

### Partial Pages with Notable Gaps
- [[slug]]: gaps: [list]

### Recommended Next Actions
- [[slug]]: highest-priority — appears in N cross-references
```

④ Offer: "For full audit with orphan detection and taxonomy analysis, run Coverage Audit (§12) from llm-wiki-pm."

**No log entry** — pure read operation.

---

## Boundaries

This skill handles: daily brief, weekly brief, tag digest, coverage brief.

For everything else — ingest, update, query, lint, archive, persona, pre-meeting briefing — the core `llm-wiki-pm` skill handles those.

> "For full ingest/update/query operations, the core llm-wiki-pm skill handles those."

## Behavioral Constraints (per AGENTS.md)

- **No writes without orient.** Filing a brief requires full orient + SCHEMA.md compliance.
- **No schema drift.** Filed query pages use taxonomy tags only.
- **No orphan pages.** Filed briefs need min 2 outbound `[[wikilinks]]`.
- **Privacy.** Log entries referencing `private: true` pages — surface topic category only, not content.
- **Human tone.** Scannable over verbose. No em-dashes. No AI tells.
