#!/bin/sh
# wiki-search.sh — MCP launcher for obsidian-mcp (BM25 search over the wiki)
# Read-only tool set: wiki writes go through Claude Code's Write/Edit so the
# pre/post-write hooks (snapshot, link check) still fire.
# POSIX sh only — the plugin manifest invokes this as `sh wiki-search.sh`,
# so no bashisms ([[ ]], set -o pipefail) which break under dash/busybox.

set -eu

# Resolve vault path with the same precedence as the other hooks:
# .wiki-path (project) > CLAUDE_PLUGIN_OPTION_wiki_path (global) > WIKI_PATH > cwd
FILE_WIKI=$(tr -d '[:space:]' < "$(pwd)/.wiki-path" 2>/dev/null || true)
VAULT="${FILE_WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}"

BIN=$(sh "$(dirname "$0")/obsidian-mcp-fetch.sh")

# Data folder outside the vault (the search index itself is in memory per process).
export OBSIDIAN_MCP_DATA="${XDG_DATA_HOME:-$HOME/.local/share}/obsidian-mcp"
export OBSIDIAN_TOOLS="vault_info,vault_list,note_read,note_read_many,note_inspect,search_text,search_regex,search_metadata,wikilinks"
export OBSIDIAN_EMBEDDINGS=false
# _archive/ holds pre-overwrite snapshots; searching them surfaces stale claims.
# note_read can still open an archived page by path.
export OBSIDIAN_EXCLUDE_PATHS="${OBSIDIAN_EXCLUDE_PATHS:-_archive/**}"
export OBSIDIAN_LOG_LEVEL="${OBSIDIAN_LOG_LEVEL:-error}"

# The filter trims obsidian-mcp's very large search responses (see its docstring).
exec python3 "$(dirname "$0")/wiki-search-filter.py" "$BIN" "$VAULT"
