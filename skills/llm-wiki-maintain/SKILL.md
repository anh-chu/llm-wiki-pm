---
name: llm-wiki-maintain
description: Orchestrates the recurring daily-maintenance loop for the PM wiki — registry-driven multi-source sweep, ingest, daily brief, brief rotation, and a health check — with explicit interactive-vs-autonomous mode handling.
when_to_use: Use for "daily maintenance", "run the daily wiki", "morning sweep", "ingest all sources and brief me", "do the daily run", "maintain the wiki", or any scheduled/autonomous run that should sweep all sources and produce a brief. For a brief alone use llm-wiki-brief; for a single ingest use core llm-wiki-pm.
allowed-tools: Read Grep Bash Edit Write
---

# LLM Wiki Maintain

The recurring maintenance loop, as one defined operation. "Every day: sweep all
sources → ingest what's new → produce a brief → keep the wiki tidy" was
previously improvised step-by-step on faith; this skill makes the order, the
brief lifecycle, and the autonomous-mode behavior explicit.

This skill **orchestrates** — it does not reimplement. The actual work is done
by the core `llm-wiki-pm` skill (orient, ingest, lint) and `llm-wiki-brief`
(brief generation). Route to them at each step. If a sub-skill isn't installed,
fall back to the core skill's matching operation.

## Mode: interactive vs autonomous (decide first)

The skill's proactive behaviors (ambient "want me to add that?", per-step
confirmations, post-task offers) assume a human is watching. In a scheduled or
autonomous run nobody answers them — they stall or force a guess. So classify
the run before doing anything:

- **Interactive** — a human invoked this in a live chat. Normal behavior:
  surface takeaways, ask before mass updates (10+ pages), offer follow-ups.
- **Autonomous** — a scheduled/cron/loop run with no human in the loop (no one
  to answer a prompt). Then:
  - **Suppress interactive prompts.** Do not ask "want me to add this?" or wait
    on confirmations. Act on the clear cases.
  - **Act-then-report, never block.** Anything that *would* need a human
    decision (a risky mass update, an ambiguous create-vs-update, a possible
    contradiction) goes into a **Needs Review** queue in the brief instead of
    halting the run.
  - **Stay within safe bounds.** Never delete or supersede without a human;
    queue those. Snapshot before any overwrite (core rule still applies).

If you can't tell which mode you're in, ask once ("interactive or autonomous
run?") and proceed on the answer; default to interactive.

## The loop (ordered)

① **Orient.** Run the core Pre-Flight + orient (SCHEMA, index, log, overview,
   `_status.md`). Do not skip — every write still requires orient.

② **Registry-driven sweep.** Read the `## Sweep Registry` in
   `$WIKI/MY-INTEGRATIONS.md` and sweep **every** source listed, under the core
   **Source-completeness guard** (≥2 varied queries, classify
   `hits`/`empty-after-retries`/`failed`, bound output — concise/limit≤15/narrow
   scope first). One batch sweep up front satisfies freshness-first for the whole
   run (see the Freshness↔batch rule); do NOT re-sweep per page. If no registry
   exists, build it from connected tools + `Active Sources`, confirm (interactive)
   or queue for review (autonomous), and write it before sweeping.

③ **Ingest findings.** For each new/changed signal, route to the core ingest
   flow (capture raw → thresholds → write/update → backlinks → log →
   MY-INTEGRATIONS). Pages are private by default; never mark a digest
   `shareable`. Stamp `lifecycle: stub-intentional` on by-design thin stubs.

④ **Daily brief.** Route to `llm-wiki-brief` (daily brief). If filing it as a
   page, write `briefings/YYYY-MM-DD.md` with `lifecycle: dated-digest` (keeps
   it out of the orphan count). The brief MUST include the Source Coverage
   ledger (one row per registered source) and, in autonomous mode, a **Needs
   Review** section.

⑤ **Brief rotation.** Keep the last 7 days in `briefings/`; move older briefs to
   `_archive/briefings/`. Use `git mv` if the file is tracked, plain `mv` if not
   (check first — don't let an untracked file abort the run).

⑥ **Health check.** Run `scripts/lint.py $WIKI`. Surface the tiered summary,
   the export-surface (shareable) audit, and any new orphans/broken links.
   Optionally `lint.py $WIKI --auto-fix` to backfill+sort the index (interactive:
   offer it; autonomous: run it — it's non-destructive).

⑦ **Report.** One consolidated summary: sweep coverage ledger, pages
   created/updated, brief link, lint health delta, and the Needs Review queue.

## Brief lifecycle convention

- `briefings/YYYY-MM-DD.md` — current briefs, `lifecycle: dated-digest`.
- `_archive/briefings/` — briefs older than 7 days.
- Briefs are orphans by design; the `dated-digest` flag keeps them out of lint's
  orphan count. Never link-spam pages just to de-orphan a brief.

## What this skill does NOT do

Single ingests, ad-hoc queries, updates, persona/PRD/research/CRM work — route
to the core skill or the matching sub-skill. This skill is the daily loop only.
