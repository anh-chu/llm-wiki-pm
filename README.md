# llm-wiki-pm
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Release](https://img.shields.io/github/v/release/anh-chu/llm-wiki-pm)](https://github.com/anh-chu/llm-wiki-pm/releases)
[![Claude Code](https://img.shields.io/badge/Claude%20Code-skill-orange)](https://docs.claude.com/en/docs/claude-code/skills)
[![Stars](https://img.shields.io/github/stars/anh-chu/llm-wiki-pm?style=social)](https://github.com/anh-chu/llm-wiki-pm/stargazers)

> A Claude Code skill that turns your PM work into a persistent, compounding
> knowledge base. Ingest meetings, analyst reports, and strategy docs.
> Query across months of context. Let the agent handle the bookkeeping.

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

## What you get

- **Three-layer architecture**: immutable `raw/` sources, agent-owned wiki
  pages, and `SCHEMA.md` governing structure
- **Ingest / query / update / lint / archive** flows with discipline guardrails
- **Supersession** with auto-redirect of inbound links
- **Crystallize** pattern: transcripts become structured decision digests
- **Privacy-first**: pre-ingest filter + `private:` frontmatter flag
- **qmd search**: BM25 + vector + LLM rerank over your whole wiki
- **Obsidian-compatible**: works as a vault out of the box
- **Next.js embed path** for platform deployments

## Install

### Option A: Claude Code plugin (recommended)

```bash
claude plugin marketplace add anh-chu/llm-wiki-pm
claude plugin install llm-wiki-pm@anh-chu/llm-wiki-pm
```

### Option B: Symlink from a clone

```bash
git clone https://github.com/anh-chu/llm-wiki-pm ~/llm-wiki-pm
mkdir -p ~/.claude/skills
ln -s ~/llm-wiki-pm/skills/llm-wiki-pm ~/.claude/skills/llm-wiki-pm
```

### Then: bootstrap your first wiki

```bash
python3 ~/llm-wiki-pm/skills/llm-wiki-pm/scripts/scaffold.py ~/pm-wiki "My PM Domain"
echo 'export WIKI_PATH=$HOME/pm-wiki' >> ~/.bashrc && source ~/.bashrc
# Restart Claude Code, then say:
#   "Ingest this analyst report: <paste url>"
```

Full setup, including qmd search and mobile Obsidian sync, in
[GETTING_STARTED.md](GETTING_STARTED.md).

## How it compares

| | llm-wiki-pm | [kfchou/wiki-skills](https://github.com/kfchou/wiki-skills) | [lewislulu/llm-wiki-skill](https://github.com/lewislulu/llm-wiki-skill) | [lucasastorian/llmwiki](https://github.com/lucasastorian/llmwiki) | NotebookLM |
|---|---|---|---|---|---|
| **Shape** | Single skill | 5 skills | Skill + plugin + server | Full web app | SaaS |
| **Storage** | Plain markdown | Plain markdown | Plain markdown | Supabase + S3 | Cloud |
| **Search** | qmd (BM25+vector+rerank) + backlinks | grep + index | grep + index | PGroonga | Proprietary |
| **Update discipline** | Diffs + supersession fields + auto-link rewrite | Diffs + source cite | Human-in-loop audit | None explicit | N/A |
| **Privacy** | Pre-ingest filter + `private:` flag | None | None | User-scoped | SaaS ToS |
| **Transcript support** | `crystallize` flow (decisions + actions) | Generic ingest | Generic ingest | Generic ingest | Source-only |
| **Install target** | Claude Code | Claude Code | OpenClaw / Codex | Self-host web | SaaS |
| **Ops burden** | None (local files) | None | Obsidian plugin + Node server | Supabase + S3 + OCR | Zero |
| **Scales to 1000+ pages** | Yes (qmd) | Degrades | Degrades | Yes | Yes |
| **PM-tuned taxonomy** | Yes (competitive, customer, strategy, roadmap, ai) | No | No | No | No |

For a deeper breakdown of which Karpathy and Rohit v2 ideas this implements,
see the [design notes](#design-notes) below.

## Target users

Good fit if you:

- Work as a PM, analyst, researcher, or founder with lots of meetings and reports
- Want a local-first, markdown-based knowledge base that you own
- Use Claude Code as your primary agent
- Are comfortable on a terminal (you'll run `scaffold.py` and `lint.py`)

Not a fit if you:

- Want a zero-terminal SaaS → use NotebookLM
- Need team collaboration out of the box → use Notion or a shared Obsidian vault
- Don't use Claude Code → port the SKILL.md to your agent of choice

## Layout

```
llm-wiki-pm/
├── SKILL.md                  # Main agent instructions
├── README.md                 # This file
├── references/
│   ├── schema-guide.md       # Customizing SCHEMA.md
│   ├── update-guide.md       # Update flow discipline
│   ├── lint-guide.md         # Interpreting tiered reports
│   ├── obsidian-sync.md      # Headless sync for mobile access
│   ├── privacy-guide.md      # Pre-ingest filter + private flag
│   ├── crystallize-guide.md  # Transcript → decision digest pattern
│   ├── qmd-search.md         # Primary search engine (BM25+vector+rerank)
│   ├── output-formats.md     # Marp / matplotlib / CSV / Mermaid
│   └── nextjs-integration.md # Graph + page viewer in a Next.js app
├── scripts/
│   ├── scaffold.py           # Bootstrap new wiki directory
│   ├── lint.py               # Tiered health report + --auto-fix
│   └── backlinks.py          # Show pages linking to a slug
└── templates/
    ├── SCHEMA.md             # PM-tuned domain + tag taxonomy
    ├── index.md              # Empty content catalog
    ├── log.md                # Empty action log
    └── overview.md           # Empty synthesis page
```

## Setup

Two scenarios documented in detail in [GETTING_STARTED.md](GETTING_STARTED.md):

1. **Human user with Claude Code**: ~15 min from zero to first ingest
2. **Application-orchestrated scaffold**: programmatic wiki provisioning
   for platform/multi-tenant deployments

## Quick Start

### 1. Bootstrap a wiki

```bash
python3 /home/sil/llm-wiki-pm/skills/llm-wiki-pm/scripts/scaffold.py ~/pm-wiki "Katalon PM"
export WIKI_PATH=~/pm-wiki
# add to ~/.bashrc or ~/.zshrc for persistence
```

This creates `~/pm-wiki/` with SCHEMA.md, index.md, log.md, overview.md, and
the raw/entities/concepts/comparisons/queries/_archive subdirs.

### 1b. Install qmd (recommended, upfront)

PM wikis grow fast with frequent meetings. Install qmd for hybrid search:

```bash
# Claude Code plugin
claude plugin marketplace add tobi/qmd
claude plugin install qmd@qmd

# CLI for shell + systemd
npm install -g @tobilu/qmd

# Wire wiki as collections
qmd collection add "$WIKI_PATH"      --name wiki
qmd collection add "$WIKI_PATH/raw"  --name raw
qmd context add qmd://wiki "PM knowledge base: entities, concepts, comparisons, queries"
qmd context add qmd://raw  "Immutable source docs: analyst reports, transcripts"
qmd embed
```

See `references/qmd-search.md` for daemon mode, systemd auto-reindex, and
privacy collection patterns.

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
- **[tobi/qmd](https://github.com/tobi/qmd)**: on-device hybrid search engine
  that makes this skill scale past a few hundred pages.

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
- Optional CLI search via [qmd](references/qmd-search.md)
- Multi-format outputs: [Marp, matplotlib, CSV, Mermaid, Canvas](references/output-formats.md)

### v2 cherry-picks (7/16)

Implemented:

- Explicit supersession with `supersedes:` / `superseded_by:` fields + auto-redirect
- Privacy filter (pre-ingest checklist + `private:` frontmatter flag)
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
