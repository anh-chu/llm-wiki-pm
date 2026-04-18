# llm-wiki-pm

Personal PM knowledge base skill for Claude Code. Karpathy LLM Wiki pattern,
tuned for product management work: competitive intel, customer notes, strategy,
roadmap, AI market.

Base: Karpathy-style LLM Wiki pattern.
Cherry-picks from [kfchou/wiki-skills](https://github.com/kfchou/wiki-skills):
- Separate `update` discipline with diffs + source citation + stale-claim sweep
- Tiered lint report (🔴🟡🔵) written back to wiki as dated page
- `overview.md` evolving synthesis as single entry point

Not cherry-picked (yet): lewislulu's Obsidian audit plugin + web viewer
(useful for team review, overkill for solo).

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

1. **Human user with Claude Code** — ~15 min from zero to first ingest
2. **Application-orchestrated scaffold** — programmatic wiki provisioning
   for platform/multi-tenant deployments

## Quick Start

### 1. Bootstrap a wiki

```bash
python3 /home/sil/llm-wiki-pm/scripts/scaffold.py ~/pm-wiki "Katalon PM"
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

Option A — user-level (available in every project):
```bash
mkdir -p ~/.claude/skills
ln -s /home/sil/llm-wiki-pm ~/.claude/skills/llm-wiki-pm
```

Option B — project-level (per-repo):
```bash
mkdir -p .claude/skills
ln -s /home/sil/llm-wiki-pm .claude/skills/llm-wiki-pm
```

Restart Claude Code. Verify with `/skills` — `llm-wiki-pm` should appear.
The skill auto-activates on ingest/query/update/lint phrasing (see SKILL.md
"When This Skill Activates").

### 4. First ingest

In Claude Code:

> "Ingest this Gartner Magic Quadrant report: <paste or path>"

Claude reads SKILL.md, orients on SCHEMA + index + log + overview, surfaces
takeaways, creates/updates pages, logs.

### 5. Run lint periodically

```bash
python3 /home/sil/llm-wiki-pm/scripts/lint.py ~/pm-wiki
# opens queries/lint-YYYY-MM-DD.md
```

### 6. Mobile access (optional)

See `references/obsidian-sync.md` for obsidian-headless + systemd setup.

## Workflow Patterns

**Weekly competitive digest** — ingest 3-5 analyst links in one session.
Batch updates, one log entry, refresh overview.md.

**Pre-meeting prep** — query "what do we know about <customer>?" → Claude
reads `entities/<customer>.md` + recent log → offer to file post-meeting update.

**Monthly 1:1 follow-up** — ingest transcript → extract decisions/themes →
update relevant concept pages → link from person page.

**Quarterly review** — lint, triage, rotate log, refresh overview, prune
tag taxonomy.

## Scope

Wiki = long-term curated facts + sources you review, cite, and share with
colleagues. Not a replacement for session memory or notes apps. If you pair
with a memory tool (Claude's native memory, mem0, Hindsight), keep them
non-overlapping: wiki holds facts + sources, memory holds persona + session
state.

## License

MIT. Adapted from Karpathy's LLM Wiki pattern and kfchou/wiki-skills.
