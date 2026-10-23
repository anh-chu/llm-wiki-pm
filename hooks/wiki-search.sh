#!/bin/sh
# wiki-search.sh — MCP launcher for obsidian-mcp (BM25 search over the wiki)
# Read-only tool set: wiki writes go through Claude Code's Write/Edit so the
# pre/post-write hooks (snapshot, link check) still fire.
# POSIX sh only — the plugin manifest invokes this as `sh wiki-search.sh`,
# so no bashisms ([[ ]], set -o pipefail) which break under dash/busybox.

set -eu

# Same wiki path as the hooks. MCP servers don't get CLAUDE_PLUGIN_OPTION_*, so
# plugin.json passes the option in as WIKI_CONFIGURED_PATH.
VAULT=$(sh "$(dirname "$0")/resolve-wiki.sh" "${WIKI_CONFIGURED_PATH:-}")
if [ -z "$VAULT" ]; then
  echo "llm-wiki-pm: no wiki path configured. Run /llm-wiki-pm:set-wiki-path ~/your-path, then restart." >&2
  exit 1
fi

BIN=$(sh "$(dirname "$0")/obsidian-mcp-fetch.sh")

# Data folder outside the vault (the search index itself is in memory per process).
export OBSIDIAN_MCP_DATA="${XDG_DATA_HOME:-$HOME/.local/share}/obsidian-mcp"
export OBSIDIAN_TOOLS="search_text,search_regex,note_read,wikilinks"
export OBSIDIAN_EMBEDDINGS=false
# _archive/ holds pre-overwrite snapshots; searching them surfaces stale claims.
# note_read can still open an archived page by path.
export OBSIDIAN_EXCLUDE_PATHS="${OBSIDIAN_EXCLUDE_PATHS:-_archive/**}"
export OBSIDIAN_LOG_LEVEL="${OBSIDIAN_LOG_LEVEL:-error}"

# The filter trims obsidian-mcp's very large search responses (see its docstring).
exec python3 "$(dirname "$0")/wiki-search-filter.py" "$BIN" "$VAULT"
