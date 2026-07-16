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

# Resolve a usable `node`. A spawned MCP stdio process may inherit a bare PATH
# (or a stale fnm per-shell multishell dir), so `node` is often NOT on PATH —
# this is the usual cause of "wiki-search failed to connect". Try PATH first,
# then fnm's stable default alias, then other common install locations.
NODE_BIN=$(command -v node 2>/dev/null || true)
if [ -z "$NODE_BIN" ]; then
  for cand in \
    "${FNM_DIR:-$HOME/.local/share/fnm}/aliases/default/bin/node" \
    "$HOME/.local/share/fnm/aliases/default/bin/node" \
    "$HOME/.volta/bin/node" \
    "$HOME/.nvm/current/bin/node" \
    /usr/local/bin/node \
    /usr/bin/node
  do
    if [ -x "$cand" ]; then NODE_BIN="$cand"; break; fi
  done
fi
[ -n "$NODE_BIN" ] || { echo "wiki-search: node not found on PATH or common locations" >&2; exit 127; }

# Put the resolved node's dir on PATH so any child (e.g. npx) can find node too.
PATH="$(dirname "$NODE_BIN"):$PATH"; export PATH

# Try cached binary first (npx caches here after first run)
CACHED=$(find "${HOME}/.npm/_npx" -path "*/@wirux/mcp-markdown-vault/dist/index.js" -print -quit 2>/dev/null || true)

if [ -n "$CACHED" ] && [ -f "$CACHED" ]; then
  exec "$NODE_BIN" "$CACHED"
else
  exec "$(dirname "$NODE_BIN")/npx" -y @wirux/mcp-markdown-vault
fi
