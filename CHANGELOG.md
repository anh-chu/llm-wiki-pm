# Changelog

All notable changes to this project.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versions follow [Semantic Versioning](https://semver.org/).

---

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
