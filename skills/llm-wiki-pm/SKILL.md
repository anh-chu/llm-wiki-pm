---
name: llm-wiki-pm
description: Persistent PM knowledge base, competitive intel, customer notes, strategy, roadmap, AI market. Markdown wiki with entities, concepts, comparisons. Ingest sources, query, update with diffs, lint. Fires on "remember that / note that / don't forget / what do we know about X / what am I missing / blind spots".
when_to_use: Use when user wants to ingest a source, query the wiki, update pages, lint/audit, bootstrap a new wiki, audit coverage gaps, capture learnings, or says "remember that / note that / don't forget / what am I missing / blind spots". For briefs/digests use llm-wiki-brief; for research sprints/deep dives use llm-wiki-research; for the daily-maintenance loop (sweep all sources → ingest → brief → tidy, incl. scheduled runs) use llm-wiki-maintain.
allowed-tools: Read Grep Write Edit Bash WebFetch
---

# LLM Wiki PM

Persistent knowledge base for PM work. Non-coding. Domain: product strategy,
competitive landscape, customer relations, roadmap, AI market, internal org.

Markdown files in a directory. Readable in Obsidian, VS Code, any editor.
The agent writes. You curate sources, ask questions, steer.

## When This Skill Activates
- User asks a question about PM knowledge, competitive intel, customers, strategy, or roadmap
- User asks to update/revise a page, or to lint/audit/health-check the wiki
- User asks to create or bootstrap a PM wiki, or references "my wiki / knowledge base / notes"
- **Natural memory phrases**: "remember that", "note that", "don't forget", "keep
  in mind", "save this", "log this", "make a note", "record that" → treat as a
  wiki ingest (see §2 micro-capture fast path). Ask which page if unclear.
- "I have a meeting/call/1:1 with [person]" → §9 Pre-Meeting Briefing
- "What happened this week / recently?" → §10 Catch Me Up
- "[tag] digest" / "catch me up on [topic]" → §11 Tag Digest
- "What am I missing?", "blind spots?", "coverage gaps?" → §12 Coverage Audit
- "What did we learn?", "capture learnings" → §13 Learn
- After a substantive PM task, Proactive Behavior B offers to capture learnings

## Sub-skills (route to these)

Route to these — including **mid-flow** when a core operation surfaces the need:

| Need | Sub-skill | Triggers |
|------|-----------|----------|
| Daily/weekly briefs, tag digests, coverage briefs | `llm-wiki-brief` | "daily/weekly brief", "catch me up", "[tag] digest" |
| Research sprints, competitive deep dives, stub enrichment | `llm-wiki-research` | "research [topic]", "deep dive", "auto-research [entity]" |
| Daily-maintenance loop (sweep all sources → ingest → brief → tidy), incl. scheduled runs | `llm-wiki-maintain` | "daily maintenance", "morning sweep", "ingest all sources and brief", "do the daily run" |
| Independent review of any wiki-based answer or write, before reporting | `llm-wiki-review` | every answer or page built from the wiki; the review-gate Stop hook enforces it; skipped on "no review" |

If a sub-skill isn't installed, the core skill's matching fallback handles it where
one exists (§10/§11/§12); research and maintain require their
sub-skill (you can still run maintenance steps manually via core ingest/brief/lint).

## Proactive Behaviors

Fire whenever the skill is loaded. Append notes briefly *after* your answer, never
before. Searches: wiki-search `search_text` preferred, grep fallback.
**Limits:** max 1 suggestion per turn; skip during code/debug tasks; PM-domain
facts not already addressed. Writes follow **Maintain by default** (Session
Defaults): don't ask "want me to update the wiki?" for a case it covers.

**A. Entity-aware recall & contradiction.** When the user mentions a named
company/person/product (not just in passing), search the wiki; if a page exists,
surface it in one line with its `confidence:`/`coverage:` and `updated:` date.
Always flag `rumor` confidence: "Wiki has [[page]] (rumor, unverified). Treat with
caution." If the user's statement conflicts with the page, note it: "This may
conflict with [[page]] from YYYY-MM-DD. Which is current?" For a named person,
fold in 1-2 relevant traits from `entities/<name>-persona.md` if present.

**B. Capture (facts, decisions, open questions, stale pages).** When the user
states a wikifiable PM fact or a decision ("we decided", "going with X"), when a
check this session proves a page stale or wrong, or when a factual question has no
answer in the wiki, capture it — *after* a mandatory **dedup search** of the key
noun phrases. If a page already holds the claim, update it; don't duplicate.
Decisions → a `decision`-tagged page (who, when, rationale). Unanswerable questions
→ a `question`-tagged page under `queries/`. After a substantive PM task (research,
ingest, briefing, strategy), self-audit once for uncaptured items and run §13
Learn. Report in one line after the answer: "Wiki: updated [[page]] (what changed,
source)". Skip casual chat, hypotheticals, and anything already captured.

*(Tool-discovery suggestions live in `references/recommended-tools.md` — surface
one only when a query would clearly be richer with an unconnected tool.)*

## Wiki Location
Before any bash command using `$WIKI`, resolve it:
```bash
WIKI=$(cat .wiki-path 2>/dev/null | tr -d '[:space:]')
CONF='${user_config.wiki_path}'; case "$CONF" in '${'*) CONF= ;; esac  # plugin option, if set
WIKI=${WIKI:-${CONF:-${WIKI_PATH:-}}}
[ -z "$WIKI" ] && [ -f SCHEMA.md ] && WIKI=$(pwd)  # cwd only if it is already a wiki
```
Resolution: `.wiki-path` (project) → the plugin's `wiki_path` option (global) →
`WIKI_PATH` → cwd, but only if cwd already is a wiki (has `SCHEMA.md`). If `WIKI`
is empty, stop and tell the user to run `/llm-wiki-pm:set-wiki-path ~/path`.
The SessionStart hook states the active path each session.

## Session Defaults

**Wiki-first protocol:** Before answering a PM knowledge question, search the wiki
with connected tools. Don't synthesize from training data when wiki pages exist.
Cite explicitly: "Per [[page]]...". If no page exists, say so, then create one if
it meets the thresholds or log an open question. Before asking the user a fact about people, teams,
ownership, customers, roadmap or process, search the wiki first, including during
code or GitHub work.

**Source discipline (the wiki is a map, not the territory):** wiki-first must not
become wiki-only. Verify from source; use the wiki to know where to look. Four
guards govern this — the full detail and rationale are in
`references/source-discipline.md` (read it before a substantive ingest, a
multi-source sweep, or any decision-bearing/exec-facing synthesis). The input side
is largely enforced by the `pre-write.sh` freshness gate and `lint.py`
(self-referential sourcing, missing inline provenance). In brief:

- **Freshness-first guard.** Before writing/updating a page, sweep connected tools
  for newer primary sources and anchor claims with inline `[source:]` markers;
  don't build a page from other pages' prose. One batch sweep covers a batch
  operation. Distinguish "wiki says X (as of date)" from "live sources confirm X today".
- **Source-completeness guard.** For any multi-source sweep, enumerate the
  **canonical sweep registry** in `$WIKI/MY-INTEGRATIONS.md` (`## Sweep Registry`)
  and cover every source. Empty ≠ done: run ≥2 varied queries, then classify each
  source `hits` / `empty-after-retries` / `failed` and report all three — never
  collapse `failed`/`empty-after-retries` into "covered."
- **Source-depth guard.** A hit that *references* an artifact (attached file,
  linked doc, cited spec) is not the content. Open it before synthesizing; if you
  can't, flag it unread and don't write over it.
- **Provenance-tier & falsification guard.** Tier every asserted claim
  `computed` / `primary` / `recalled`; never state a recalled claim as fact in a
  decision-bearing answer without upgrading it against a primary source. Route
  targeting/pipeline/quantitative questions to the primary system (CRM, warehouse,
  Gong), not wiki prose. Before exec-facing synthesis, run a falsification pass:
  name and run the query that would disprove each headline claim.
- **Check, don't offer.** A wiki page is a lead, not proof. Before stating a fact
  about status, dates, people, numbers or absence, run the read-only check that
  settles it when it is a call or two away, using the user's rules in
  `$WIKI/MY-INTEGRATIONS.md` → `## Claim Checks` (the prompt-recall hook adds the
  rules that match each prompt). Before you send, reread your "not checked" list:
  run every item that is a read-only call away and drop it from the list. Offer a
  check instead of running it only when access is blocked or it is costly, and
  say which. A claim that nothing exists
  ("no reply", "not shipped", "no activity") needs coverage: two query forms, every
  page and thread read, window and identity checked; otherwise say "not found in
  <searches run>". When the user has to ask for a check or corrects a fact, fix the
  claim first; add a Claim Checks rule only when the same failure repeats, and report it.

**Maintain by default; report after.** The wiki evolves through use, so keep it
current without asking. Write when a primary source read this session, or the
user's own statement, supports the change: new facts, stale or wrong claims (and
their variants on other pages), decisions, open questions, pages that meet the
thresholds, links and the index. Then report every page changed (what, source).
Ask first only when a write would: change a stated strategy, bet or earlier
decision; contradict the user with no primary source to settle it; delete,
archive or supersede a page; touch 10+ pages; or add `shareable: true`. Never write
a claim whose only support is wiki prose or memory; log it as a gap. If your answer
would call a page stale or wrong and you hold the primary source, fix the page
before you send; don't just report it. Dated records (briefs, `log.md`, `raw/`,
`_archive/`) stay as written. Snapshots (pre-write hook), `log.md` and the report
make every write easy to undo.

**Session trust model:** Trust `.wiki-path` for location, `SCHEMA.md` for taxonomy
(new tags go there first), `log.md` for recent activity. Deviate only with explicit
user confirmation.

## Tool Selection Hierarchy

Inventory every connected MCP tool at session start and use them eagerly.

| Priority | Tools | When |
|----------|-------|------|
| 1 | **wiki-search** (bundled) — BM25 keyword, regex, tag and link search over wiki | Wiki queries, entity lookup, recall |
| 2 | **MCP integrations** — Gmail, Slack, calendar, CRM, any connected MCP | Emails, threads, messages, events, enriching pages |
| 3 | **WebFetch / WebSearch** | External research, fetching pages for ingest |
| 4 | **grep** | Exact token match (dollar figures, codenames, frontmatter values) |
| 5 | **Read** | When you already know the exact file |

**wiki-search tools** (bundled [obsidian-mcp](https://github.com/lstpsche/obsidian-mcp),
read-only): `search_text` (ranked BM25; pass 2-6 distinctive terms, not a
sentence; it matches words, not meaning, so retry with synonyms), `search_regex`
(exact tokens, numbers, codenames, or a tag or frontmatter value such as
`tags:.*competitive`), `wikilinks` (backlinks, outgoing, broken, orphans),
`note_read`. They are loaded at session start, so use them before grep for wiki
lookups. Results come back trimmed to a few snippets per file; `note_read` the
hits you need. `_archive/` snapshots are left out of
search and backlinks (read them by path when you need history). Optional key-required tools:
`references/recommended-tools.md`.

**Rules:**
- **Connected tools first, file reads last.** Search before read; don't scan files sequentially.
- **Bound connected-tool output.** Broad chat/email/warehouse searches can return
  100K+ chars. Default to the tightest useful query: summary format, no message
  context, `limit`≤15, and **narrow scope (channel/author/label/date) BEFORE broad
  keyword**. Widen only if the narrow pass is empty. Dump-then-slice is a defect.
- **Date operators are soft on search backends.** Many treat `after:`/`before:`
  as advisory — verify each result's actual timestamp before trusting it as in-window.

## Architecture: Three Layers

`raw/` (Layer 1, immutable sources — agent reads, never modifies) → `entities/`,
`concepts/`, `comparisons/`, `queries/` (Layer 2, agent-owned pages) governed by
`SCHEMA.md` (Layer 3, taxonomy). Plus `index.md` (catalog), `overview.md`
(synthesis), `log.md` (append-only action log), `_status.md` (session-start health),
`_archive/` (snapshots + superseded). Full directory layout and `raw/` sub-routing:
`references/ingest-guide.md` and `references/schema-guide.md`.

## Pre-Flight Check

Run at session start before any operation. Proceed silently if all pass; narrate
only on a problem.

**① Wiki exists?** Resolve `$WIKI` (see Wiki Location); if the dir is missing:
"Wiki directory not found. Scaffold a new wiki or run `/llm-wiki-pm:set-wiki-path`."
**② SCHEMA.md exists?** If absent, offer to scaffold from `templates/SCHEMA.md`. No
write operation proceeds until it exists.
**③ MY-INTEGRATIONS.md (optional).** If present, apply its Routing Notes to ingest
defaults and read `## Sweep Registry` (canonical source list). No file = generic
defaults. Never create it during Pre-Flight (auto-created on first ingest).
**④ _status.md warnings.** If present, read it and surface staleness/lock warnings.

## Orient Every Session

Before any ingest/query/update/lint:

① Read `SCHEMA.md` — domain, conventions, tag taxonomy
② Read `index.md` — what pages exist
③ Read last 20-30 lines of `log.md` — recent activity
④ Read `overview.md` — current synthesis state
⑤ For 100+ page wikis: search before creating (`search_text` or `grep -r`)
⑥ **Staleness warning:** if a page's `updated:` is older than 14 days
   (overview/index) or 30 days (entity/concept) AND `log.md` shows recent activity
   in that area, surface: "Warning: [[page]] may be stale (updated YYYY-MM-DD)."
⑦ **_status.md warnings** were surfaced in Pre-Flight ④; if Pre-Flight was skipped,
   read `$WIKI/_status.md` now. It also precomputes confidence-decay candidates.
⑧ **Orient gate (checklist):** before creating or modifying any wiki page, ensure
   ①-④ are done this session. If not: "Need to orient first. Running now." Then
   orient. Narrow read-only queries answerable from a single page read may skip it.

Skipping orientation → duplicate pages, missed cross-refs, schema drift.
(Bash-heavy orient/lint reads are required correctness work — a session hook that
caps raw output does not exempt you; route bulk through the hook's preferred path.
This skill's correctness and tone rules govern wiki work; see
`references/lint-guide.md` for harness-hook precedence detail.)

## Core Operations

### 1. Initialize (new wiki)
The SessionStart hook scaffolds the wiki automatically on first run (directory
structure + templates, using the domain set at plugin-enable). If it wasn't
auto-created, restart the session. After init, confirm domain scope and customize
`SCHEMA.md` taxonomy.

### 2. Ingest a source

**Micro-capture fast path** — for a SINGLE conversational fact ("remember that…",
a decision dropped in chat; `source: conversation | <date>`): skip the
ingest-guide read, crystallize, entity-promotion scan, and per-op freshness sweep.
Do exactly one mandatory step — a **dedup search** of the key noun (append to the
existing page, else create a small stub with frontmatter + ≥2 links) — then log it.
Still requires Orient once this session. Anything that is a file/URL/transcript/
warehouse/email/chat export, or a batch, uses the full flow below.

**Full ingest — read `references/ingest-guide.md` first** (raw-capture conventions,
page thresholds, inline provenance, privacy filter, crystallize, entity-promotion).
In brief:
① **Capture raw** to `raw/` (immutable), behind the privacy filter. Pages are
   private by default; add `shareable: true` only to genuinely public-safe pages.
② **Note takeaways** for the report; don't stop to wait for a reply.
③ **Check existing pages** — decide create vs update.
④ **Apply page thresholds** (2+ sources or central) and **enrich from connected
   tools BEFORE writing** (Freshness-first) — never build a page from other pages' prose.
⑤ **Write/update** with required frontmatter, taxonomy tags, ≥2 `[[wikilinks]]`,
   inline `[source: ...]` markers, and `coverage:`/`gaps:`/`confidence:` set.
⑥–⑧ Backlink audit; refresh `overview.md` if synthesis shifts; update `index.md`;
   append the `ingest` entry to `log.md` listing every file touched.
⑨ Log the source row in `MY-INTEGRATIONS.md`.
⑩ Report every file touched; confirm before mass-updating (10+ pages).
⑪ **Crystallize** transcripts/research chains into a `queries/` digest (`references/crystallize-guide.md`).
⑫ **Entity promotion scan** — promote people/companies/products with 3+ attributes
   to their own page, and report it.

### 3. Query
① **Search first**: `search_text` → `search_regex`/grep → file read.
② Read `index.md` to confirm the catalog for top hits.
③ Read relevant pages (only after search identified them).
④ Synthesize; cite pages: "Per [[competitor-x]] and [[test-automation-mq]]...". **For
   a decision-bearing or exec-facing answer, run the falsification pass first**
   (Session Defaults → Source discipline → Provenance-tier guard): tier each claim,
   upgrade recalled claims against a primary source, and route
   targeting/pipeline/quantitative questions to the primary system (CRM, warehouse,
   Gong), not wiki prose. For a casual lookup, cite pages and answer. **Then run
   `llm-wiki-review` on the draft before you send it**, casual lookups included: a
   wrong "who asked for what, when" is the costliest wiki error.
⑤ **Select output format**: inline markdown for most; a `queries/<slug>/<slug>.md`
   page for substantial syntheses; add artifacts (Marp/matplotlib/CSV/Mermaid) when
   warranted (`references/output-formats.md`).
⑥ **File valuable answers back** (substantial comparisons, deep dives, novel
   synthesis); skip trivial lookups.
⑦ Append to `log.md`: `## [YYYY-MM-DD] query | <question> (filed: yes/no)`.

### 4. Update (revise existing pages)

Separate discipline from ingest — triggered when new info conflicts with or refines
existing content. **Pre-update snapshot is automatic:** the `pre-write.sh` hook
copies the current page to `_archive/<slug>-<date>.md` before an overwrite
(idempotent, once/day), so "undo that last change" stays trivial.

① **Identify all affected pages** — three-way search: `backlinks.py` (structural),
   `search_text` with rephrased terms (paraphrases), `grep -r` (exact tokens). Don't
   fix one page and leave three with the stale claim.
② **Write, then report the diff**: per page, old text, new text and source, after
   the answer. Ask first only for the cases in **Maintain by default** (strategy,
   contradicting the user without a source, delete/supersede, 10+ pages, shareable).
③ **Cite source**: every update names the raw source justifying it, in the body and log.
④ **Stale-claim sweep**: after the update, re-search and fix all instances in the same pass.
⑤ **Bump `updated:`** on every page touched.
⑥ **Log**: `## [YYYY-MM-DD] update | <claim/page> | source: raw/...`, listing every file.
⑦ **Write verification**: re-read after writing; if frontmatter is malformed or the
   write failed, surface the error and do NOT update index.md or log.md.
⑧ **Inline provenance on updates**: update the `[source: ...]` marker on the changed
   claim; don't leave old markers on revised facts.

### 5. Lint (tiered report)
```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/lint.py "$WIKI"
```
Writes `queries/lint-YYYY-MM-DD.md` with severity tiers: 🔴 (broken links,
missing/invalid frontmatter, off-taxonomy tags, self-referential factual/decision
pages), 🟡 (orphans, index drift, oversized/stale pages, missing coverage markers,
unresolved contradictions), 🟠 (stale overview/index with recent log activity), 🔵
(tag frequency, log rotation). Act on 🔴, investigate 🟠, discuss 🟡, note 🔵. Full
checklist: `references/lint-guide.md`. `--auto-fix` repairs safe issues
(supersession redirects, index backfill/sort).

### 6. Archive
Superseded/out-of-scope content: move to `_archive/` preserving path; remove from
`index.md`; replace inbound `[[old]]` links with plain text "(archived)"; log with reason.

### 7. Staleness Check
Run on "is the wiki up to date?" or after a gap (also runs in orient ⑥). Scan
`updated:` across entities/concepts/comparisons/overview/index (thresholds: 14 days
overview/index, 30 entity/concept). Cross-reference `log.md` — a page with recent
activity but an unmoved `updated:` is behind; flag those first. Offer the Update
flow (§4). Log the check regardless.

### 8. Persona Pages
Existing `<name>-persona.md` pages stay valid (type `persona` in SCHEMA.md). Put new
communication notes on the person's entity page, quoting real messages; never invent
traits.

### 9. Pre-Meeting Briefing
Trigger: "I have a meeting/1:1 with X". Read the entity page + persona if present;
pull `concepts/relationship-map.md`; read the last 5 `log.md` entries mentioning X;
grep open `question`-tagged pages. Synthesize: **Who** / **What we know** / **Recent
activity** / **Open questions** / **Communication tips**. Log: `## [date] brief | X | pre-meeting`.

### 10. Catch Me Up
`llm-wiki-brief` handles this richer — route there when installed. Fallback: read
`log.md` for the last N days (default 7), list new/updated pages, decisions, open
questions; surface `_status.md` warnings and the 2-3 most active areas. Log:
`## [date] catchup | last N days | X actions`.

### 11. Tag Digest
`llm-wiki-brief` handles this richer — route there when installed. Fallback: grep
frontmatter for the tag → read matches newest-first → synthesize (key players,
recent changes, open questions, patterns) → file it as a query page. Log:
`## [date] digest | tag: <tag> | X pages`.

### 12. Coverage Audit
Trigger: "what am I missing?", "blind spots?", "coverage gaps?". (`llm-wiki-brief`
Coverage Brief is richer.) Scan `coverage:` across entities/concepts/comparisons
(count stub/partial/comprehensive); collect `gaps:`; read open `question` pages;
any entity in 3+ pages without its own page is a gap; create stubs for them. Log:
`## [date] coverage-audit | stubs: N | gaps: N | open-questions: N`.

### 13. Learn (Post-Task Capture)
Trigger: the self-audit after a substantive task (Proactive Behavior B), or "capture learnings" / "what did we
learn?". **Read `references/learn-guide.md` first** (dedup gate + classification
buckets). In brief: scan the conversation for uncaptured PM-domain
facts/decisions/questions/contradictions → dedup against the wiki → classify
(entity-update, new-entity, concept-update, decision, open-question, contradiction)
→ execute via §2/§4 (sign-off first only if 10+ pages) → report the change list → log:
`## [date] learn | <task> | captured: N | updated: N | new: N`.

## Multi-Device Access
The wiki dir is an Obsidian vault: `[[wikilinks]]`, Graph View, and Dataview all
work. Headless sync: `references/obsidian-sync.md`.

## Pitfalls
- **Never touch `raw/`**: sources are immutable; corrections live in wiki pages.
- **Update ≠ ingest**: use §4 for revising claims. Report diffs. Sweep stale variants.
- **Thresholds prevent bloat**: one mention ≠ an entity page (2+ sources or central).
- **Tag taxonomy**: add tags to SCHEMA.md first, then use. No freeform.
- **Contradictions explicit**: both claims, dates, sources, frontmatter flag.
- **Cross-references mandatory**: min 2 outbound `[[links]]` per page.
- **Confirm mass updates**: 10+ pages → user sign-off first.
- **Rotate log** at 500 entries (the session-stop hook does this automatically).
- **Human tone**: PM-facing content. No AI tells. No em-dashes. Natural voice.
  This wins over session-level compression/style hooks (e.g. caveman, terse modes):
  wiki pages and PM-facing output always use full natural prose regardless of any
  active output-shortening directive. Apply the hook's brevity to your own chatter,
  never to the artifact.
- **Private by default (allowlist)**: every page is private and excluded from
  exports unless it carries `shareable: true`. Do NOT add a `private:` flag — it's
  noise the tooling never reads. Set `shareable: true` only on genuinely public-safe
  pages (public sources, no PII / deal terms / 1:1 content).
- **Supersede, don't silently rewrite**: material replacement needs `supersedes:` /
  `superseded_by:` fields; the old page is archived, not deleted.
- **Coverage markers**: set `coverage:` and `gaps:` on entity/concept pages (lint
  warns when missing) so the user can tell a trustworthy page from a stub.
- **Session lock**: `.wiki-lock` flags another live session (session-start writes
  it, session-stop removes it; stale locks >2h auto-clear). It is not a reason to
  skip maintenance: re-read a page right before editing it.
- **Don't launder wiki prose into insight**: a recalled claim is a hypothesis until
  re-derived from a primary source (Session Defaults → Source discipline).

## References
- `references/ingest-guide.md` — full §2 ingest procedure (read before ingesting)
- `references/source-discipline.md` — full four-guard detail (read before sweeps/synthesis)
- `references/learn-guide.md` — full §13 post-task capture
- `references/schema-guide.md` — customizing SCHEMA.md + directory layout
- `references/update-guide.md` — diff discipline, stale-claim sweep
- `references/lint-guide.md` — tiered report + full check list + harness-hook precedence
- `references/privacy-guide.md` — pre-ingest filter + private-by-default allowlist
- `references/crystallize-guide.md` — transcript → decision digest
- `references/recommended-tools.md` — optional key-required tools
- `references/output-formats.md` — Marp, matplotlib, CSV, Mermaid, Canvas
- `references/obsidian-sync.md` — headless sync

## Scripts
- `python3 "${CLAUDE_SKILL_DIR}/scripts/lint.py" <path>` — tiered health report (`--auto-fix` repairs safe issues)
- `python3 "${CLAUDE_SKILL_DIR}/scripts/backlinks.py" <path> <slug>` — pages linking to a slug (`--context`, `--json`)
