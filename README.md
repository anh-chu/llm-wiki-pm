# llm-wiki-pm
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/anh-chu/llm-wiki-pm)](https://github.com/anh-chu/llm-wiki-pm/releases)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-orange)](https://docs.claude.com/en/docs/claude-code/skills)
[![Stars](https://img.shields.io/github/stars/anh-chu/llm-wiki-pm?style=social)](https://github.com/anh-chu/llm-wiki-pm/stargazers)

> A PM knowledge base that stays correct as it grows. Ingest meetings,
> analyst reports, and strategy docs into a plain Markdown wiki, then work
> with it from Claude Code or ChatGPT. Every write follows the same rules:
> cited sources, snapshots before overwrites, explicit supersession, lint.

Based on [Andrej Karpathy's LLM Wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f),
tuned for product management: competitive intel, customer notes, strategy,
roadmap, AI market tracking.

## Why

Most PM work today spreads across Slack threads, meeting transcripts, analyst
PDFs, and one-off notes. RAG tools like NotebookLM retrieve from raw sources
each query, so knowledge never compounds. Personal wikis fail because the
bookkeeping overhead outgrows the value.

This skill gives you the middle path: you curate sources, the agent maintains
an interlinked markdown wiki that stays current. Every ingest touches 5-15
pages. Every query cites specific wiki entries. The wiki compounds.

Letting an agent write is the easy part. Keeping months of agent writes
trustworthy is the hard part, and it is where most memory tools stop. Here,
when a fact changes the old page is superseded and its inbound links are
rewritten rather than silently overwritten. Every claim points back to an
immutable source in `raw/`, every overwrite leaves a snapshot in `_archive/`,
and lint flags stale pages, broken links, and off-schema tags. The same rules
apply whether the write comes from Claude Code or from ChatGPT through the
bundled [wiki-mcp server](server/README.md).

## What you get

- **Three-layer architecture**: immutable `raw/` sources, agent-owned wiki
  pages, and `SCHEMA.md` governing structure
- **Ingest / query / update / lint / archive** flows with discipline guardrails
- **Supersession** with auto-redirect of inbound links
- **Crystallize** pattern: transcripts become structured decision digests
- **Privacy-first**: pre-ingest filter, and every page is private (excluded from exports) unless it carries `shareable: true`
- **Bundled wiki-search**: ranked keyword, regex, tag and backlink search over your whole wiki, via [obsidian-mcp](https://github.com/lstpsche/obsidian-mcp) (auto-indexes on startup)
- **ChatGPT access via [wiki-mcp](server/README.md)**: a remote MCP server behind Cloudflare Access. Read tools by default; with `WIKI_WRITE=1` it adds create, edit, append, archive, supersede, and raw capture, each validated against `SCHEMA.md`, snapshotted, and logged the same way Claude Code writes are
- **Obsidian-compatible**: works as a vault out of the box
- **Prompt recall**: each prompt that names a page, or matches pages closely, lists up to 3 of them in context, so the agent reads the wiki before asking you
- **Sub-skills** (optional, install as needed):
  - `llm-wiki-brief` — daily/weekly briefs, tag digests, coverage brief
  - `llm-wiki-research` — research sprints, competitive deep dives, stub enrichment
  - `llm-wiki-maintain` — the daily-maintenance loop (registry-driven sweep → ingest → brief → tidy → health check), with interactive vs autonomous modes
- **MY-INTEGRATIONS.md**: learned source routing — auto-populated from actual ingest activity
- **Next.js embed path** for platform deployments

## Install

### Option A: Claude Code plugin (recommended)

```bash
claude plugin marketplace add anh-chu/llm-wiki-pm
claude plugin install llm-wiki-pm@anh-chu-plugins
```

### Option B: Standalone skill via `npx skills`

```bash
npx skills add anh-chu/llm-wiki-pm --skill llm-wiki-pm -a claude-code -g
```

Install individual sub-skills the same way:

```bash
npx skills add anh-chu/llm-wiki-pm --skill llm-wiki-research -a claude-code -g
npx skills add anh-chu/llm-wiki-pm --skill llm-wiki-brief -a claude-code -g
```

This installs the skill with all its scripts, templates, and references. **What you don't get** without the full plugin: session hooks (auto-scaffold, prompt recall, wikilink validation, log rotation) and the bundled wiki-search. Core wiki operations (ingest, query, update, lint) work fine — you just need to create the wiki directory structure manually on first use.

### Option C: Symlink from a clone

```bash
git clone https://github.com/anh-chu/llm-wiki-pm ~/llm-wiki-pm
mkdir -p ~/.claude/skills
ln -s ~/llm-wiki-pm/skills/llm-wiki-pm ~/.claude/skills/llm-wiki-pm
```

Same trade-offs as Option B. For hook automation and auto-scaffold, also install the plugin:

```bash
claude plugin install llm-wiki-pm@anh-chu-plugins
```

### Then: start Claude Code
Restart Claude Code after enabling the plugin. You will be prompted for your wiki path and domain. The `SessionStart` hook creates the wiki directory on the first session start.

If you used Option B without installing the plugin, set `WIKI_PATH` before starting Claude Code:
```bash
echo 'export WIKI_PATH=$HOME/pm-wiki' >> ~/.bashrc && source ~/.bashrc
```

Full setup, including mobile Obsidian sync, in
[GETTING_STARTED.md](GETTING_STARTED.md).

## How it compares

| | llm-wiki-pm | [kfchou/wiki-skills](https://github.com/kfchou/wiki-skills) | [lewislulu/llm-wiki-skill](https://github.com/lewislulu/llm-wiki-skill) | [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki) | NotebookLM |
|---|---|---|---|---|---|
| **Shape** | Single skill | 5 skills | Skill + plugin + server | Full web app | SaaS |
| **Storage** | Plain markdown | Plain markdown | Plain markdown | Supabase + S3 | Cloud |
| **Search** | Bundled BM25 + regex + tags (wiki-search) + backlinks | grep + index | grep + index | PGroonga | Proprietary |
| **Update discipline** | Diffs + supersession fields + auto-link rewrite | Diffs + source cite | Human-in-loop audit | None explicit | N/A |
| **Privacy** | Pre-ingest filter + private by default (`shareable:` allowlist) | None | None | User-scoped | SaaS ToS |
| **Transcript support** | `crystallize` flow (decisions + actions) | Generic ingest | Generic ingest | Generic ingest | Source-only |
| **Install target** | Claude Code, plus ChatGPT via wiki-mcp | Claude Code | OpenClaw / Codex | Self-host web | SaaS |
| **Ops burden** | None (local files) | None | Obsidian plugin + Node server | Supabase + S3 + OCR | Zero |
| **Scales to 1000+ pages** | Yes (wiki-search, bundled) | Degrades | Degrades | Yes | Yes |
| **PM-tuned taxonomy** | Yes (competitive, customer, strategy, roadmap, ai) | No | No | No | No |

For a deeper breakdown of which Karpathy and Rohit v2 ideas this implements,
see the [design notes](#design-notes) below.

## Benchmarks

Retrieval quality was measured on a real working wiki (about 700 Markdown
files, 11 MB, 325 of them raw sources) with 26 known-answer questions
written from the raw sources: obscure facts, paraphrases, multi-document
answers, facts that changed over time, and renamed concepts. Scoring is
automatic (no LLM judge). Queries were short keyword or natural-language
phrases written blind by a separate agent, the way an agent would search.

| Search backend | Hit@10 | Hit@1 | Idle RAM |
|---|---|---|---|
| [@wirux/mcp-markdown-vault](https://www.npmjs.com/package/@wirux/mcp-markdown-vault) (bundled before 2.23) | 69-77% | 50-54% | ~580 MB |
| [obsidian-mcp](https://github.com/lstpsche/obsidian-mcp), BM25 only (bundled since 2.23) | 65-77% | 38-42% | ~80 MB |
| obsidian-mcp, with embeddings | 69-77% | 42-46% | ~1.2 GB |
| [Basic Memory](https://github.com/basicmachines-co/basic-memory), hybrid | 50-54% | 19-27% | ~505 MB |

Hit@10 means a file holding the answer appears in the top 10 results. On
this corpus the two plain-files engines came out ahead, at similar
quality, with no database involved. Credit for that goes to the search
projects themselves:
[@wirux/mcp-markdown-vault](https://www.npmjs.com/package/@wirux/mcp-markdown-vault)
and [obsidian-mcp](https://github.com/lstpsche/obsidian-mcp), which now
backs both the bundled wiki-search and [wiki-mcp](server/README.md). This
skill adds the structure and update rules around them, not the ranking.

Read these numbers with some care:

- 26 questions is a small set. One question is about 4 points, so gaps under
  roughly 10 points are noise.
- Questions about facts that changed over time or concepts that were
  renamed scored lowest for every backend tested (about half). Search
  alone does not fix those; they depend on the supersession and update
  rules in this skill.
- On a fresh copy of a wiki, mcp-markdown-vault's first full index
  stopped at about half the files with no error. That, its memory use, and
  its open write bugs are why 2.23 switched the bundled search to
  obsidian-mcp, which indexed every page in about 3 seconds.

## Target users

Good fit if you:

- Work as a PM, analyst, researcher, or founder with lots of meetings and reports
- Want a local-first, markdown-based knowledge base that you own
- Use Claude Code as your primary agent, optionally with ChatGPT as a second client
- Are comfortable on a terminal (you'll occasionally run `lint.py`, and ChatGPT access means running a small server behind a reverse proxy)

Not a fit if you:

- Want a zero-terminal SaaS → use NotebookLM
- Need team collaboration out of the box → use Notion or a shared Obsidian vault
- Don't use Claude Code → ChatGPT can read and write through wiki-mcp, but the skills, hooks, and sub-skill workflows are Claude Code only. `AGENTS.md` is the portable reference if you want to port to another agent

## Layout

```
llm-wiki-pm/
├── AGENTS.md                        # Universal agent behavioral contract
├── CONTRIBUTING.md
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── hooks/
│   └── hooks.json
├── scripts/
│   └── update-safe.sh
└── skills/
    ├── llm-wiki-pm/                 # Core skill (required)
    │   ├── SKILL.md
    │   ├── hooks/   (session-start.sh, post-write.sh, session-stop.sh)
    │   ├── references/
    │   ├── scripts/ (lint.py, backlinks.py)
    │   └── templates/ (SCHEMA.md, index.md, overview.md, log.md, persona.md,
    │                    MY-INTEGRATIONS.md)
    ├── llm-wiki-brief/              # Optional: daily/weekly briefs, tag digests
    │   └── SKILL.md
    ├── llm-wiki-research/           # Optional: research sprints, competitive deep dives
    │   └── SKILL.md
    └── llm-wiki-maintain/           # Optional: daily-maintenance loop (sweep→ingest→brief→tidy)
        └── SKILL.md
```

## Setup

Two scenarios documented in detail in [GETTING_STARTED.md](GETTING_STARTED.md):

1. **Human user with Claude Code**: enable plugin, wiki auto-scaffolds on first session
2. **Application-orchestrated**: programmatic wiki provisioning for platform deployments

## Quick Start

### 1. Bootstrap a wiki
Enable the plugin. When prompted, enter your wiki path and domain.
On the first session start, the `SessionStart` hook creates:
`~/pm-wiki/` with SCHEMA.md, index.md, log.md, overview.md, and
the raw/entities/concepts/comparisons/queries/_archive subdirectories.

### 1b. Wiki search (bundled, automatic)

Ranked keyword (BM25), regex, tag and wikilink search over your wiki is
bundled as `wiki-search`, backed by
[obsidian-mcp](https://github.com/lstpsche/obsidian-mcp). The first session
downloads a pinned, checksum-verified binary (21 MB download, 64 MB
unpacked) to `~/.cache/llm-wiki-pm/`; if `obsidian-mcp` 3.x is already on
your PATH it is used instead. Each Claude Code session runs its own copy,
which builds the index in memory in seconds at startup. obsidian-mcp keeps
its data folder in `~/.local/share/obsidian-mcp/` but still creates a small
`.obsidian-mcp/` folder in the wiki (add it to `.gitignore`). Needs
`python3` (already required by the hooks), which trims search results to a
few snippets per file. `_archive/` snapshots are left out of search;
`note_read` still opens them by path.

### 2. Review SCHEMA.md

Open `~/pm-wiki/SCHEMA.md`. Adjust:
- Domain statement (scope)
- Tag taxonomy (add/remove tags for your specific accounts, competitors, themes)
- Page thresholds (tune later after a few ingests)

### 3. Install as Claude Code skill

Option A, user-level (available in every project):
```bash
mkdir -p ~/.claude/skills
ln -s /home/sil/llm-wiki-pm/skills/llm-wiki-pm ~/.claude/skills/llm-wiki-pm
```

Option B, project-level (per-repo):
```bash
mkdir -p .claude/skills
ln -s /home/sil/llm-wiki-pm/skills/llm-wiki-pm .claude/skills/llm-wiki-pm
```

Restart Claude Code. Verify with `/skills`, `llm-wiki-pm` should appear.
The skill auto-activates on ingest/query/update/lint phrasing (see SKILL.md
"When This Skill Activates").

### 4. First ingest

In Claude Code:

> "Ingest this Gartner Magic Quadrant report: <paste or path>"

Claude reads SKILL.md, orients on SCHEMA + index + log + overview, surfaces
takeaways, creates/updates pages, logs.

### 5. Run lint periodically

```bash
python3 /home/sil/llm-wiki-pm/skills/llm-wiki-pm/scripts/lint.py ~/pm-wiki
# opens queries/lint-YYYY-MM-DD.md
```

### 6. Mobile access (optional)

See `references/obsidian-sync.md` for obsidian-headless + systemd setup.

## Workflow Patterns

**Weekly competitive digest**: ingest 3-5 analyst links in one session.
Batch updates, one log entry, refresh overview.md.

**Pre-meeting prep**: query "what do we know about <customer>?" → Claude
reads `entities/<customer>.md` + recent log → offer to file post-meeting update.

**Monthly 1:1 follow-up**: ingest transcript → extract decisions/themes →
update relevant concept pages → link from person page.

**Quarterly review**: lint, triage, rotate log, refresh overview, prune
tag taxonomy.

## Scope

Wiki = long-term curated facts + sources you review, cite, and share with
colleagues. Not a replacement for session memory or notes apps. If you pair
with a memory tool (Claude's native memory, mem0, Hindsight), keep them
non-overlapping: wiki holds facts + sources, memory holds persona + session
state.

## License

## Tests

Hook scripts and plugin manifest validation:

```bash
python3 -m venv .venv && .venv/bin/pip install pytest -q
.venv/bin/python -m pytest tests/ -v
```

43 tests covering scaffold, wikilink validation, log rotation, stdin parsing,
and plugin manifest compliance. All tests create isolated temp wikis and feed
the real Claude Code hook JSON schema to the scripts.

MIT.

## Credits

Built on prior art from:

- **[Andrej Karpathy, LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)**
 , the original pattern: stop re-deriving, start compiling. Three-layer
  architecture, Memex lineage, and the insight that LLMs are the first
  librarians who don't get bored of bookkeeping.
- **[Rohit G, LLM Wiki v2](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2)**
 , lifecycle concepts (supersession, privacy, crystallization, self-healing
  lint). We cherry-picked the four highest-ROI v2 ideas for PM work.
- **[kfchou/wiki-skills](https://github.com/kfchou/wiki-skills)**: update
  discipline with diffs and stale-claim sweep, tiered lint reports, evolving
  `overview.md` synthesis.
- **[lewislulu/llm-wiki-skill](https://github.com/lewislulu/llm-wiki-skill)**
 , audit/feedback loop design (inspiration for future team-mode support).
- **[obsidian-mcp](https://github.com/lstpsche/obsidian-mcp)**: BM25, regex
  and wikilink search over markdown vaults (bundled as wiki-search, and the
  backend of wiki-mcp).
- **[@wirux/mcp-markdown-vault](https://github.com/Wirux/mcp-markdown-vault)**:
  semantic + TF-IDF search, bundled as wiki-search up to 2.22.

## Design notes

How this skill maps to Karpathy's original gist and Rohit's v2 extensions:

### Karpathy core (10/10)

- Three-layer architecture (raw sources, agent-owned wiki, schema)
- LLM owns the wiki; human curates sources
- Ingest / query / lint operations
- `index.md` content catalog + `log.md` chronological record
- File good answers back as pages (`queries/` dir)
- Obsidian compatibility (Graph, Dataview, frontmatter)
- Schema as key configuration, co-evolved
- Ingests touch 10-15 pages routinely
- Bundled wiki-search via `obsidian-mcp`
- Multi-format outputs: [Marp, matplotlib, CSV, Mermaid, Canvas](references/output-formats.md)

### v2 cherry-picks (7/16)

Implemented:

- Explicit supersession with `supersedes:` / `superseded_by:` fields + auto-redirect
- Privacy filter (pre-ingest checklist + private-by-default `shareable:` allowlist)
- Self-healing lint (`--auto-fix` for safe repairs)
- Crystallization (transcript → decision digest)
- Schema as the real product
- Contradiction handling with frontmatter flag
- Backlink tracing (`scripts/backlinks.py` for structural refs)

Intentionally skipped for solo PM use (overkill):

- Confidence decay curves
- Consolidation tiers (working/episodic/semantic/procedural memory)
- Typed knowledge graph with relationship types
- Multi-agent mesh sync
- Quality scoring pipeline
