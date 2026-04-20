---
name: llm-wiki-pm
description: Persistent PM knowledge base, competitive intel, customer notes, strategy, roadmap, AI market. Markdown wiki with entities, concepts, comparisons. Ingest sources, query, update with diffs, lint with tiered reports.
---

# LLM Wiki PM

Persistent knowledge base for PM work. Non-coding. Domain: product strategy,
competitive landscape, customer relations, roadmap, AI market, internal org.

Markdown files in a directory. Readable in Obsidian, VS Code, any editor.
The agent writes. You curate sources, ask questions, steer.

## When This Skill Activates

- User asks to ingest a source (article, report, transcript, meeting notes, PDF extract, Slack thread, Gmail chain, or current conversation) into their wiki
- User asks a question and a wiki exists at `$WIKI_PATH`
- User asks to update or revise a page with new info
- User asks to lint, audit, or health-check the wiki
- User asks to create or bootstrap a PM wiki
- User references "my wiki", "the wiki", "knowledge base", "notes" in a PM context
- User asks to build a persona or communication profile for a person
- User asks to map relationships or org hierarchy in the wiki

## Wiki Location

```bash
WIKI="${WIKI_PATH:-$HOME/llm-wiki-pm/wiki}"
```

Set `WIKI_PATH` in your shell rc (`~/.bashrc`, `~/.zshrc`). Default: `$HOME/llm-wiki-pm/wiki`.

## Architecture: Three Layers

```
wiki/
├── SCHEMA.md              # Conventions, domain config, tag taxonomy
├── index.md               # Sectioned content catalog
├── overview.md            # Evolving synthesis, single entry point
├── log.md                 # Append-only action log (rotate at 500)
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
└── _archive/              # Superseded content
```

**Layer 1 raw/**: immutable. Agent reads, never modifies.
**Layer 2 wiki pages**: agent-owned. Created, updated, cross-referenced.
**Layer 3 SCHEMA.md**: governs structure and taxonomy.

## CRITICAL: Orient Every Session

Before any ingest/query/update/lint, **always**:

① Read `SCHEMA.md`, domain, conventions, tag taxonomy
② Read `index.md`, what pages exist
③ Read last 20-30 lines of `log.md`, recent activity
④ Read `overview.md`, current synthesis state
⑤ For 100+ page wikis: `grep -r "topic" $WIKI --include="*.md"` before creating
⑥ **Staleness warning**: if any page has `updated:` older than 14 days
   (overview/index) or 30 days (entity/concept pages) AND log.md shows recent
   activity touching that area, surface: "Warning: [[page]] may be stale.
   Last updated YYYY-MM-DD. Recent log activity: [date, action]."

Skipping orientation → duplicate pages, missed cross-refs, schema drift.

## Core Operations

### 1. Initialize (new wiki)

Use `scripts/scaffold.py`:

```bash
python3 /home/sil/llm-wiki-pm/skills/llm-wiki-pm/scripts/scaffold.py "$WIKI" "PM, Katalon"
```

Ask user to confirm domain scope. Customize `SCHEMA.md` tag taxonomy for their
domain (see `templates/SCHEMA.md` for PM-tuned defaults).

### 2. Ingest a source

① **Capture raw** (choose source type):
   - URL → `web_fetch` → save markdown to `raw/articles/<slug>.md`
   - PDF → extract text → `raw/papers/<slug>.md` (keep PDF in `raw/assets/`)
   - Paste/transcript → `raw/transcripts/<slug>.md`
   - **Slack thread**: copy thread messages → `raw/internal/<channel>-<date>.md`.
     Add frontmatter: `source_channel: "#channel-name"`, `source_date_range: "YYYY-MM-DD"`,
     `source_thread_id: "<thread_ts>"`. Dedup: before saving, grep wiki for same
     thread_ts to avoid double-ingest. Strip @mentions to initials if private.
   - **Gmail chain**: export thread text → `raw/internal/email-<subject-slug>-<date>.md`.
     Add frontmatter: `source_channel: "Gmail"`, `source_date_range: "YYYY-MM-DD/YYYY-MM-DD"`,
     `source_thread_id: "<gmail-thread-id>"`. Strip external email addresses if sensitive.
   - **Current conversation**: when user says "from this conversation" or "use what
     we discussed", treat the session as a source. Save a summary to
     `raw/internal/conversation-<YYYY-MM-DD>.md`. Distinguish:
       - User-stated facts: attribute as `user, <date>`
       - Tool-retrieved (Slack, Gmail, web_fetch): attribute to original source
     Do not collapse these. Keep provenance separate in the raw file.
   - Name descriptively: `raw/articles/gartner-test-automation-mq-2026.md`
   - **Privacy filter (mandatory)**: strip API keys, tokens, passwords from raw.
     If the source contains customer-identifying info, deal sizes, 1:1 content,
     or internal-only strategy, set `private: true` on resulting wiki pages.

② **Surface takeaways to user BEFORE writing wiki pages.** What's interesting?
   What matters for the PM domain? Which entities/concepts does this touch?
   (Skip in automated/batch contexts.)

③ **Check existing pages**: `grep -r` for every entity/concept mentioned.
   Read existing pages before deciding create vs update.

④ **Apply Page Thresholds** (from SCHEMA.md):
   - Create entity page only if 2+ sources mention OR central to current source
   - **People specifically**: create a person entity page when a person appears
     in 2+ sources, has a named role, or is central to a relationship being mapped.
     Don't wait for the user to ask. Apply the same 2+ threshold proactively.
   - Passing mentions in footnotes don't warrant pages
   - Update existing pages rather than duplicating

⑤ **Write/update pages:**
   - Required frontmatter (title, created, updated, type, tags, sources)
   - Tags MUST come from SCHEMA.md taxonomy, add new tags there first
   - Minimum 2 outbound `[[wikilinks]]` per page
   - Contradictions → note both positions with dates + sources, add
     `contradictions: [page-name]` to frontmatter, flag in log
   - Supersession: if a new page materially *replaces* (not just revises) an
     old one, set `supersedes: [old-slug]` on new page, `superseded_by: new-slug`
     on old page. Archive the old page. `lint --auto-fix` rewrites inbound links.

⑥ **Backlink audit**: after creating a page, scan related pages and add
   inbound `[[links]]` so the new page isn't an orphan.

⑧ **Entity promotion scan**: after writing or updating any concept page, scan
   for named people, companies, and products described with 3+ distinct attributes
   (role, decisions, style, concerns, history, etc.) inline.
   - Count how many entities meet that threshold.
   - If any do, prompt: "N entities on this page meet the entity threshold.
     Create individual entity pages?"
   - Create entity pages for confirmed items. Link the concept page out to each
     new entity page instead of keeping the prose inline.
   - For promoted person entities: check whether a persona page is warranted
     (see §8 Persona Pages).

⑧ **Update `overview.md`**: if the source shifts the domain synthesis, edit
   the overview. Keep it under 200 lines. Link heavily.

⑨ **Update navigation:**
   - Add new pages to `index.md` under correct section, alphabetical
   - Bump total page count + "Last updated" header
   - Append to `log.md`: `## [YYYY-MM-DD] ingest | <source title>` with list
     of every file created/updated

①⓪ **Report to user**: list every file touched. One source → 5-15 pages is
   normal. Confirm before mass-updating (10+ pages).
①① **Crystallize (for transcripts and research chains)**: when ingesting a
   meeting transcript, 1:1 notes, or a multi-source research thread, also
   produce a distilled digest page under `queries/`:
   ```markdown
   ---
   title: Crystallize: <Topic or Meeting>
   type: query
   tags: [decision, timeline]
   sources: [raw/transcripts/<slug>.md]
   private: true  # if sensitive
   ---
   ## Context
   ## Decisions
   ## Action Items (owner + date)
   ## Open Questions
   ## Lessons / Patterns
   ```
   Link from affected entity/concept pages back to the crystallize page.
   This is how exploration compounds into the wiki, not just raw ingests.

①② **Entity promotion scan** (after every ingest): scan pages you just created
   or updated for named people, companies, and products described with 3+ attributes
   (role, style, concerns, position, history, etc.).
   - If found in a concept page: prompt user, "X entities in [[page]] meet the
     entity threshold. Create individual entity pages?"
   - Don't silently promote. Always confirm.
   - After splitting, update the concept page to link out: `[[entity-slug]]`
     instead of the inline prose.
   - Check whether a persona page is warranted for any promoted person entity
     (see §8 Persona Pages).

### 3. Query
② **Primary search: qmd MCP tools** (`query`, `get`, `multi_get`). Use qmd
   for any "what do we know about X" question. Falls back to grep + index.md
   only if qmd unavailable. See `references/qmd-search.md`.
③ Read `index.md` to confirm page catalog for top hits
④ Read relevant pages via file reads or `qmd get`
⑤ Synthesize. Cite pages: "Per [[tricentis]] and [[test-automation-mq]]..."
⑥ **Select output format** based on question and audience:
   - Plain markdown answer inline → most queries
   - File under `queries/<slug>/README.md` → substantial syntheses
   - Add artifacts (Marp deck / matplotlib chart / CSV / Mermaid) if the
     audience or question warrants it. See `references/output-formats.md`.
⑦ **File valuable answers back**: substantial comparisons, deep dives,
   novel synthesis. Skip trivial lookups.
⑧ Append to `log.md`: `## [YYYY-MM-DD] query | <question> (filed: yes/no)`
⑨ After filing a new page: `qmd update && qmd embed` (or rely on systemd
   watcher if configured) so the next query sees it.

### 4. Update (revise existing pages)

Separate discipline from ingest. Triggered when new info conflicts with or
refines existing content.

① **Identify all affected pages**: three-way search:
   - `scripts/backlinks.py $WIKI <slug>` for structural backlinks (pages
     linking to the entity being revised)
   - `qmd query` for semantic variants (paraphrases of the stale claim)
   - `grep -r` for exact token match (dollar figures, codenames)
   Don't update one page and leave 3 others with the stale version.

② **Show diff BEFORE writing**: present old text, new text, reason. Confirm
   with user for any claim touching 5+ pages or changing stated strategy.

③ **Cite source**: every update must include the raw source that justifies
   the change in the page body and in the log entry.

④ **Stale-claim sweep**: after update, re-search (qmd query + grep for
   exact variants) across the wiki. Fix all instances in the same pass.

⑤ **Bump `updated:` date** on every page touched.

⑥ **Log**: `## [YYYY-MM-DD] update | <claim/page> | source: raw/...`
   List every file modified.

### 5. Lint (tiered report)

Use `scripts/lint.py`, writes report to `wiki/queries/lint-YYYY-MM-DD.md`
with severity tiers. Offers concrete fixes. Logs unconditionally.

```bash
python3 /home/sil/llm-wiki-pm/skills/llm-wiki-pm/scripts/lint.py "$WIKI"
```

Checks:
1. 🔴 Broken `[[wikilinks]]` pointing to non-existent pages
2. 🔴 Missing required frontmatter fields
3. 🔴 Tags not in SCHEMA.md taxonomy
4. 🟡 Orphan pages (zero inbound links)
5. 🟡 Pages not in `index.md` (or vice versa)
6. 🟡 Pages > 200 lines (split candidates)
7. 🟡 Contradictions flagged in frontmatter but unresolved
8. 🟡 Stale pages (updated > 90 days, no correlated log activity)
9. 🟠 Stale overview/index (updated > 14 days, log shows recent activity)
10. 🟠 Stale entity/concept/comparison (updated > 30 days, log shows recent activity)
11. 🔵 Tag usage frequency (taxonomy tuning)
12. 🔵 Log size > 500 entries (rotation due)

Read the report, act on 🔴 items, investigate 🟠 stale pages, discuss 🟡 with user, note 🔵 for later.

### 6. Archive

Superseded or out-of-scope content:
1. Create `_archive/` if missing
2. Move page preserving path (`_archive/entities/old.md`)
3. Remove from `index.md`
4. Update inbound linkers: replace `[[old]]` with plain text "(archived)"
5. Log archive action with reason

### 7. Staleness Check

Run when: user asks "is the wiki up to date?", "what needs updating?", or after
an extended gap in wiki activity. Also runs automatically during orient (step ⑥).

① **Scan frontmatter dates**: read `updated:` from all pages in `entities/`,
   `concepts/`, `comparisons/`, `overview.md`, and `index.md`.

② **Apply thresholds**:
   - `overview.md`, `index.md`: stale if `updated:` > 14 days ago
   - `entities/`, `concepts/`, `comparisons/`: stale if `updated:` > 30 days ago

③ **Cross-reference log.md**: for each stale page, check whether log.md has
   entries in the past 30 days referencing that entity or topic. Log activity
   with no page update means the page is likely behind, not just dormant.

④ **Surface findings** to user:
   - "X pages haven't been updated in Y+ days" (grouped by type)
   - Highlight pages where log.md shows activity but `updated:` hasn't moved
   - Suggest the 2-3 most likely candidates for updates based on log recency

⑤ **Offer update flow**: for each flagged page, offer to run the Update flow (§4)
   or open the page for manual review.

⑥ **Log**: append staleness check to `log.md` regardless of whether updates follow.

### 8. Persona Pages

Build when: user asks for a communication profile, style analysis, or persona
for a person. Also triggered after promoting a person entity when 3+ attributes
exist about their communication style.

① **Confirm data sources**: ask user which communication tiers have actual
   source material. Don't fabricate tiers you have no data for.
   Typical tiers: Slack DM, Slack channel, Email internal, Email external.

② **Gather source material**: ingest any Slack threads, email chains, or
   conversation content via §2 ingest flow before writing the persona page.

③ **Write persona page** at `entities/<name>-persona.md`:
   - Type: `persona`. Link to `[[<name>]]` entity in frontmatter `sources:`.
   - Core traits summary (3-5 sentences, no bullet spray).
   - One section per tier with data. Format per tier:
     ```
     ### Slack DM
     - Formality: informal
     - Sentence length: short, often 1 line
     - Humor: dry, occasional
     - Sign-off: none typical
     - Notes: mixes Vietnamese in casual threads
     ```
   - Cross-tier comparison table at the bottom:
     | Dimension | Slack DM | Slack channel | Email internal | Email external |
     |-----------|----------|---------------|----------------|----------------|
     | Formality | ... | ... | ... | ... |
     | Length | ... | ... | ... | ... |
     | Humor | ... | ... | ... | ... |
     | Sign-off | ... | ... | ... | ... |

④ **Link persona to person entity**: add `[[<name>-persona]]` to the person
   entity page under Relationships or a "Communication profile" section.

⑤ **Relationship map**: when 3+ person entity pages exist, check whether
   `concepts/relationship-map.md` exists. If not, offer to create it.
   Format: markdown table with columns Name, Role, Reports to, Peers,
   Interaction frequency. Update when new person entities are added.

⑥ **Log**: `## [YYYY-MM-DD] persona | <name>-persona | tiers: [list]`

```
## [YYYY-MM-DD] staleness-check | X stale pages found | updated: [slugs] or none
```
## PM Workflow Patterns

**Weekly competitive digest:** user drops 3-5 analyst links → ingest all →
batch entity updates → one log entry → overview.md refresh.

**Pre-meeting prep:** query "what do we know about <customer>?" → read
`entities/<customer>.md` → check recent log entries for updates → offer to
file post-meeting notes back into the customer page via update flow.

**1:1 follow-up (Vu Lam monthly):** ingest transcript to
`raw/transcripts/vu-lam-1-1-YYYY-MM.md` → extract decisions/themes → update
`concepts/<theme>.md` pages → link from `entities/vu-lam.md`.

**Quarterly lint:** run lint, triage 🔴, discuss 🟡 trends, rotate log if
needed, refresh overview.md.

## Multi-Device Access (Obsidian + obsidian-headless)

Wiki dir = Obsidian vault. `[[wikilinks]]` render, Graph View works, YAML
frontmatter powers Dataview.

Server-side sync without GUI:

```bash
npm install -g obsidian-headless
ob login --email <email> --password '<pw>'
ob sync-create-remote --name "PM Wiki"
cd "$WIKI" && ob sync-setup --vault "<vault-id>"
ob sync --continuous
```

Systemd unit for background:

```ini
# ~/.config/systemd/user/obsidian-pm-sync.service
[Unit]
Description=Obsidian PM Wiki Sync
After=network-online.target

[Service]
ExecStart=/usr/bin/ob sync --continuous
WorkingDirectory=%h/llm-wiki-pm/wiki
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
```

```bash
systemctl --user enable --now obsidian-pm-sync
sudo loginctl enable-linger $USER
```

Now Claude Code writes on laptop, Obsidian mobile reads within seconds ,
handy for pre-meeting glance.

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
- **Privacy by default**: customer names, deal sizes, 1:1 content = `private: true`.
  When in doubt, mark private. Exports/shares respect the flag.
- **Supersede, don't silently rewrite**: materially replacing a page needs
  explicit `supersedes:` / `superseded_by:` fields. Old page archived, not deleted.
- **Use qmd first**: grep misses semantic matches. At dozens of meetings/week
  the wiki grows fast; grep + index alone will silently degrade quality.

## References

- `references/schema-guide.md`, customizing SCHEMA.md for your domain
- `references/update-guide.md`, diff discipline, stale-claim sweep patterns
- `references/lint-guide.md`, interpreting tiered reports
- `references/persona-guide.md`, building persona and relationship map pages
- `references/obsidian-sync.md`, headless sync deep dive
- `references/privacy-guide.md`, pre-ingest filter + `private:` flag
- `references/crystallize-guide.md`, transcript → decision digest pattern
- `references/qmd-search.md`, primary search engine setup and use
- `references/output-formats.md`, Marp, matplotlib, CSV, Mermaid, Canvas
- `references/nextjs-integration.md`, embed graph + page viewer in a Next.js app

## Scripts

- `scripts/scaffold.py <path> <domain>`, bootstrap new wiki
- `scripts/lint.py <path>`, tiered health report
- `scripts/backlinks.py <path> <slug>`, show pages linking to a slug.
  Use `--context` for line-level matches, `--json` for agent consumption.
- `scripts/lint.py <path> --auto-fix`, repair safe issues (supersession
  link redirects, index backfill)
