# Privacy Guide

PM sources contain sensitive material: customer names, deal sizes, churn
risks, internal strategy, 1:1 conversations. The wiki holds all of this long-
term. Treat privacy as a first-class concern, not an afterthought.

## Two Levers

1. **Filter on ingest** — what never makes it into `raw/` can't leak
2. **`private: true` frontmatter** — what's in the wiki but excluded from exports

## Pre-Ingest Checklist

Before saving any source to `raw/`:

- [ ] Strip API keys, tokens, passwords, credentials — always
- [ ] Strip customer employee emails/phones unless publicly known — usually
- [ ] Redact specific deal dollar amounts if unnecessary for the point
- [ ] Remove or pseudonymize quotes attributed to named individuals if sensitive
- [ ] Check for accidental paste of internal Slack messages with unintended context

If you're unsure, err on stripping. Raw sources are immutable once filed.

## Private Frontmatter Flag

```yaml
---
title: Customer Foo Renewal Risk
private: true
---
```

Pages with `private: true`:
- Stay in the wiki and are used by the agent normally
- Are excluded from any export/share operation
- Are not sent to third-party tools that receive the wiki
- Should be the default for: customer-specific pages, 1:1 summaries,
  named-employee conduct notes, unreleased roadmap/pricing

## What Should Be Private by Default

Always `private: true`:
- Specific customer account pages with revenue/churn signals
- 1:1 transcripts and crystallized digests
- Named-employee performance/conduct notes
- Pre-release pricing changes
- Internal competitive moves (undisclosed acquisitions, hiring plans)
- Any page with `type: query` derived from private sources

Usually public (`private: false` or omitted):
- Competitor pages built from public analyst reports
- Market analysis from published sources
- Concept pages (frameworks, themes) without customer PII
- General strategy notes not tied to specific people/accounts

## Obfuscation Patterns

If a page must be referenced widely but contains sensitive specifics:

**Codename customers:**
```markdown
## Customer Alpha (real: <private-reference>)
- Sector: financial services
- Seats: ~500
- Risk: medium
```

Keep the real mapping in a separate `_private/mappings.md` with `private: true`.
Reference the codename in public pages.

**Redact numbers:**
```markdown
- ARR: $X (mid 6 figures)
- Renewal: Q3 2026
```

## When a Source is Fully Sensitive

If the entire raw source shouldn't exist on the wiki at all (e.g., legally
privileged material, pre-acquisition targets):

- Don't ingest. Keep the source outside the wiki entirely.
- If key facts must be captured, hand-write them into a `private: true` page
  with no source link.

## Exports and Shares

When exporting wiki subsets (to share with a teammate, post in a doc, move
to another system):

```bash
# Find private pages before any export
grep -rl "^private: true" $WIKI --include="*.md"
```

Review the list. Remove private pages from the export. Double-check the
export for codenames vs real names.

## Audit

Every quarter, grep the wiki for common PII patterns:

```bash
# emails
grep -rEn "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}" $WIKI --include="*.md"
# phone numbers (US format)
grep -rEn "\b[0-9]{3}[-.][0-9]{3}[-.][0-9]{4}\b" $WIKI --include="*.md"
```

Review hits. Either redact, pseudonymize, or mark the page private.
