# Update Guide

Updating is a separate discipline from ingesting. Strategy docs, competitor
positions, customer states shift. Without update discipline, the wiki
accumulates stale claims that contradict each other silently.

## When to use Update (not Ingest)

- New source contradicts an existing claim
- New info refines/corrects an existing claim
- Customer state changed (renewal, churn, expansion)
- Competitor shipped/pivoted
- Strategic bet shifted
- A decision was reversed

If the source is brand new territory (no existing pages), use Ingest instead.

## The Update Flow

### 1. Identify all affected pages

Three-way search for completeness:

```bash
# Structural, pages that link to the entity being revised
python3 "${CLAUDE_SKILL_DIR}/scripts/backlinks.py" "$WIKI" <slug>

# Semantic, paraphrases of the stale claim
qmd query "old claim phrased in various ways"

# Exact token, numbers, codenames, specific quotes
grep -r "claim keyword" "$WIKI" --include="*.md"
```

Use all three. Backlinks catches structural references, qmd catches
paraphrases, grep catches literals. Miss any and you leave stale variants.

Don't update one page and leave stale variants. If the claim appears in:
- `entities/tricentis.md`
- `comparisons/test-automation-mq.md`
- `overview.md`

...all three need the update.

### 2. Show diff before writing

Present to user:

```
## Page: entities/tricentis.md
OLD:
  Pricing reported at $X per seat (source: 2025-08 analyst report).
NEW:
  Pricing reported at $Y per seat (source: raw/articles/tricentis-price-2026-03.md, 2026-03-15).

## Page: comparisons/test-automation-mq.md
OLD:
  Tricentis priced above Katalon.
NEW:
  Tricentis priced ~1.4x Katalon (from 2x per earlier note).
```

Confirm before writing. Mandatory for:
- Changes touching 5+ pages
- Changes to stated strategy or bets
- Changes contradicting prior user assertions

### 3. Cite the source in the page body

Every update lands with a citation inline or in a dated note block:

```markdown
## Pricing

As of 2026-03, ~1.4x Katalon enterprise SKU
(per [[raw/articles/tricentis-price-2026-03]]).

Previously (2025-08): 2x Katalon.
```

Don't overwrite old claims, preserve the history with dates when relevant
to understanding trends.

### 4. Stale-claim sweep

After updating the primary page, re-grep for variants:
- Phrase variations ("priced double", "2x pricing", "premium tier")
- Numeric variants ("$500", "$500/seat", "five hundred")
- Related claims that depended on the stale one

Fix all in the same pass. Don't leave landmines.

### 5. Bump dates everywhere

Every page touched → update `updated:` in frontmatter.

### 6. Handle contradictions and supersession explicitly

**Revision** (same page, refined info), stays in this Update flow. Bump
`updated:`, preserve history with dates, cite source.

**Supersession** (new page materially *replaces* old one), different flow:

```yaml
# new page frontmatter
supersedes: [old-slug]

# old page frontmatter
superseded_by: new-slug
```

Then:
- Archive old page to `_archive/`
- Run `lint.py --auto-fix` to rewrite inbound `[[old-slug]]` links
- Log: `## [YYYY-MM-DD] supersede | old-slug → new-slug`

If the new info doesn't cleanly supersede (e.g., conflicting sources, same date):

```yaml
---
title: Tricentis
contradictions: [tricentis-pricing-dispute]
---
```

Create or reference a concept page documenting the conflict. Flag in log.
Use `contradictions:` when both claims stand side-by-side.
Use `supersedes:` / `superseded_by:` when one claim replaces another.

### 7. Log unconditionally

```
## [2026-03-15] update | Tricentis pricing | source: raw/articles/tricentis-price-2026-03.md
- entities/tricentis.md
- comparisons/test-automation-mq.md
- overview.md
- Reason: new analyst report revised prior 2x claim to 1.4x
```

## Anti-patterns

- **Silent overwrite**: old claim deleted, no trace. Breaks trust.
- **Update one page, miss three**: wiki becomes internally inconsistent.
- **Uncited update**: nobody can verify 6 months later.
- **Batch update without diffs**: user can't catch over-corrections.
- **Update through Ingest flow**: loses the discipline. Use the right tool.

## Mass updates (10+ pages)

Always confirm scope first. Show the list:

```
This update will touch 14 pages:
  - entities/[12 competitor pages]
  - comparisons/test-automation-mq.md
  - overview.md

Proceed? (y/N/select subset)
```

Better to pause than to corrupt a third of the wiki in one batch.
