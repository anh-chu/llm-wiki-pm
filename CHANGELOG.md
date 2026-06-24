# Changelog

All notable changes to this project.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

## [2.17.0] - 2026-06-24

### Added

- **Canonical sweep registry (anti-omission).** The source-completeness guard
  caught "you reported a source empty" but not "you forgot the source exists" —
  the more dangerous failure (a daily brief silently omitted Slack and GitHub
  while declaring the sweep complete). New `## Sweep Registry` section in
  `MY-INTEGRATIONS.md` defines the canonical source set a full "ingest all
  sources" / daily-brief sweep must iterate, with one ledger row per registered
  source. The guard, Pre-Flight ③, and `llm-wiki-brief` now read the registry
  instead of an implicit from-memory list; if absent it is built from connected
  tools + Active Sources, confirmed with the user, and written before sweeping.

## [2.16.0] - 2026-06-22

### Added

- **Warehouse / database / BI ingest pattern** (ingest-guide) — SQL/analytics
  sources (Metabase, BigQuery, Snowflake, dbt, dashboards) are now first-class.
  Provenance convention: cite the query ref + snapshot id (`source_query_ref`,
  `source_snapshot`, e.g. `month_id=202606`), not just the tool name, so a
  warehouse number is reproducible. New `warehouse` source type and a
  recommended-tools entry. Warehouse facts are `confidence: verified` even at
  `coverage: stub`.

### Changed

- **`lint --auto-fix` now alpha-sorts and backfills index.md sections.** Replaces
  the old append-after-header behavior (which inserted out of order and never
  touched existing entries). Each `## ` section's `- [[slug]]` bullet run is
  merged with missing entries and sorted case-insensitively; non-bullet lines
  keep their place. Without `--auto-fix`, drift is reported as a warning.

## [2.15.0] - 2026-06-22

### Added

- **Connected-tool output bounding** (core skill, Tool Selection Hierarchy) —
  broad chat/email/warehouse searches can return 100K+ chars and blow the token
  budget. New rule: tightest useful query first (concise format, no context,
  `limit`≤15, narrow scope before broad keyword); widen only on empty.
- **Soft date-operator warning** (core skill) — `after:`/`before:` are advisory
  on semantic-search backends (rank by relevance, not recency). Always verify a
  result's actual timestamp before trusting it as in-window.
- **`lifecycle: stub-intentional` frontmatter flag** — marks by-design thin pages
  (fresh warehouse/account/escalation stubs). `lint.py` now exempts them from the
  orphan warning (counted as info), ending the daily re-flagging of correct
  behavior. Documented in schema-guide.

### Changed

- **schema-guide: `confidence` and `coverage` are independent axes** — source
  reliability vs completeness must not be collapsed. A page can be
  `confidence: verified` + `coverage: stub` (e.g. warehouse facts with no
  engagement context yet); don't downgrade confidence just because coverage is
  thin.

---

## [2.14.0] - 2026-06-22

### Added

- **Source-depth guard (open what you found)** — new Session Default in the core
  skill, complementing the source-completeness guard. Breadth of search is not
  depth of source: a result that references/attaches a file/doc/image/canvas/URL
  is an unresolved source, fetch and read it before synthesizing from surrounding
  prose. Unfetchable artifacts are flagged unread (like a `failed` source), never
  treated as covered. Closes the gap where thread prose was mistaken for an
  unopened attachment.

### Changed

- **Harness-hook precedence** stated explicitly in the core skill. PM-facing/wiki
  output keeps full natural prose regardless of session-level compression/style
  hooks (e.g. caveman/terse modes) — brevity applies to chatter, not artifacts.
  Bash-heavy orient/lint steps are not exempted by raw-output caps (e.g.
  context-mode's Bash-length limit); run them and route bulky output through the
  hook's preferred path rather than skipping the step.

---

## [2.13.0] - 2026-06-13

### Added

- **Source-completeness guard (anti-premature-closure)** — new Session Default in
  the core skill plus a Source Coverage ledger in `llm-wiki-brief`. An empty or
  errored source is now treated as a search defect, not a stop signal: ≥2 varied
  queries per source before declaring it empty, three-state classification
  (`hits` / `empty-after-retries` / `failed`), and every requested source must
  appear in multi-source output. No "enough captured" while a void is unresolved.
- **`llm-wiki-persona` sub-skill** — communication persona pages and relationship
  maps promoted out of the core skill into its own independently-installable
  sub-skill (real standalone trigger, owns the channel model and relationship-map
  format, no longer collides with crm's persona pointer).
- **Sub-skill routing roster** in the core skill so agents reliably hand off
  mid-flow to brief/prd/research/crm/persona.

### Changed

- **Vendor-agnostic generalization** across the plugin — source `type` enum
  (`chat`/`email`/`other` instead of `slack`/`gmail`), ingest recipes, and persona
  communication channels now state the model generically with Slack/Gmail/etc. as
  labelled examples, not baked-in rules.
- **Core skill slimmed 791 → ~560 lines** — ingest and learn procedures moved to
  `references/ingest-guide.md` and `references/learn-guide.md` (gated reads), lint
  checklist to `lint-guide.md`, fallback ops condensed to sub-skill pointers,
  Proactive Behaviors prose tightened. Governance/safety rules kept resident.
- **`llm-wiki-prd` slimmed 352 → 145 lines** — output templates moved to
  `references/prd-templates.md`.
- **crm/research enrichment boundary clarified** — crm's Auto-Enrichment defers
  deep factual sweeps to `llm-wiki-research` when installed, focusing on
  relationship/CRM fields.

### Fixed

- Core §3 Query step numbering (started at ②); §13 Learn ambiguous section refs;
  `enrich [entity]` trigger collision between crm and research; truncated trigger
  sentence in Proactive Behavior §2 (Ambient Fact Capture).

---

## [2.10.1] - 2026-05-10

### Fixed

- **wiki-search startup 35s → ~4s** — replaced `npx -y` invocation with a
  wrapper script (`hooks/wiki-search.sh`) that resolves the cached binary
  directly, skipping npx's 9s package resolution overhead. Falls back to npx
  on first run. Session-start hook pre-caches the package in the background.

---

## [2.10.0] - 2026-05-10

### Changed

- **Slim bundled MCP to wiki-search only** — removed 9 bundled servers (RSS,
  YouTube, web reader, Wayback Machine, web search, Wikipedia, arXiv, news,
  app-insight) that caused ~3.5 min startup timeout on first run. Moved all to
  `references/recommended-tools.md` with `claude mcp add` install commands.
  Plugin now bundles only `wiki-search` (`@wirux/mcp-markdown-vault`).
- **Removed qmd dependency** — wiki-search fully replaces qmd as default
  search. Deleted `references/qmd-search.md`.

---

## [2.9.0] - 2026-05-10

### Added

- **Bundled wiki-search MCP** — semantic + TF-IDF search over wiki via
  `@wirux/mcp-markdown-vault` (~80MB model auto-downloaded on first use).
- **Proactive Behavior #8: Tool Discovery** — agent suggests useful tools when
  user's query would benefit from an integration they haven't connected. Max 1
  suggestion per session. References recommended-tools guide.
- **`references/recommended-tools.md`** — curated guide for 20+ optional tools
  (RSS, YouTube, arXiv, news, app-insight, Brave, Exa, Firecrawl, LinkedIn,
  SEC EDGAR, SimilarWeb, Readwise, NotebookLM, and more) with install commands
  and when-to-suggest triggers.
- **Rewritten Tool Selection Hierarchy** — 5-tier priority table with
  wiki-search first, connected tools second, WebFetch/WebSearch as fallback.

### Fixed

- **RSS MCP** — replaced broken `rss-mcp` (uncompiled ESM) with
  `@0xquinto/rss-mcp` (11 tools: feeds, digests, OPML import).
- **arXiv MCP** — replaced `arxiv-mcp-server` (Python/poetry dependency) with
  `@cyanheads/arxiv-mcp-server` (pure Node.js, 4 tools).

---

## [2.8.0] - 2026-05-10

### Added

- **Proactive Behavior #7: Post-Task Capture** — agent self-audits after
  completing PM-domain tasks for uncaptured facts, decisions, entity updates,
  and open questions. Offers a one-line summary before writing anything.
- **Core Operation #13: Learn** — full workflow for extracting and recording
  post-task learnings. Scan → dedup → classify → propose → execute → log.
  Learnings go into existing page types (entity, concept, query, decision).
- New activation triggers: "what did we learn?", "capture learnings",
  "record what we found"

---

## [2.7.2] - 2026-05-05

### Fixed

- **session-stop.sh**: wiki path resolution now reads `.wiki-path` file and falls
  back to cwd, matching `session-start.sh`. Previously the lock was never released
  for projects using `.wiki-path` (the default project-level config).
- **session-stop.sh**: lock release moved to an `EXIT` trap so it fires on all
  exit paths (early returns, errors, normal completion). Previously early exits
  skipped lock cleanup.
- **session-stop.sh**: lock is now held through log rotation instead of being
  released before the `mv`, closing a race window with concurrent sessions.
- **post-write.sh**: wiki path resolution now reads `.wiki-path` file, matching
  `session-start.sh`. Wikilink checks were silently skipped for `.wiki-path` users.

---

## [2.7.1] - 2026-04-23

### Changed

- **worker-wiki-indexer**: auto-regenerate `overview.md` when stale (>7 days with
  recent activity) instead of only flagging. Synthesizes theme clusters, coverage
  summary, recent activity, known gaps, and stats from page frontmatter. Preserves
  any hand-written intro paragraph.

---

## [2.7.0] - 2026-04-23

Sub-skill architecture, MY-INTEGRATIONS learned routing, worker-people-updater, CRM layer.

### Added

- **Sub-skill architecture**. Four optional skills that extend the core without
  bloating `llm-wiki-pm/SKILL.md`. Each has scoped `when_to_use` triggers; core
  skill serves as fallback when sub-skills are not installed.
  - **`llm-wiki-brief`**: daily/weekly briefs, tag digests, coverage brief. Read-only
    by default; files output to `queries/` only on user request. Richer output than
    core §10/§11 fallbacks.
  - **`llm-wiki-prd`**: PRD drafts, user stories, release notes. Wiki-grounded only —
    gaps surfaced before drafting. No fabrication policy enforced.
  - **`llm-wiki-research`**: research sprints, competitive deep dives, auto-research
    (stub enrichment), gap research. Delegates all URL fetching to `worker-source-fetcher`
    — never WebFetch directly for source saving.
  - **`llm-wiki-crm`**: PM CRM layer. Relationship health check (tier staleness
    thresholds), auto-enrichment (public data only via WebSearch), account health
    dashboard, feature ask tracker (`key_asks` aggregation across accounts),
    touchpoint logging. No dollar figures — `arr_tier` tiers only.
- **`skills/llm-wiki-crm/templates/SCHEMA-crm-fields.md`**: patch file (not a
  SCHEMA.md replacement) with CRM frontmatter additions for person and company
  entities. Merge instructions included.
- **`worker-people-updater`** (`.claude/agents/`). Scans wiki for promotion
  candidates (names in 3+ pages, no entity page), stale profiles (log activity
  but page not updated), and CRM touchpoint overdue. Report-only — never modifies
  wiki files. Outputs to `/tmp/wiki-people-update-<YYYYMMDD>.md`.
- **`MY-INTEGRATIONS.md`** template (`skills/llm-wiki-pm/templates/`). Learned
  source routing file — auto-populated by skill after each ingest (source type,
  last used, ingest count). Pre-Flight now checks for and reads this file. Replaces
  hardcoded source routing defaults with observed ingest behavior.

### Changed

- `SKILL.md` Pre-Flight: new step ③ reads `MY-INTEGRATIONS.md` if present; existing
  role pack detection shifted to step ④; `_status.md` check shifted to step ⑤.
- `SKILL.md` §2 Ingest: new step ①⓪ auto-updates `MY-INTEGRATIONS.md` after each
  ingest; Crystallize shifted to ①②, entity promotion scan to ①③.
- `SKILL.md` §10, §11: added fallback notes pointing to `llm-wiki-brief` when installed.
- `AGENTS.md`: added sub-skill architecture table; updated Agent Surfaces section;
  removed Kiro/Gemini CLI references.
- `plugin.json`: version 2.7.0, skillCount 5 (core + 4 sub-skills), workerCount 5,
  skill architecture note updated, keywords expanded (crm, research, briefs).
- `marketplace.json`: version 2.7.0, tags expanded (crm, research, briefs, prd).
- `README.md`: layout diagram shows full sub-skill tree; "What you get" updated with
  sub-skills and MY-INTEGRATIONS.

---

## [2.6.0] - 2026-04-23

COG-inspired architecture: worker agents, role packs, universal agent contract, and pre-flight hardening.

### Added

- **Worker agents** (`.claude/agents/`). Four specialized subagents for expensive
  wiki operations: `worker-wiki-indexer` (rebuilds index.md/overview.md),
  `worker-source-fetcher` (fetch + privacy-filter URLs/PDFs into raw/),
  `worker-link-validator` (broken wikilinks, orphans, index gaps),
  `worker-lint` (runs lint.py, returns severity summary). Workers write
  large outputs to `/tmp/` and return short status, keeping the lead session lean.
- **Role packs** (`.claude/roles/`). Four persona files — `product-manager`,
  `researcher`, `executive`, `founder` — plus a `_template`. Each declares
  `focus_tags`, `preferred_output_format`, `crystallize_template`, and
  `surface_confidence_threshold`. Pre-Flight step ③ loads the matching pack
  and applies it: boosts proactive recall for focus tags, compresses output
  for executives, raises confidence bar for researchers.
- **AGENTS.md** universal agent contract. Single source of truth for wiki path
  resolution, orient protocol, source attribution, core operation summary, and
  behavioral constraints. Claude Code reads SKILL.md; AGENTS.md is the portable
  reference for any future agent surface.
- **Pre-Flight Check** section in SKILL.md. Runs before Orient: verifies wiki
  directory exists, SCHEMA.md present, loads role pack, surfaces `_status.md`
  warnings. Explicit sequencing: Pre-Flight → Orient → operation.
- **Session Defaults** section in SKILL.md. Codifies wiki-first protocol
  (read wiki before answering from training data), session trust model (.wiki-path
  / SCHEMA.md / log.md are authoritative), and model routing table
  (Sonnet for I/O, Opus for reasoning/synthesis).
- **`scripts/update-safe.sh`**. Upgrade helper: detects uncommitted customizations
  in user-editable files, offers keep/backup/overwrite per file, copies safe-to-
  overwrite files from an upstream clone. Supports `--check`, `--dry-run`, `--force`.
- **`CONTRIBUTING.md`**. Contributor guide: how to add operations and workers,
  version bump protocol (semver table), testing checklist, protected conventions.

### Changed

- `plugin.json`: version 2.6.0, expanded keywords (15 total), added `metadata`
  block (skillCount, workerCount, rolePackCount, supportedAgents, directoryLayout)
  and `hooks` declaration.
- `marketplace.json`: version 2.6.0, expanded tags.
- README: layout diagram updated, new Architecture section documents worker
  agents and role packs.
- Orient step ⑧ (`_status.md`): deduped — now defers to Pre-Flight step ④
  rather than reading twice.

### Removed

- Kiro (`.kiro/`) and Gemini CLI (`.gemini/`) surface stubs. Thin wrappers
  with no real content. AGENTS.md is the portable reference if other agent
  surfaces are added later.

---

## [2.5.0] - 2026-04-21

Behavioral trust hardening. Eight features to make the wiki a reliable second brain.

### Added

- **Inline claim provenance (mandatory).** Every non-obvious factual claim now
  requires `[source: raw-slug, location]` inline markers. Frontmatter `sources:`
  alone no longer sufficient. Applies to ingest (S2 step 5) and update (S4 step 8).
- **Pre-update rollback snapshots.** Before any destructive write (overwrite,
  archive, supersede), the current page is copied to `_archive/<slug>-<date>.md`.
  Makes "undo that last change" trivial. Skipped for trivial edits (typo, date bump).
- **Concurrent session lock.** `session-start.sh` writes `.wiki-lock` with
  session ID and timestamp. `session-stop.sh` removes it. Stale locks (>2h)
  auto-cleared. Lock warning surfaced via `additionalContext` if another session
  is active.
- **Coverage markers.** New `coverage: stub | partial | comprehensive` and
  `gaps: []` frontmatter fields. Proactive Recall now surfaces coverage level.
  Used by Coverage Audit (S12).
- **Orient gate enforcement.** Hard gate: write operations (ingest, update,
  archive, supersede) refused if SCHEMA.md, index.md, and log.md have not been
  read in the current session. Read-only narrow queries exempt.
- **Confidence in Proactive Recall.** Recall now surfaces `confidence:` and
  `coverage:` from frontmatter. Rumor-grade pages always flagged.
- **Ambient capture dedup.** Before offering to capture a fact, grep wiki for
  key noun phrases. If already present, offer to update instead of creating
  duplicate.
- **S12 Coverage Audit.** New operation triggered by "what am I missing?",
  "blind spots?", "coverage gaps?". Scans coverage fields, collects gaps,
  cross-references entity mentions vs existing pages, surfaces blind spots.

### Changed

- Architecture diagram now shows `_status.md` and `.wiki-lock`.
- `_archive/` description updated: "Superseded content + pre-update snapshots".
- `when_to_use` frontmatter expanded with coverage audit triggers.
- Pitfalls section expanded with 7 new entries (snapshots, write verification,
  inline provenance, coverage markers, session lock, dedup, orient gate).
- SCHEMA.md template: added `coverage:` and `gaps:` to frontmatter spec,
  new "Coverage Markers" and "Inline Provenance" documentation sections.
- `session-start.sh`: saves stdin early for session ID extraction, writes
  lock file, surfaces lock warnings in additionalContext.
- `session-stop.sh`: releases `.wiki-lock` on session end.
- Write verification added to S4 Update: re-read after writing, confirm
  frontmatter parses before updating index/log.

---

## [2.4.0] - 2026-04-21

### Added

- `.wiki-path` file for project-specific wiki path configuration. Takes
  precedence over `CLAUDE_PLUGIN_OPTION_wiki_path` and `WIKI_PATH` env var.
- `/llm-wiki-pm:set-wiki-path` command writes `.wiki-path` to project root.

### Changed

- Wiki path resolution order: `.wiki-path` (project) > plugin option (global)
  > `WIKI_PATH` env > cwd fallback.
- Docs updated: `.wiki-path` replaces `settings.local.json` for project config.
- Strengthened skill invoke instruction in `additionalContext`: before first
  user message, regardless of content.

---

## [2.3.1] - 2026-04-21

### Added

- SessionStart `additionalContext` now instructs Claude to auto-invoke the
  skill at session start so proactive behaviors activate without user trigger.

### Fixed

- `plugin.json` and `marketplace.json` version synced to 2.3.1.
- `.gitignore` updated to exclude runtime wiki output files.

---

## [2.3.0] - 2026-04-21

### Changed

- Simplified wiki path configuration. Removed hardcoded default path.
- `systemMessage` used for unconfigured wiki path warning (separate from
  `additionalContext` health summary).
- cwd fallback when no wiki path configured.

---

## [2.2.0] - 2026-04-21

### Fixed

- `/llm-wiki-pm:set-wiki-path` now writes to correct settings scope.

---

## [2.1.2] - 2026-04-20

### Fixed

- `hooks.json` spec compliance: corrected format to match plugin system
  requirements.

---

## [2.1.1] - 2026-04-20

### Fixed

- Plugin spec compliance: corrected `plugin.json` structure.

---

## [2.1.0] - 2026-04-20

### Added

- `/llm-wiki-pm:set-wiki-path` slash command for setting wiki path from
  any project directory.
- `/llm-wiki-pm:llm-wiki-path` command to display current resolved path.
- SKILL.md: explicit `$WIKI` resolution block before any bash command.
- `pluginConfigs` format documented in `hooks/README.md` and
  `GETTING_STARTED.md`.

### Changed

- Trimmed SKILL.md wiki location section to stay under 500 lines.

---

## [2.0.1] - 2026-04-20

### Fixed

- Hook command format: removed `bash` prefix and path quotes that broke
  execution on some systems.

## [2.0.0] - 2026-04-20

Major release. Plugin architecture rebuilt from scratch. Breaking changes throughout.

### Breaking changes

- **Plugin install replaces manual setup.** Users must now install via
  `claude plugin install llm-wiki-pm@marketplace` instead of symlinking
  the skill directory. The skill-only symlink path still works but does
  not include hooks or auto-scaffold.
- **`scaffold.py` removed.** Wiki initialization is now handled automatically
  by the `SessionStart` hook on first run. No manual bootstrap command needed.
- **`hooks/hooks.json` at plugin root.** Hooks are bundled with the plugin and
  activate automatically on install. The previous approach of writing to
  `.claude/settings.json` via `scaffold.py` is gone.
- **Wiki path configured at plugin enable time.** Set via `userConfig` prompt
  (`wiki_path`, `wiki_domain`) instead of the `WIKI_PATH` env var. The env
  var still works as a fallback.

### Added

**Plugin infrastructure**
- `.claude-plugin/plugin.json`: `userConfig` fields for `wiki_path` and
  `wiki_domain`, prompted at plugin enable time. Values exposed as
  `CLAUDE_PLUGIN_OPTION_wiki_path` and `CLAUDE_PLUGIN_OPTION_wiki_domain`
  to all hook scripts.
- `hooks/hooks.json` at plugin root: correct format with outer `"hooks"` wrapper
  and `"description"` field, matching official Anthropic plugin examples.
  Events: `SessionStart`, `PostToolUse` (`Write|Edit|MultiEdit`), `SessionEnd`.
- All hook commands prefixed with `bash` so exec bit is not required after
  marketplace extraction.

**Auto-scaffold on first run**
- `session-start.sh` detects missing or empty wiki and scaffolds from templates
  automatically. Never overwrites files in an existing non-empty directory
  without `SCHEMA.md` (warns and skips instead).
- Domain substitution uses Python `str.replace()`, safe against `&`, `/`, and
  other sed metacharacters in the domain string.
- SCHEMA.md heading (`# Wiki Schema, PM`) also updated to match the domain.

**Hook correctness**
- `session-start.sh` outputs `additionalContext` JSON so Claude sees the health
  summary immediately at session start without a separate file read step.
- `post-write.sh` reads `tool_input.file_path` from stdin JSON using Python
  (no `jq` dependency). Wikilink search scoped to `entities/`, `concepts/`,
  `comparisons/`, `queries/` only — `raw/` excluded to prevent false positives.
- `session-stop.sh` counts log entries (`grep -c '^## \['`) not lines (`wc -l`).
- `lint.py`: added `--json` and `--quiet` flags. JSON output: `{broken_links,
  orphans, errors, warnings}`. Session-start hook now gets real counts instead
  of always-zero.
- `scan_dir` in `session-start.sh` uses `return 0` instead of bare `return`
  to avoid propagating non-zero exit through `set -euo pipefail`.

**Cross-platform portability**
- Replaced GNU `date -d` with Python `datetime.fromisoformat()`.
- Replaced `realpath` (not on macOS) with Python `os.path.realpath()`.
- Replaced `grep -oP` (GNU only) with Python `re.findall()`.

**Second-brain features (SKILL.md)**
- `when_to_use` and `allowed-tools` frontmatter fields added.
- §Proactive Behaviors: recall, ambient fact capture, contradiction alert,
  open question backlog, decision journaling, relationship-aware answers.
  Rate-limited: max 1 suggestion per turn, skip during code/debug tasks.
- §9 Pre-Meeting Briefing: entity brief before a call (entity page + persona
  + recent log + open questions).
- §10 Catch Me Up: log digest for last N days.
- §11 Tag Digest: synthesize any tag on demand.
- §7 Staleness Check: explicit procedure with thresholds (14d overview/index,
  30d entity/concept) and log cross-reference.
- §8 Persona Pages: tiered communication analysis (Slack DM/channel, Email
  internal/external) with cross-tier comparison table.
- Orient step: confidence decay check (competitive pages >60 days) and
  `_status.md` read from hook.
- Natural memory phrases ("remember that", "note that", "don't forget") route
  to wiki ingest when no other memory system present.

**New page types and schema fields**
- `persona` page type with structured frontmatter: `language_patterns`,
  `tone_by_channel`, `vocabulary_markers`, `code_switching`, `core_traits`.
- Person entity relationship fields: `reports_to`, `direct_reports`, `peers`,
  `interaction_frequency`.
- Source metadata fields for Slack/Gmail: `source_channel`, `source_date_range`,
  `source_thread_id`.
- `confidence_decay_days` frontmatter field for time-sensitive pages.
- `templates/persona.md`: starter template for persona pages.
- `references/persona-guide.md`: persona and relationship map authoring guide.

**Ingest improvements**
- Slack thread and Gmail chain capture patterns with dedup by `thread_ts`.
- "From this conversation" as a valid ingest source with provenance separation
  (user-stated vs tool-retrieved).
- Person entity auto-promotion rule: 2+ sources or 3+ attributes triggers entity
  page creation.
- Entity promotion scan step after every concept page write.

**Tests**
- `tests/test_hooks.py`: 43 pytest tests covering all three hook scripts and
  plugin manifest validation. Tests create isolated temp wiki fixtures and feed
  real Claude Code hook JSON payloads (matching `SessionStart`, `PostToolUse`,
  `SessionEnd` schemas).

### Fixed

- `hooks/hooks.json` was missing the outer `{"hooks": {...}}` wrapper required
  by the plugin system. Without it, all hooks silently failed to load.
  Verified against official Anthropic plugin examples.
- `post-write.sh` had dead backlinks logic: expected `{"broken": [...]}` from
  `backlinks.py` but the script returns `{"target": ..., "pages": [...]}`.
  Block removed.
- `session-start.sh` PLUGIN_ROOT computed one level too shallow (`../..`
  instead of `../../..`), causing template path resolution to fail on first run.
- `UserPromptSubmit` used instead of `SessionStart` for the health-check hook
  (fired on every message, not once per session).
- `Stop` used instead of `SessionEnd` for log rotation (fired after every turn,
  not on session terminate).
- SKILL.md contained hardcoded `/home/sil/...` paths. Replaced with
  `${CLAUDE_SKILL_DIR}/scripts/...`.
- SKILL.md was 573 lines (spec: under 500). Reduced to 496 by removing
  duplicated entity promotion block and trimming sections already covered
  in `references/`.

### Removed

- `scripts/scaffold.py`: logic absorbed into `session-start.sh`. All
  functionality preserved; no user-facing change except the file is gone.
- Backlinks check from `post-write.sh`: `backlinks.py` lists inbound links,
  not broken ones. The block was silently doing nothing.

### Documentation

- `README.md`: updated repo layout diagram, split install paths (plugin vs
  skill-only), added Tests section.
- `GETTING_STARTED.md`: Scenario 1 restructured into Path A (plugin, with
  auto-scaffold and hooks) and Path B (skill-only symlink, manual wiki setup).
  Troubleshooting updated with correct wiki path resolution order.
- `hooks/README.md`: corrected `post-write.sh` description, "500 lines" to
  "500 entries", matcher to `Write|Edit|MultiEdit`, removed false claim about
  `MultiEdit` not existing.
- `references/update-guide.md`: `backlinks.py` path uses `${CLAUDE_SKILL_DIR}`.
- `references/obsidian-sync.md`: removed hardcoded `/home/sil/` and fnm version
  from systemd unit.
- `references/lint-guide.md`: added STALE tier (active staleness with log
  correlation), updated response workflow.

---

## [1.0.0] - 2026-04-18

Initial release.

- Core skill: ingest, query, update, lint, archive, crystallize.
- Wiki structure: entities, concepts, comparisons, queries, raw sources.
- SCHEMA.md: PM-tuned tag taxonomy, page thresholds, supersession policy,
  privacy policy, confidence levels.
- `scripts/scaffold.py`: bootstrap new wiki from templates.
- `scripts/lint.py`: tiered health report (broken links, orphans, stale pages,
  tag drift) with `--auto-fix` for safe repairs.
- `scripts/backlinks.py`: show pages linking to a slug.
- Obsidian compatibility: `[[wikilinks]]`, YAML frontmatter, Dataview support.
- qmd hybrid search integration (BM25 + vector + rerank).
- `references/`: schema-guide, update-guide, lint-guide, obsidian-sync,
  privacy-guide, crystallize-guide, qmd-search, output-formats,
  nextjs-integration.
- `GETTING_STARTED.md`: full setup walkthrough and application scaffold guide.
