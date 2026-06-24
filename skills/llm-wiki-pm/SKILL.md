---
name: llm-wiki-pm
description: Persistent PM knowledge base, competitive intel, customer notes, strategy, roadmap, AI market. Markdown wiki with entities, concepts, comparisons. Ingest sources, query, update with diffs, lint. Fires on "remember that / note that / don't forget / what do we know about X / what am I missing / blind spots".
when_to_use: Use when user wants to ingest a source, query the wiki, update pages, lint/audit, bootstrap a new wiki, audit coverage gaps, capture learnings, or says "remember that / note that / don't forget / what am I missing / blind spots". For persona/relationship-map pages use llm-wiki-persona; for briefs/digests use llm-wiki-brief; for CRM use llm-wiki-crm; for PRDs/user-stories/release-notes use llm-wiki-prd; for research sprints/deep dives use llm-wiki-research.
allowed-tools: Read Grep Write Edit Bash WebFetch
---

# LLM Wiki PM

Persistent knowledge base for PM work. Non-coding. Domain: product strategy,
competitive landscape, customer relations, roadmap, AI market, internal org.

Markdown files in a directory. Readable in Obsidian, VS Code, any editor.
The agent writes. You curate sources, ask questions, steer.

## When This Skill Activates
- User asks a question about PM knowledge, competitive intel, customers, strategy, or roadmap
- User asks to update or revise a page with new info
- User asks to lint, audit, or health-check the wiki
- User asks to create or bootstrap a PM wiki
- User references "my wiki", "the wiki", "knowledge base", "notes" in a PM context
- **Natural memory phrases** (no other memory system assumed): "remember that",
  "note that", "don't forget", "keep in mind", "save this", "log this",
  "make a note", "record that", "I want to remember" → treat as a wiki ingest.
  Capture the fact as a short wiki page or update to an existing relevant page.
  Use §2 Ingest with source `conversation | <date>`. Ask user which page it
  belongs to if unclear, or create a new entity/concept page if it warrants one.
- "I have a meeting/call/1:1 with [person]" → triggers §9 Pre-Meeting Briefing
- "What happened this week / last week / recently?" → triggers §10 Catch Me Up
- "[tag] digest" or "catch me up on [topic]" → triggers §11 Tag Digest
- "What am I missing?", "blind spots?", "coverage gaps?" → triggers §12 Coverage Audit
- "What did we learn?", "capture learnings", "record what we found" → triggers §13 Learn
- After completing a PM-domain task, Proactive Behavior #7 offers to capture uncaptured learnings

## Sub-skills (route to these)

These capabilities live in separate, independently-installable sub-skills, each
with its own triggers. Route to them — including **mid-flow**, when a core operation
surfaces one of these needs (don't try to do them from the core skill):

| Need | Sub-skill | Triggers |
|------|-----------|----------|
| Communication persona pages, relationship maps, org charts | `llm-wiki-persona` | "build a persona", "communication profile", "map relationships" |
| Daily/weekly briefs, tag digests, coverage briefs | `llm-wiki-brief` | "daily/weekly brief", "catch me up", "[tag] digest" |
| PRDs, user stories, release notes | `llm-wiki-prd` | "write a PRD", "user stories", "release notes" |
| Research sprints, competitive deep dives, stub enrichment | `llm-wiki-research` | "research [topic]", "deep dive", "auto-research [entity]" |
| Relationship/account health, CRM context, touchpoints | `llm-wiki-crm` | "relationship health", "account health", "who haven't I talked to" |

If a sub-skill isn't installed, the core skill's matching fallback operation
handles it where one exists (§10/§11/§12); persona, PRD, research, and CRM have no
core fallback — they require their sub-skill.

## Proactive Behaviors

These fire whenever the skill is loaded, not tied to explicit commands. Append
notes briefly *after* your answer, never before; don't interrupt it. All searches
below: wiki-search `semantic_search` preferred, grep fallback.
**Limits:** max 1 suggestion per turn; skip during code/debug tasks; only for PM-domain facts not already addressed.

### 1. Proactive Recall
User mentions a named entity (company, person, product) → search the wiki; if a
page exists, surface it inline (one line), including `confidence:`/`coverage:` from
frontmatter:
> "Wiki has [[page]] (updated YYYY-MM-DD, confidence: verified, coverage: partial). Want a summary?"

Always flag `rumor` confidence: "Wiki has [[page]] (rumor, unverified). Treat with caution." Skip entities that came up only in passing.

### 2. Ambient Fact Capture
User states a wikifiable PM fact (decision, person, company, roadmap, competitor,
customer) → offer to add it: *"That sounds wikifiable. Want me to add it?"* Skip
casual chat, unspecific opinions, hypotheticals.
**Dedup gate (mandatory):** search the wiki for the statement's key noun phrases first. If a page already holds the claim (same entity + same fact), offer an update instead, don't duplicate:
> "Already in [[page]] (updated YYYY-MM-DD). Want me to update it?"

### 3. Contradiction Alert
User states a fact about a known entity → search that entity, check for conflicts:
> "This may conflict with [[page]] from YYYY-MM-DD. Which is current?"

Best-effort. Don't surface false positives from vague matches.

### 4. Open Question Backlog
A factual question the wiki can't answer → offer to log it (*"Want me to log that
as an open question?"*) as a `question`-tagged page under `queries/` with text +
date. Skip rhetorical questions or ones the user is about to answer themselves.

### 5. Decision Journaling
Decision language ("we decided", "the call is", "going with X", "I've decided") →
offer to log it (*"Want me to log that decision?"*). If yes, create/update a
`decision`-tagged page with who decided, when, and the rationale if stated.

### 6. Relationship-Aware Answers
Question involves a named person → check `entities/<name>-persona.md` and
`concepts/relationship-map.md`; if found and relevant, fold in 1-2 lines of key
traits. Don't pad; skip if persona data isn't relevant.

### 7. Post-Task Capture
After a substantive PM-domain task (research, ingest, query, briefing, strategy),
self-audit for uncaptured facts/decisions/entity-updates/relationship-changes/
open-questions and offer a one-line summary:
> "This task surfaced N uncaptured facts/decisions. Want me to record them? (§13 Learn)"

**Guardrails:** PM-domain tasks only (skip code/debug); skip if already captured via #2-#5; max 1 offer per task (not per turn), no repeats within a multi-turn task; never auto-write; ignore passing/hypothetical mentions.

### 8. Tool Discovery
At session start, inventory connected MCP tools. When a query would be richer with
an unconnected tool, suggest it once:
> "This query would be richer with [tool]. Setup: `[install command]`. See references/recommended-tools.md."

Examples: public-company financials → SEC EDGAR; competitor LinkedIn → LinkedIn MCP; site traffic → SimilarWeb; cited grounded answers → NotebookLM; reading lists/highlights → Readwise.
**Guardrails:** max 1 suggestion per session (don't nag); only tools from `references/recommended-tools.md` (don't invent); skip tools the user declined; bundled tools should just work, so only flag key-required ones; frame as enhancement — answer with available tools first, then mention the upgrade path.

## Wiki Location
Before running any bash command that uses `$WIKI`, resolve it with:
```bash
WIKI=$(cat .wiki-path 2>/dev/null | tr -d '[:space:]')
WIKI=${WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}
```

Resolution: `.wiki-path` (project) → `CLAUDE_PLUGIN_OPTION_wiki_path` (global) → `WIKI_PATH` → cwd. Run `/llm-wiki-pm:set-wiki-path ~/path` to set project path. `additionalContext` states the active path each session.

The SessionStart hook's `additionalContext` states the active path each session.

## Session Defaults

**Wiki-first protocol:** Before answering any PM knowledge question, search the wiki using connected tools. Don't synthesize from training data when wiki pages exist. Cite explicitly: "Per [[page]]..." If no page exists, say so and offer to create one or log an open question.

**Freshness-first protocol (counterweight to wiki-first):** The wiki is only as good as the information fed into it. Wiki-first must not become a self-reinforcing loop where the wiki only ever cites itself and slowly drifts from reality. For ANY substantive operation — answering, creating, OR updating, on any page type, not just people/companies — proactively pull fresh primary information from connected tools (Slack, Gmail, Granola/meetings, CRM, web) rather than relying solely on what the wiki already records. Specifically:
- **Before writing or updating a page**, sweep connected tools for newer primary sources on the topic. Ingest what you find to `raw/` and anchor claims with inline provenance. Don't build or revise a page purely from the prose of other wiki pages — that launders secondhand mentions into false confidence (e.g. mislabeling a CTO as a "vendor cost owner" because that's all the linked pages happened to say).
- **One batch sweep satisfies freshness-first for a batch operation.** "Before writing... sweep" is per-*operation*, not per-*page*. A daily-maintenance run or multi-page ingest that touches ~8 pages does NOT mean eight separate tool sweeps: do one registry-driven sweep up front (per the Source-completeness guard), then write all the pages that sweep covered. The per-page rule applies to a standalone single-page write/update done outside a batch (a decision-bearing edit to one page → refresh that topic first). This resolves the apparent conflict with "Respect cost": batch once, write many; don't re-sweep per page, and don't skip the sweep entirely.
- **When answering**, if the most relevant wiki pages are thinly sourced, stale (past the staleness thresholds), or single-source, run a quick live search to corroborate or refresh before relying on them. Surface what changed and offer to update the page.
- **Default to ingest, not just recall.** When a connected tool surfaces something the wiki doesn't have, treat it as a candidate ingest, not a throwaway lookup. The goal is a wiki that constantly absorbs new signal, not one that re-serves old signal.
- **Be honest about provenance age.** Distinguish "the wiki says X (as of <date>)" from "live sources confirm X today." If you couldn't verify against a live source, say so.
- **Respect cost.** Proportional to stakes: a quick lookup needn't trigger a full sweep, but anything written, updated, or decision-bearing should be checked against live sources.

**Source-completeness guard (anti-premature-closure):** A thin, empty, or errored result from a requested source is NOT permission to stop. It is a signal that your search, not the source, may be the problem. "Enough captured", "that's sufficient", or moving on while a requested source returned nothing is a defect, not a judgment call. Specifically:
- **Define the source set before you sweep (anti-omission).** This guard catches "you reported a source empty" but NOT "you forgot the source exists" — the more dangerous failure. Before any "ingest all sources" / daily-brief / multi-source sweep, enumerate the **canonical sweep registry** in `$WIKI/MY-INTEGRATIONS.md` (the `## Sweep Registry` section) and iterate every source listed there. The registry, not your memory, defines what "all sources" means. If the file or section is missing, build the set from your connected-tool inventory plus the `Active Sources` table, **confirm it with the user, and write it to the registry** before sweeping — do not sweep an implicit, from-memory list. Silently omitting a registered source (declaring a sweep complete without it) is the worst-case defect: it reads as a complete picture while a high-signal source went unread.
- **Empty ≠ done.** Before concluding a source has nothing, run at least 2-3 query variations: broaden/narrow terms, widen the time window, try aliases/synonyms/handles/scope variants, and switch search syntax to whatever the tool supports (sender/author filters, channel/folder/label scopes, bare keyword). Keyword-based search tools commonly miss on first phrasing — vary before you quit, whatever the source.
- **Distinguish the three states.** For each requested source, classify the outcome as: `hits` (returned content), `empty-after-retries` (genuinely nothing after ≥2 varied queries), or `failed` (auth error, not connected, timeout, rate limit). Never silently collapse `failed` or `empty-after-retries` into "covered."
- **Make voids visible.** When a multi-source task (e.g. "ingest all sources", daily brief) is asked to cover N sources, you MUST report the status of every requested source — including the ones that came back empty or failed. Surface: which source, what queries you tried, and the most likely reason (genuinely quiet vs. wrong query vs. not connected vs. unauthorized). A void you report is honest; a void you hide reads as false completeness.
- **No closure language over an unresolved void.** Do not say a sweep is complete while any requested source is in `failed` state or was abandoned after a single query. Either resolve it, or explicitly flag it as an unresolved gap and offer the next step (reconnect tool, confirm channel name, widen range).
- **Proportional, not infinite.** This is not a mandate to loop forever. ≥2 varied queries per source, then report state. The bar is: tried honestly, reported truthfully — not "searched until found."

**Source-depth guard (open what you found):** Breadth of search is not depth of source. A hit that *references* content is not the content. If a result links to, attaches, or names a file/doc/image/canvas/PDF/spreadsheet/URL, that artifact is an **unresolved source** — fetch and read it before synthesizing anything from the surrounding prose. Specifically:
- **Referenced ≠ read.** A Slack thread saying "here's the 1-pager" with an attached image, a message linking a Drive doc, a ticket citing a spec — the prose around the artifact is a pointer, not a substitute. Drafting feedback, decisions, or page content from the pointer alone is a defect, even when the surrounding text sounds complete.
- **Open before you write.** Before producing any analysis, review, or wiki page that depends on a referenced artifact, actually fetch it (read the image, download the doc, follow the link). Real tiers, prices, numbers, and matrices routinely live only inside the file and contradict the thread summary.
- **Name what you couldn't open.** If an artifact can't be fetched (no access, unsupported type, dead link), treat it like a `failed` source: flag it explicitly as unread, do not synthesize over it, and offer the next step. Never let an unopened attachment read as covered.

**Session trust model:** Trust `.wiki-path` for location. Trust `SCHEMA.md` for taxonomy — new tags go there first. Trust `log.md` for recent activity. Deviate from any of these only with explicit user confirmation.

## Tool Selection Hierarchy

**Use ALL connected tools eagerly.** At session start, inventory every MCP tool
and integration available to you. The plugin bundles `wiki-search` for semantic
wiki search. Use it alongside any user-connected tools.

| Priority | Tools | When |
|----------|-------|------|
| 1 | **wiki-search** (bundled) — semantic + TF-IDF over wiki | Wiki queries, entity lookup, semantic recall |
| 2 | **MCP integrations** — Gmail, Slack, calendar, CRM, or any user-connected MCP | Emails, threads, messages, events, enriching entity pages with comms |
| 3 | **WebFetch / WebSearch** | External research, fetching web pages for wiki ingest |
| 4 | **grep** | Exact token match only (dollar figures, codenames, frontmatter values) |
| 5 | **Read** (file reads) | When you already know the exact file and need full content |

**Bundled MCP server:** `wiki-search` (semantic + TF-IDF over wiki via
`@wirux/mcp-markdown-vault`, ~80MB model on first use).

**Optional tools** that enhance these capabilities are listed in
`references/recommended-tools.md`. Suggest them via Proactive Behavior #8
when the user's query would benefit.

**Rules:**
- **Connected tools first, file reads last.** If a tool answers faster than
  reading files, use it.
- **Search before read.** Use search/query tools to find relevant pages before
  reading files. Don't scan sequentially.
- **Use all available tools.** Inventory at session start. Don't overlook tools.
- **Bound connected-tool output.** Broad searches against chat/email/warehouse
  tools can return 100K+ chars and blow the token budget. Default to the
  tightest useful query: concise/summary response format, no message context,
  `limit`≤15, and **narrow scope (channel/author/label/folder/date) BEFORE
  broad keyword**. Widen only if the narrow pass comes back empty. A sweep that
  dumps everything then slices it after the fact is a defect, not thoroughness.
- **Date operators are soft on semantic backends.** Many semantic-search tools
  (incl. some chat search) treat `after:`/`before:` as advisory — ranking by
  relevance, not recency — so a dated query can still return out-of-window hits.
  Always verify each result's actual timestamp before trusting it as in-window;
  don't assume the date filter was honored.

**Model routing:**

| Task | Model |
|------|-------|
| File reads, grep, web fetches, writing pages, log appends | Sonnet (I/O) |
| Synthesis, crystallize, coverage audit, conflict resolution | Opus (reasoning) |

Workers write output ≥ 2K tokens to `/tmp/{task}-{date}.md` and return short status + path. Never return large text as inline worker output.

## Architecture: Three Layers

```
wiki/
├── SCHEMA.md              # Conventions, domain config, tag taxonomy
├── index.md               # Sectioned content catalog
├── overview.md            # Evolving synthesis, single entry point
├── log.md                 # Append-only action log (rotate at 500)
├── _status.md             # Pre-computed health (session-start hook)
├── .wiki-lock             # Session lock (auto-managed by hooks)
├── raw/                   # Layer 1: Immutable sources
│   ├── articles/          # Analyst reports, press, blog clippings
│   ├── papers/            # PDFs, whitepapers
│   ├── transcripts/       # Customer calls, 1:1 notes, interviews
│   ├── internal/          # Slack threads, strategy docs, decks
│   └── assets/            # Images, screenshots
├── entities/              # Layer 2: People, companies, products, teams
├── concepts/              # Layer 2: Strategies, themes, frameworks
├── comparisons/           # Layer 2: Side-by-side analyses
├── queries/               # Layer 2: Filed Q&A worth keeping
└── _archive/              # Superseded content + pre-update snapshots
```

**Layer 1 raw/**: immutable. Agent reads, never modifies.
**Layer 2 wiki pages**: agent-owned. Created, updated, cross-referenced.
**Layer 3 SCHEMA.md**: governs structure and taxonomy.

## Pre-Flight Check

Run at session start before any operation.

**① Wiki exists?**
```bash
WIKI=$(cat .wiki-path 2>/dev/null | tr -d '[:space:]')
WIKI=${WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}
[ -d "$WIKI" ] || echo "MISSING"
```
If missing: "Wiki directory not found. Scaffold a new wiki or run `/llm-wiki-pm:set-wiki-path` to point to an existing one."

**② SCHEMA.md exists?**
If `$WIKI/SCHEMA.md` is absent: offer to scaffold it from `templates/SCHEMA.md`. Do not proceed with any write operation until SCHEMA.md exists.

**③ MY-INTEGRATIONS.md (optional)**
If `$WIKI/MY-INTEGRATIONS.md` exists, read it. Apply any routing preferences in the "Routing Notes" section (e.g., preferred Slack channel naming, Gmail label patterns) to the current session's ingest defaults. Also read the `## Sweep Registry` section — it is the canonical list of sources a full "ingest all sources" / daily-brief sweep must cover (see the Source-completeness guard). No file = use generic defaults. Never create this file during Pre-Flight — it is auto-created on first ingest. (The registry is established/confirmed the first time a multi-source sweep runs, not during Pre-Flight.)

**④ Role pack detection (optional)**
Check `.claude/roles/` for a matching role file based on how the user describes their role. If found, apply these behaviors for the session:

| Field | Effect |
|---|---|
| `focus_tags` | Proactive Recall (§1) and Ambient Capture (§2) prioritize entities tagged with these. Surface them even on passing mentions. |
| `preferred_output_format: brief` | Compress query answers to essentials. Full synthesis filed to `queries/` in background. |
| `preferred_output_format: file` | Substantial answers always filed to `queries/<slug>/README.md`, not returned inline. |
| `crystallize_template` | Use this template name when running Crystallize (§2 step ①①). |
| `surface_confidence_threshold` | Proactive Recall (§1) only surfaces pages meeting this confidence level: `verified` = high-signal only, `likely` = default, `rumor` = always surface with warning. |

No role pack = all defaults apply. Missing `.claude/roles/` is not an error.

**⑤ Surface _status.md warnings**
If `$WIKI/_status.md` exists, read it now. Surface any pre-computed staleness or lock warnings immediately.

If all checks pass (①–⑤): proceed silently. No need to narrate the pre-flight to the user unless a problem is found.

**Pre-Flight runs before Orient.** Once Pre-Flight completes, proceed to the Orient steps below.

## CRITICAL: Orient Every Session

Before any ingest/query/update/lint, **always**:

① Read `SCHEMA.md`, domain, conventions, tag taxonomy
② Read `index.md`, what pages exist
③ Read last 20-30 lines of `log.md`, recent activity
④ Read `overview.md`, current synthesis state
⑤ For 100+ page wikis: search before creating — use wiki-search `semantic_search` (preferred) or `grep -r "topic" $WIKI --include="*.md"` (fallback)
⑥ **Staleness warning**: if any page has `updated:` older than 14 days
   (overview/index) or 30 days (entity/concept pages) AND log.md shows recent
   activity touching that area, surface: "Warning: [[page]] may be stale.
   Last updated YYYY-MM-DD. Recent log activity: [date, action]."

⑦ **Confidence decay check**: after reading `log.md`, search for competitive pages — use wiki-search `semantic_search` with query "competitive" (preferred) or `grep -r "competitive" $WIKI/entities $WIKI/concepts --include="*.md" -l` (fallback).
   For each result, check its `updated:` date. If older than 60 days, surface:
   > "⚠️ Confidence decay: [[page]] is 60+ days old. Verify before use."

⑧ **`_status.md` warnings**: already surfaced during Pre-Flight step ④. Skip if Pre-Flight completed this session. If Pre-Flight was skipped: read `$WIKI/_status.md` now and surface any warnings before proceeding.

⑨ **Orient gate (enforced):** if you have NOT completed steps ①-④ in THIS
   session, refuse any write operation (ingest, update, archive, supersede).
   Surface: "Need to orient first. Running now." Then orient, then proceed.
   Read-only queries (§3) may proceed without full orient if the user's
   question is narrow and you can answer from a single page read. But any
   operation that creates or modifies a wiki page requires orient.

Skipping orientation → duplicate pages, missed cross-refs, schema drift.

**Harness-hook precedence during orient.** The orient and lint steps are deliberately bash-heavy (`tail log.md`, `grep` frontmatter, `_status.md` reads). A session-level hook that caps raw output (e.g. context-mode's "no Bash >20 lines") does not exempt you from orienting — these reads are required correctness work, not casual output. Run them; route bulky output through whatever the hook prefers (a context-mode tool, or read the file directly) rather than skipping the step. When a harness hook and this skill conflict, this skill's correctness and tone rules govern wiki work; apply the hook to discretionary chatter only.

## Core Operations

### 1. Initialize (new wiki)
The plugin scaffolds the wiki automatically on first session start. No manual
command needed. The `SessionStart` hook detects a missing wiki, creates the
directory structure, and copies templates using the domain you provided at
plugin enable time.

If the wiki was not auto-created (e.g. plugin installed mid-session), tell the
user to restart the session and the hook will scaffold it.

After initialization, confirm domain scope with the user and customize
`SCHEMA.md` tag taxonomy (see `templates/SCHEMA.md` for PM-tuned defaults).

### 2. Ingest a source

**Read `references/ingest-guide.md` before ingesting** — it carries the full
step-by-step (raw-capture conventions, page thresholds, inline provenance, the
mandatory privacy filter, crystallize, entity-promotion scan). Skipping it
produces orphan pages, missing cross-refs, and laundered secondhand claims. In brief:

① **Capture raw** to `raw/` (immutable), behind a privacy filter — strip secrets;
   mark `private: true` for customer/deal/1:1/internal-strategy content.
② **Surface takeaways** to the user before writing (skip in batch contexts).
③ **Check existing pages** (`grep -r`) — decide create vs update.
④ **Apply page thresholds** (2+ sources or central) and **enrich from connected
   tools BEFORE writing** per Freshness-first — never build a page from other
   pages' prose alone.
⑤ **Write/update** with required frontmatter, taxonomy tags, ≥2 `[[wikilinks]]`,
   inline `[source: ...]` markers, and `coverage:`/`gaps:`/`confidence:` set.
⑥–⑧ Backlink audit; refresh `overview.md` if synthesis shifts; update `index.md`;
   append the `ingest` entry to `log.md` listing every file touched.
⑨ Log the source row in `MY-INTEGRATIONS.md`.
①⓪ Report every file touched; confirm before mass-updating (10+ pages).
①① **Crystallize** transcripts/research chains into a `queries/` digest (see
   `references/crystallize-guide.md`).
①② **Entity promotion scan** — promote people/companies/products with 3+
   attributes to their own pages (always confirm). Offer a persona page (the
   `llm-wiki-persona` sub-skill) for any promoted person.

### 3. Query
① **Search first** (per Tool Selection Hierarchy above): wiki-search `semantic_search` → grep → file read. Never start by reading files hoping to find the answer.
② Read `index.md` to confirm page catalog for top hits
③ Read relevant pages via wiki-search `read` or file reads (only after search identified them)
④ Synthesize. Cite pages: "Per [[tricentis]] and [[test-automation-mq]]..."
⑤ **Select output format** based on question and audience:
   - Plain markdown answer inline → most queries
   - File under `queries/<slug>/README.md` → substantial syntheses
   - Add artifacts (Marp deck / matplotlib chart / CSV / Mermaid) if the
     audience or question warrants it. See `references/output-formats.md`.
⑥ **File valuable answers back**: substantial comparisons, deep dives,
   novel synthesis. Skip trivial lookups.
⑦ Append to `log.md`: `## [YYYY-MM-DD] query | <question> (filed: yes/no)`
⑧ After filing a new page, wiki-search auto-reindexes on next query.

### 4. Update (revise existing pages)

Separate discipline from ingest. Triggered when new info conflicts with or
refines existing content.

**Pre-update snapshot (mandatory):** before any destructive update (overwrite,
archive, supersede), copy the current page to `_archive/<slug>-<YYYY-MM-DD>.md`.
Log: `snapshot: _archive/<slug>-<date>.md before update`. This makes "undo that
last change" trivial. Skip snapshots only for trivial edits (typo fix, date bump).
① **Identify all affected pages**: three-way search:
   - `python3 "${CLAUDE_SKILL_DIR}/scripts/backlinks.py" "$WIKI" <slug>` for structural backlinks (pages
     linking to the entity being revised)
   - wiki-search `semantic_search` for semantic variants (paraphrases of the stale claim)
   - `grep -r` for exact token match (dollar figures, codenames)
   Don't update one page and leave 3 others with the stale version.

② **Show diff BEFORE writing**: present old text, new text, reason. Confirm
   with user for any claim touching 5+ pages or changing stated strategy.

③ **Cite source**: every update must include the raw source that justifies
   the change in the page body and in the log entry.

④ **Stale-claim sweep**: after update, re-search (wiki-search semantic_search + grep for
   exact variants) across the wiki. Fix all instances in the same pass.

⑤ **Bump `updated:` date** on every page touched.

⑥ **Log**: `## [YYYY-MM-DD] update | <claim/page> | source: raw/...`
   List every file modified.

⑦ **Write verification:** after writing any page, re-read the file and confirm
   frontmatter parses (title, updated, type, tags all present). If write failed
   or frontmatter is malformed, surface error immediately and do NOT update
   index.md or log.md. Partial state is worse than a failed write.

⑧ **Inline provenance on updates:** when changing a specific claim, update
   the inline `[source: ...]` marker on that claim. Don't leave old source
   markers on revised facts.

### 5. Lint (tiered report)

Use `scripts/lint.py`, writes report to `wiki/queries/lint-YYYY-MM-DD.md`
with severity tiers. Offers concrete fixes. Logs unconditionally.

```bash
python3 ${CLAUDE_SKILL_DIR}/scripts/lint.py "$WIKI"
```

Checks span 🔴 (broken links, missing/invalid frontmatter, off-taxonomy tags),
🟡 (orphans, index drift, oversized pages, unresolved contradictions, stale pages),
🟠 (stale overview/index/entities with recent log activity), and 🔵 (tag-frequency,
log rotation). Full check list and how to read the report: `references/lint-guide.md`.
Act on 🔴, investigate 🟠, discuss 🟡 with the user, note 🔵 for later.

### 6. Archive

Superseded or out-of-scope content:
1. Create `_archive/` if missing
2. Move page preserving path (`_archive/entities/old.md`)
3. Remove from `index.md`
4. Update inbound linkers: replace `[[old]]` with plain text "(archived)"
5. Log archive action with reason

### 7. Staleness Check

Run when: user asks "is the wiki up to date?", "what needs updating?", or after
an extended gap. Also runs automatically during orient (step ⑥).

Scan `updated:` across `entities/`, `concepts/`, `comparisons/`, `overview.md`,
`index.md`. Stale thresholds: 14 days for overview/index, 30 days for entity/
concept/comparison. Cross-reference `log.md` — a page with recent log activity
but an unmoved `updated:` is behind, not dormant; flag those first. Surface
findings grouped by type, suggest the 2-3 likeliest update candidates, and offer
the Update flow (§4) per page. Log the check regardless of whether updates follow.

### 8. Persona Pages → `llm-wiki-persona` sub-skill

Communication persona pages and relationship maps are handled by the
**`llm-wiki-persona`** sub-skill (build a persona, style analysis, org chart,
relationship map). It owns the channel model, the no-fabrication rule, and the
relationship-map format. The entity-promotion scan (§2 ①②) offers a persona for
any promoted person — route there.

### 9. Pre-Meeting Briefing

Trigger: "I have a meeting/call/1:1 with X" or "brief me on X before my call"

grep the entity name and read its page; read its persona page if one exists; pull
relevant context from `concepts/relationship-map.md`; read the last 5 `log.md`
entries mentioning the entity; grep open `question`-tagged pages for it. Synthesize
a short brief: **Who** (role, org, relationship), **What we know** (key facts),
**Recent activity**, **Open questions**, **Communication tips** (1-2 lines from the
persona page if available). Log: `## [YYYY-MM-DD] brief | <entity> | pre-meeting`.

### 10. Catch Me Up

**`llm-wiki-brief`** handles this with richer output (daily/weekly/coverage briefs)
— route there when installed. Fallback when it isn't: read `log.md` for the last N
days (default 7), list new/updated pages, decisions, and open questions; surface
`_status.md` warnings and the 2-3 most active areas. Log:
`## [YYYY-MM-DD] catchup | last N days | X actions`.

### 11. Tag Digest

**`llm-wiki-brief`** handles tag digests with cross-referencing and file-to-queries
output — route there when installed. Fallback when it isn't:

① grep wiki frontmatter for the requested tag.
② Read matching pages, newest first by `updated:` date.
③ Synthesize into a structured brief:
   - Key players or themes
   - Recent changes
   - Open questions
   - Notable patterns
④ Offer to file the synthesis as a query page.

Log: `## [YYYY-MM-DD] digest | tag: <tag> | X pages synthesized`

### 12. Coverage Audit

Trigger: "what am I missing?", "blind spots?", "coverage gaps?", "what don't
we know?", "wiki completeness". (`llm-wiki-brief`'s Coverage Brief gives richer
output — route there when installed.)

Scan `coverage:` frontmatter across entities/, concepts/, comparisons/ (count
stub/partial/comprehensive/missing); collect `gaps:` lists; read open
`question`-tagged pages. Cross-reference: any entity mentioned in 3+ pages without
its own page is a gap. Surface partial/stub counts with top gaps, pending open
questions, un-paged entities, and taxonomy domains with zero pages. Offer to create
stub pages for the biggest gaps. Log:
`## [YYYY-MM-DD] coverage-audit | stubs: N | gaps: N | open-questions: N`.

### 13. Learn (Post-Task Capture)

Trigger: user accepts Proactive Behavior #7 offer, or explicitly says "what did
we learn?", "capture learnings", "record what we found", "save what we discussed".

**Read `references/learn-guide.md` before running a capture pass** — it carries the
dedup gate and the classification buckets, and skipping it produces duplicate facts
and unclassified captures. In brief: scan the conversation for uncaptured PM-domain
facts/decisions/questions/contradictions → dedup against the wiki → classify each
(entity-update, new-entity, concept-update, decision, open-question, contradiction)
→ propose a compact change list (sign-off if 10+) → execute via §2/§4 conventions →
log: `## [YYYY-MM-DD] learn | <task-summary> | captured: N | updated: N | new: N`.

## PM Workflow Patterns

**Weekly competitive digest:** user drops 3-5 analyst links → ingest all →
batch entity updates → one log entry → overview.md refresh.

**Pre-meeting prep:** query "what do we know about <customer>?" → read
`entities/<customer>.md` → check recent log entries for updates → offer to
file post-meeting notes back into the customer page via update flow.

**Recurring 1:1 follow-up:** ingest the transcript to
`raw/transcripts/<person>-1-1-YYYY-MM.md` → extract decisions/themes → update
`concepts/<theme>.md` pages → link from `entities/<person>.md`.

**Quarterly lint:** run lint, triage 🔴, discuss 🟡 trends, rotate log if
needed, refresh overview.md.

## Multi-Device Access (Obsidian + obsidian-headless)
Wiki dir = Obsidian vault. `[[wikilinks]]` render, Graph View works, YAML
frontmatter powers Dataview. See `references/obsidian-sync.md` for headless sync setup.

## Pitfalls

- **Orient first**: SCHEMA + index + log + overview before any operation.
- **Never touch `raw/`**: sources immutable. Corrections live in wiki pages.
- **Update != ingest**: use the Update flow for revising existing claims.
  Show diffs. Sweep stale variants. Don't silently overwrite.
- **Thresholds prevent bloat**: analyst reports name-drop 30 companies per
  article. One mention ≠ entity page.
- **Tag taxonomy**: add tags to SCHEMA.md first, then use. No freeform.
- **Contradictions explicit**: both claims, dates, sources, frontmatter flag.
- **Cross-references mandatory**: min 2 outbound `[[links]]` per page.
- **Confirm mass updates**: 10+ pages touched → get user sign-off first.
- **Rotate log**: at 500 entries, rename `log-YYYY.md`, start fresh.
- **Human tone**: PM-facing content. No AI tells. No em-dashes. Natural voice.
  This wins over session-level compression/style hooks (e.g. caveman, terse modes):
  wiki pages and PM-facing output always use full natural prose regardless of any
  active output-shortening directive. Apply the hook's brevity to your own chatter,
  never to the artifact.
- **Privacy by default**: customer names, deal sizes, 1:1 content = `private: true`.
  When in doubt, mark private. Exports/shares respect the flag.
- **Supersede, don't silently rewrite**: materially replacing a page needs
  explicit `supersedes:` / `superseded_by:` fields. Old page archived, not deleted.
- **Use wiki-search first**: grep misses semantic matches. At dozens of meetings/week
  the wiki grows fast; grep + index alone will silently degrade quality.
- **Snapshot before destructive writes**: copy page to `_archive/<slug>-<date>.md`
  before overwrite, archive, or supersede. Makes rollback trivial.
- **Verify writes**: re-read after writing, confirm frontmatter parses. Don't
  update index/log if the write failed.
- **Inline provenance**: every non-obvious claim needs `[source: slug, location]`.
  Frontmatter sources alone don't anchor claims. Updates without inline markers
  silently corrupt provenance.
- **Coverage markers**: set `coverage:` and `gaps:` on every entity/concept page.
  Without these, the user can't tell if a page is trustworthy or just a stub.
- **Session lock**: `.wiki-lock` prevents concurrent session corruption. The
  session-start hook writes it; session-stop removes it. If a stale lock
  persists (>2h), session-start auto-clears it.
- **Dedup ambient captures**: grep before offering to add a fact the wiki already
  knows. Duplicate facts erode trust faster than missing facts.

## References

- `references/ingest-guide.md`, full §2 ingest procedure (read before ingesting)
- `references/learn-guide.md`, full §13 post-task capture procedure
- `references/schema-guide.md`, customizing SCHEMA.md for your domain
- `references/update-guide.md`, diff discipline, stale-claim sweep patterns
- `references/lint-guide.md`, interpreting tiered reports + full check list
- `references/obsidian-sync.md`, headless sync deep dive
- `references/privacy-guide.md`, pre-ingest filter + `private:` flag
- `references/crystallize-guide.md`, transcript → decision digest pattern
- `references/recommended-tools.md`, optional key-required tool recommendations
- `references/output-formats.md`, Marp, matplotlib, CSV, Mermaid, Canvas
- `references/nextjs-integration.md`, embed graph + page viewer in a Next.js app

## Scripts

- `python3 "${CLAUDE_SKILL_DIR}/scripts/lint.py" <path>`, tiered health report
- `python3 "${CLAUDE_SKILL_DIR}/scripts/backlinks.py" <path> <slug>`, show pages linking to a slug.
  Use `--context` for line-level matches, `--json` for agent consumption.
- `python3 "${CLAUDE_SKILL_DIR}/scripts/lint.py" <path> --auto-fix`, repair safe issues (supersession
  link redirects, index backfill)
