# Lint Guide

Lint runs programmatically via `scripts/lint.py` and writes a tiered report to
`wiki/queries/lint-YYYY-MM-DD.md`. Run every 5-10 ingests, or monthly.

## Severity Tiers

### 🔴 Errors — fix before next session

- **Broken `[[wikilinks]]`** — target page doesn't exist. Either create the
  target, fix the link, or remove it.
- **Missing frontmatter fields** — required: title, created, updated, type,
  tags, sources. Non-negotiable.
- **Tags not in SCHEMA.md taxonomy** — add to taxonomy first, or change the
  tag. No exceptions.

These block the wiki's search/navigation/discipline. Fix immediately.

### 🟡 Warnings — triage with user

- **Orphan pages** — zero inbound links. Either add backlinks from related
  pages, or archive if truly standalone. Borderline pages may just need
  cross-references.
- **Pages not in index.md** — index is the catalog. Add it or archive the page.
- **Pages > 200 lines** — split candidate. Break into sub-topics with cross-
  links. Big pages hide content.
- **Stale pages** — `updated:` > 90 days ago. Might be fine (stable facts)
  or might be out of date. Review.
- **Unresolved contradictions** — flagged in frontmatter but never closed.
  Revisit with latest info.

Discuss trends, not just individual items. If 30% of pages are stale, the
wiki isn't being maintained actively enough.

### 🔵 Info — quarterly review

- **Tag usage frequency** — top tags dominate the domain. Rarely-used tags
  may be candidates for consolidation or removal.
- **Singleton tags** (used once) — usually typos or impulsive additions.
  Consolidate into existing tags or justify and keep.
- **Log size** — rotate at 500 entries.

Not urgent. Save for quarterly taxonomy review.

## Response Workflow

After lint:

1. Open the generated report at `wiki/queries/lint-YYYY-MM-DD.md`
2. Fix all 🔴 errors in one pass. Re-run lint to confirm.
3. Scan 🟡 warnings. Flag 3-5 for user discussion. Batch similar fixes.
4. Note 🔵 info. Check back next quarter.
5. Update `overview.md` if the lint revealed drift in the synthesis.
## Auto-Fix Mode

```bash
python3 scripts/lint.py $WIKI --auto-fix
```

Safe repairs applied automatically:

- **Supersession link redirect** — rewrite `[[old-slug]]` → `[[new-slug]]` on
  every page where the old page has `superseded_by: new-slug` set
- **Broken link redirect** — if a broken link target has a supersession
  mapping, rewrite to the new target instead of erroring
- **Index backfill** — append missing non-superseded pages to `index.md`
  under the correct type section

NOT auto-fixed (requires human judgement):
- Missing frontmatter fields
- Tags not in taxonomy (typo vs new tag)
- Orphan pages (need backlinks or archival)
- Stale pages (fine vs out of date)
- Unresolved contradictions

Always re-run without `--auto-fix` after to confirm cleanup. Lint reports
themselves (`queries/lint-*.md`) are excluded from scans.

## Interpreting Trends

Run-over-run patterns matter more than single reports.

- **Orphans climbing** — ingest flow skipping backlink audit.
- **Broken links climbing** — pages being deleted/renamed without sweep.
- **Stale count climbing** — update discipline slipping, or domain expanding
  faster than curation.
- **Tag count sprawling** — taxonomy enforcement slipping.

Treat lint as the wiki's health dashboard, not a one-off cleanup.

## What lint doesn't catch

- Factual errors (requires domain knowledge)
- Missed cross-references (requires semantic understanding)
- Coverage gaps (what SHOULD exist but doesn't)
- Redundant pages on the same entity with different slugs

For these, periodic human review is required. Budget 30 min/quarter.
