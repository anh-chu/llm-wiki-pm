# Privacy Guide

PM sources contain sensitive material: customer names, deal sizes, churn
risks, internal strategy, 1:1 conversations. The wiki holds all of this long-
term. Treat privacy as a first-class concern, not an afterthought.

## Two Levers

1. **Filter on ingest**: what never makes it into `raw/` can't leak
2. **Private-by-default exports (allowlist)**: every page is private and excluded
   from exports/shares unless it explicitly carries `shareable: true`

> **Model: private by default.** The old `private: true` flag collapsed into
> always-on — nearly every internal PM page qualified, so the flag stopped
> carrying signal and couldn't drive export decisions. The model is now
> inverted: pages are private unless marked `shareable: true`. The rare positive
> flag is the meaningful one, and a forgotten flag fails safe (stays private)
> instead of leaking. `private: true` is deprecated; you no longer need to set
> it (it's the default), and it is treated as "not shareable" for back-compat.

## Pre-Ingest Checklist

Before saving any source to `raw/`:

- [ ] Strip API keys, tokens, passwords, credentials, always
- [ ] Strip customer employee emails/phones unless publicly known, usually
- [ ] Redact specific deal dollar amounts if unnecessary for the point
- [ ] Remove or pseudonymize quotes attributed to named individuals if sensitive
- [ ] Check for accidental paste of internal Slack messages with unintended context

If you're unsure, err on stripping. Raw sources are immutable once filed.

## The `shareable` Flag

```yaml
---
title: Gartner Test Automation MQ 2026
shareable: true
---
```

Default (no flag) = private:
- Stays in the wiki and is used by the agent normally
- Excluded from any export/share operation
- Not sent to third-party tools that receive the wiki

`shareable: true` opts a page INTO exports. Set it only when the page is
genuinely safe to share externally.

## What May Be `shareable: true`

Only pages with no sensitive content — typically:
- Competitor pages built from public analyst reports
- Market analysis from published sources
- Concept pages (frameworks, themes) without customer PII
- General strategy notes not tied to specific people/accounts

Leave everything else unflagged (private). That includes — and these must NEVER
get `shareable: true`:
- Specific customer account pages with revenue/churn signals
- 1:1 transcripts and crystallized digests
- Named-employee performance/conduct notes
- Pre-release pricing changes
- Internal competitive moves (undisclosed acquisitions, hiring plans)
- Any page with `type: query` derived from private sources

## Obfuscation Patterns

If a page must be referenced widely but contains sensitive specifics:

**Codename customers:**
```markdown
## Customer Alpha (real: <private-reference>)
- Sector: financial services
- Seats: ~500
- Risk: medium
```

Keep the real mapping in a separate `_private/mappings.md` (private by default —
never make it shareable). Reference the codename in public pages.

**Redact numbers:**
```markdown
- ARR: $X (mid 6 figures)
- Renewal: Q3 2026
```

## When a Source is Fully Sensitive

If the entire raw source shouldn't exist on the wiki at all (e.g., legally
privileged material, pre-acquisition targets):

- Don't ingest. Keep the source outside the wiki entirely.
- If key facts must be captured, hand-write them into an unflagged (private)
  page with no source link.

## Exports and Shares

When exporting wiki subsets (to share with a teammate, post in a doc, move
to another system), export ONLY the allowlist:

```bash
# The export set = pages explicitly marked shareable. Everything else stays private.
grep -rl "^shareable: true" $WIKI --include="*.md"
```

Export only those pages. Anything not on this list is private by default and
must be left out. Double-check the shareable set for codenames vs real names
before it leaves your machine.

## Audit

Every quarter, grep the wiki for common PII patterns:

```bash
# emails
grep -rEn "[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}" $WIKI --include="*.md"
# phone numbers (US format)
grep -rEn "\b[0-9]{3}[-.][0-9]{3}[-.][0-9]{4}\b" $WIKI --include="*.md"
```

Review hits. Either redact, pseudonymize, or ensure the page is not `shareable`
(unflagged pages are already private).
