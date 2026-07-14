#!/bin/sh
# wiki-search.sh — Fast MCP launcher for @wirux/mcp-markdown-vault
# Avoids npx's ~9s package resolution overhead by finding the cached binary.
# Falls back to npx on first run (slower, but self-installing).
# POSIX sh only — the plugin manifest invokes this as `sh wiki-search.sh`,
# so no bashisms ([[ ]], set -o pipefail) which break under dash/busybox.

set -eu

# Resolve vault path with the same precedence as the other hooks:
# .wiki-path (project) > CLAUDE_PLUGIN_OPTION_wiki_path (global) > WIKI_PATH > cwd
FILE_WIKI=$(tr -d '[:space:]' < "$(pwd)/.wiki-path" 2>/dev/null || true)
export VAULT_PATH="${FILE_WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$(pwd)}}}"

# Try cached binary first (npx caches here after first run)
CACHED=$(find "${HOME}/.npm/_npx" -path "*/@wirux/mcp-markdown-vault/dist/index.js" -print -quit 2>/dev/null || true)

if [ -n "$CACHED" ] && [ -f "$CACHED" ]; then
  exec node "$CACHED"
else
  exec npx -y @wirux/mcp-markdown-vault
fi
