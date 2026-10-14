#!/bin/sh
# resolve-wiki.sh — Print the wiki path, or nothing when no wiki is configured.
# Order: .wiki-path in the current directory > the plugin's wiki_path option >
# WIKI_PATH > the current directory only if it already is a wiki (has SCHEMA.md).
# Never falls back to an arbitrary directory, so a project that isn't a wiki
# gets no _status.md, lock file, scaffold or search index.
# Arg 1: the configured path when the caller has it (the MCP launcher gets it
# via ${user_config.wiki_path}); hooks get it as CLAUDE_PLUGIN_OPTION_WIKI_PATH
# (the lowercase name is read too, for older Claude Code).
# POSIX sh only.

conf="${1:-${CLAUDE_PLUGIN_OPTION_WIKI_PATH:-${CLAUDE_PLUGIN_OPTION_wiki_path:-}}}"
case "$conf" in '${'*) conf= ;; esac  # option unset: substitution left the literal
file=$(tr -d '[:space:]' 2>/dev/null < .wiki-path || true)
wiki="${file:-${conf:-${WIKI_PATH:-}}}"
if [ -z "$wiki" ] && [ -f SCHEMA.md ]; then
  wiki=$(pwd)
fi
[ -n "$wiki" ] && printf '%s\n' "$wiki"
exit 0
