# llm-wiki-pm feedback — from wiki-claude-code (daily-maintenance sessions)

Re: ask #ask-271df1c5. v2.14.0 source-depth guard + harness-hook precedence fixes confirmed good. Caveman-hook precedence held this session — natural prose in pages, terse only in chat.

Additional pain points below, ranked.

## 1. Slack search overflow (highest impact)
Broad `slack_search_public_and_private` returned 107K chars, blew the token cap, dumped to a file I then had to slice by char range. Skill gives zero guidance on bounding connected-tool output.
**Fix:** Tool Selection Hierarchy note — default `response_format=concise`, `include_context=false`, `limit<=15`, narrow channel/author scope FIRST before broad keyword. Bound output on every connected-tool sweep.

## 2. Soft date filters on semantic search
Slack `after:`/`before:` are NOT honored by semantic ranking — an `after:2026-06-17` query returned March/April messages. Source-completeness guard tells me to vary queries but never warns that date operators are advisory on semantic backends. Wasted a cycle separating in-window hits from relevance matches.
**Fix:** "Verify each result's actual date; treat date operators as soft on semantic-search backends."

## 3. Stub lifecycle / orphan pollution
Created 7 intentional stubs (6 ARR accounts + Nicus); orphan count jumped 5→14 and lint flags them as orphans/oversight. No way to mark "intentional stub, low coverage, awaiting signal."
**Fix:** frontmatter flag (e.g. `lifecycle: stub-intentional`) that lint respects, OR auto-exempt from orphan check when `coverage: stub` + <2 backlinks is by-design. Current health metrics punish correct behavior.

## 4. Confidence vs coverage conflation
Warehouse-sourced pages are hard FACT (direct from source DB) but have zero engagement context. Forced to mark `confidence: likely` + `coverage: stub`, which reads as "shaky" when the data is authoritative. The two axes (source reliability vs completeness) collapse badly here.
**Fix:** schema-guide should explicitly separate them, with this case: a page can be verified-fact + stub-coverage.

## 5. Stale _status.md mid-session
Computed at SessionStart, never refreshes. After creating 8 pages the orphan/stale counts were wrong for the rest of a long session; can't trust it post-ingest.
**Fix:** cheap "recompute status" after writes, OR skill note that `_status.md` is session-start-only.

## 6. Index maintenance manual + unordered
Every new page = hand-edit into the right `index.md` section; no alpha-sort enforced (I appended out of order). Entities section is now ~55 unsorted lines. Lint flags index drift but doesn't fix it.
**Fix:** `lint --auto-fix` should backfill index entries (alpha order, correct section).

## 7. Daily-brief archive is manual git mv
Every sweep I manually move yesterday's brief to `_archive/briefings/`. Rote.
**Fix:** brief-rotation helper — keep N days in `briefings/`, auto-archive older.

## 8. No DB/warehouse ingest pattern
Metabase/warehouse is a first-class source for me (ARR, usage, activation) but `ingest-guide.md` only contemplates web/Slack/Gmail/transcripts. No provenance convention for SQL-sourced facts — I improvised (query + snapshot id inline, e.g. `month_id=202606`).
**Fix:** recommended-tools entry + ingest pattern for warehouse sources (cite query + snapshot id as provenance).
