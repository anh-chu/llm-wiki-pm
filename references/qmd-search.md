# QMD Search

[qmd](https://github.com/tobi/qmd) is the recommended search engine for the
wiki. Install upfront. With dozens of meetings per week and crystallize pages
accumulating, `grep` becomes unreliable past 200 pages and misses semantic
matches entirely.

qmd provides BM25 + vector + LLM reranking, all local, via CLI or MCP.

## Install (Claude Code)

Plugin route (recommended):

```bash
claude plugin marketplace add tobi/qmd
claude plugin install qmd@qmd
```

Or manual MCP config in `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "qmd": {
      "command": "qmd",
      "args": ["mcp"]
    }
  }
}
```

Global CLI for shelling out:

```bash
npm install -g @tobilu/qmd
# or
bun install -g @tobilu/qmd
```

## Wire to the wiki

```bash
# collections — index wiki layer + raw sources separately
qmd collection add "$WIKI_PATH" --name wiki
qmd collection add "$WIKI_PATH/raw" --name raw

# context — helps the reranker pick the right results
qmd context add qmd://wiki "Agent-authored PM knowledge base: entities, concepts, comparisons, queries"
qmd context add qmd://raw  "Immutable source documents: analyst reports, transcripts, internal docs"

# Build indexes
qmd embed
```

Re-index after heavy ingest batches:

```bash
qmd update                # scan filesystem
qmd embed                 # refresh vectors for changed files
```

For continuous sync consider a systemd timer or file-watch hook (see
"Automation" below).

## Use patterns

### In Claude Code (via MCP)

The agent calls `query`, `get`, `multi_get` tools directly. No CLI gymnastics.

Preferred search tool order for the agent:
1. **`query` (qmd hybrid)** — default for any "what do we know about X" question
2. **`get` / `multi_get`** — when you know the path or a pattern
3. **`grep`** — last resort, only for exact token match (e.g. a specific
   dollar figure or codename) that semantic search might miss

### From shell

```bash
# Fast keyword search
qmd search "tricentis pricing" -c wiki

# Semantic / natural language
qmd vsearch "how are competitors positioning around AI"

# Best quality — hybrid + LLM rerank
qmd query "what did we decide about enterprise migration in Q2"

# Scoped to raw sources only
qmd query "customer alpha renewal signals" -c raw

# Agent-friendly output
qmd query "kai pricing direction" --json -n 10
qmd query "trueplatform launch" --all --files --min-score 0.4
```

### Collection strategies

Two collections (`wiki`, `raw`) is the default. Search `wiki` first — it's
already synthesized. Fall through to `raw` only when wiki is thin on the
topic or when you need a direct quote.

For very large wikis, consider splitting further:

```bash
qmd collection add "$WIKI_PATH/entities"    --name entities
qmd collection add "$WIKI_PATH/concepts"    --name concepts
qmd collection add "$WIKI_PATH/queries"     --name queries
qmd collection add "$WIKI_PATH/raw"         --name raw
```

Lets the agent scope `-c queries` when asked "what have we decided about X".

## Privacy: exclude private pages from search surfacing

qmd doesn't filter on frontmatter. Two options:

**Option A — separate private collection:**

```bash
# Move private pages to a separate dir or tag them with a path prefix
qmd collection add "$WIKI_PATH/_private" --name private
```

Then omit `-c private` from default searches. Explicit opt-in for sensitive
queries.

**Option B — post-filter in the agent:**

After qmd returns results, the agent greps for `private: true` in each hit's
frontmatter. Skip when exporting or when the request came from a shared context.

For mixed-sensitivity wikis, Option A is cleaner.

## Update/refresh cadence

- **After every ingest batch**: `qmd update && qmd embed`
- **Daily**: `qmd update` (picks up file changes)
- **Weekly**: `qmd embed --force` to refresh all vectors if models changed

### Background daemon (Claude Code, HTTP MCP)

Keeps models in VRAM across requests — faster than stdio reload per query:

```bash
qmd mcp --http --daemon
qmd status    # confirms "MCP: running"
```

Point Claude Code at `http://localhost:8181/mcp` instead of launching via
`command: qmd`.

### Systemd watcher for auto-reindex

`~/.config/systemd/user/qmd-watch.path`:

```ini
[Unit]
Description=Watch PM wiki for changes

[Path]
PathModified=%h/pm-wiki
PathModified=%h/pm-wiki/raw

[Install]
WantedBy=default.target
```

`~/.config/systemd/user/qmd-watch.service`:

```ini
[Unit]
Description=Reindex PM wiki on change

[Service]
Type=oneshot
ExecStart=/bin/sh -c 'qmd update && qmd embed'
```

```bash
systemctl --user enable --now qmd-watch.path
```

Now any edit on the laptop re-embeds in the background. No manual `qmd embed`.

## Skill integration

The agent should prefer qmd over grep whenever available:

1. Check `qmd status` at session start. If running, use `query` / `get`
   / `multi_get` MCP tools.
2. If qmd is missing or the index is stale (`status` shows unindexed files),
   prompt user to run `qmd update && qmd embed`.
3. Fall back to grep + `index.md` only if qmd unavailable.

At dozens of meetings per week, skipping qmd means the wiki's value decays
fast — the agent won't find things you filed three months ago.

## Troubleshooting

- **"no results"** → check collection is added (`qmd status`), embeddings
  generated (`qmd embed`)
- **slow queries** → use HTTP daemon mode, `qmd mcp --http --daemon`
- **stale results** → `qmd update` after any bulk filesystem change
- **reranker too slow** → fall back to `qmd search` (BM25 only) or
  `qmd vsearch` (vector only) for speed-sensitive flows
