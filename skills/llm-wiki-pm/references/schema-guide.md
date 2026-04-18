# Schema Guide

SCHEMA.md governs the wiki. Customize it upfront. Revisit quarterly.

## When to edit SCHEMA.md

- Starting a new domain or sub-domain
- Adding a new tag (do this BEFORE using the tag)
- Adjusting page thresholds (too many trivial pages? raise the bar)
- Changing frontmatter requirements
- Updating the update policy

## Tag taxonomy discipline

Rule: every tag on any page must exist in SCHEMA.md.

Workflow when you want a new tag:
1. Stop. Edit SCHEMA.md. Add the tag under the right section with a one-line gloss.
2. Commit / save SCHEMA.md.
3. Now use the tag.

Why: freeform tags decay. After 6 months you have `ai`, `AI`, `ai-tools`,
`aitools`, `artificialintelligence` — all slightly different, all unsearchable.
Enforced taxonomy prevents this.

## Page threshold tuning

Default: create a page when an entity appears in 2+ sources OR is central to one.

Signals to raise the bar (fewer pages):
- Lint reports 40%+ orphans
- You can't remember what half the entity pages are for
- You're creating pages for competitors mentioned once in a footnote

Signals to lower the bar (more pages):
- You keep re-reading raw sources because info isn't filed
- Queries return nothing because the entity isn't a page
- Important people don't have pages yet

## Frontmatter extensions

Add fields for PM-specific signals:

```yaml
relevance: high | medium | low    # How much this matters to our strategy
last_reviewed: YYYY-MM-DD         # When a human last eyeballed it
owner: anh | vu | data-team       # Who owns verifying this
confidence: verified | likely | rumor
```

Add these to the "Frontmatter" section in SCHEMA.md when you adopt them.

## Domain pivots

If scope shifts (e.g., TruePlatform becomes the whole company focus):
1. Update `## Domain` in SCHEMA.md
2. Run lint to identify now-out-of-scope pages
3. Archive or re-tag as needed
4. Update tag taxonomy — prune dead categories
5. Refresh `overview.md`
