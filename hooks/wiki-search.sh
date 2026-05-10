#!/usr/bin/env bash
# wiki-search.sh — Fast MCP launcher for @wirux/mcp-markdown-vault
# Avoids npx's ~9s package resolution overhead by finding the cached binary.
# Falls back to npx on first run (slower, but self-installing).

set -euo pipefail

export VAULT_PATH="${CLAUDE_PLUGIN_OPTION_wiki_path:-$(pwd)}"

# Try cached binary first (npx caches here after first run)
CACHED=$(find "${HOME}/.npm/_npx" -path "*/@wirux/mcp-markdown-vault/dist/index.js" -print -quit 2>/dev/null || true)

if [[ -n "$CACHED" && -f "$CACHED" ]]; then
  exec node "$CACHED"
else
  exec npx -y @wirux/mcp-markdown-vault
fi
