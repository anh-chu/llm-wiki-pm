---
title: My Integrations
updated: YYYY-MM-DD
---

# My Integrations

Sources used in this wiki, auto-discovered from ingest activity. The Active Sources
table is auto-maintained by the skill after each ingest. The Routing Notes section
below is user-editable — add preferences there, not in the table.

## Sweep Registry

Canonical list of sources a full "ingest all sources" / daily-brief sweep MUST
cover. This — not the agent's memory — defines what "all sources" means; the
sweep iterates every row and reports state (`hits` / `empty-after-retries` /
`failed`) for each. Established/confirmed the first time a multi-source sweep
runs; edit freely to add or retire sources. A source missing here is a source
that will be silently skipped, so keep it complete.

| Source | Sweep? | How to query | Notes |
|--------|--------|--------------|-------|
<!-- e.g.: | Slack | yes | search #product-strategy, to:me, <@mentions> | most active |
     e.g.: | GitHub | yes | issues assigned/mentioning me, recent PRs | high signal |
     e.g.: | Gmail | yes | PM/ label, last 2 days | | -->

## Active Sources

| Source | Type | Last used | Times ingested | Notes |
|--------|------|-----------|----------------|-------|
<!-- rows appended by skill on each ingest -->

## Routing Notes

Add any routing preferences here — the skill reads this file at Pre-Flight to
tailor ingest defaults (e.g., preferred Slack channel naming, Gmail label patterns).

```
# Example entries (fill in after first few ingests):
# slack_workspace: your-workspace.slack.com
# gmail_label_filter: PM/
# preferred_transcript_format: zoom | meet | otter
```
