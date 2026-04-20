#!/usr/bin/env bash
# post-write.sh
# Runs after any file write to the wiki directory. Checks wikilinks in the written file.
# Hook type: PostToolUse (Write|Edit tools) in Claude Code
# Input: JSON on stdin with tool_name and tool_input fields

set -euo pipefail

# ── Resolve paths ─────────────────────────────────────────────────────────────
WIKI="${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$HOME/llm-wiki-pm/wiki}}"

# ① Read file path from stdin JSON using Python (no jq dependency)
INPUT=$(cat)
WRITTEN_FILE=$(python3 -c "
import json, sys
try:
    data = json.loads(sys.argv[1])
    print((data.get('tool_input') or {}).get('file_path', ''))
except Exception:
    print('')
" "$INPUT" 2>/dev/null || true)
if [[ -z "$WRITTEN_FILE" ]]; then
  exit 0
fi

# Resolve to absolute path using Python (portable, works on macOS and Linux)
WRITTEN_FILE=$(python3 -c "
import os, sys
p = os.path.realpath(os.path.abspath(sys.argv[1]))
print(p)
" "$WRITTEN_FILE" 2>/dev/null || echo "$WRITTEN_FILE")

# ② Skip if file is not inside the wiki directory
WIKI_REAL=$(python3 -c "
import os, sys
print(os.path.realpath(os.path.abspath(sys.argv[1])))
" "$WIKI" 2>/dev/null || echo "$WIKI")

if [[ "$WRITTEN_FILE" != "$WIKI_REAL"/* ]]; then
  exit 0
fi

# Skip non-markdown files
if [[ "$WRITTEN_FILE" != *.md ]]; then
  exit 0
fi

STATUS_FILE="$WIKI/_status.md"
NOW_FMT=$(date '+%Y-%m-%d %H:%M')
ISSUES=()

# ③ Extract slug from filename
SLUG=$(basename "$WRITTEN_FILE" .md)

# ④ Check for broken [[wikilinks]] in the written file itself
WIKILINK_ISSUES=0
if [[ -f "$WRITTEN_FILE" ]]; then
  # Use Python to extract wikilinks (grep -oP is GNU-only)
  while IFS= read -r link; do
    [[ -z "$link" ]] && continue
    # Strip [[ and ]] and handle aliases: [[target|label]] -> target
    TARGET=$(echo "$link" | python3 -c "
import sys
raw = sys.stdin.read().strip()
# Remove [[ and ]]
raw = raw.lstrip('[[').rstrip(']]')
# Handle alias syntax: target|label -> target, and anchors: target#section -> target
raw = raw.split('|')[0].split('#')[0].strip()
print(raw)
")

    TARGET_SLUG=$(echo "$TARGET" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

    # Search only in wiki page dirs (not raw/) to avoid false positives
    FOUND=$(find \
      "$WIKI/entities" "$WIKI/concepts" "$WIKI/comparisons" "$WIKI/queries" \
      -name "${TARGET}.md" -o -name "${TARGET_SLUG}.md" 2>/dev/null | head -1 || true)
    if [[ -z "$FOUND" ]]; then
      WIKILINK_ISSUES=$(( WIKILINK_ISSUES + 1 ))
      ISSUES+=("  - broken wikilink: [[$TARGET]]")
    fi
  done < <(python3 -c "
import re, sys
text = open(sys.argv[1]).read()
for m in re.findall(r'\[\[[^\]]+\]\]', text):
    print(m)
" "$WRITTEN_FILE" 2>/dev/null || true)
fi

# ⑤ Append to _status.md
# Create _status.md with minimal header if it does not exist yet
if [[ ! -f "$STATUS_FILE" ]]; then
  printf '# Wiki Status\n\n' > "$STATUS_FILE"
fi

{
  if [[ "${#ISSUES[@]}" -gt 0 ]]; then
    echo ""
    echo "## Recent Write Issues"
    echo ""
    echo "**[$NOW_FMT] write | $SLUG**"
    echo ""
    for issue in "${ISSUES[@]}"; do
      echo "$issue"
    done
    echo ""
  else
    echo ""
    echo "## [$NOW_FMT] write | $SLUG | clean"
  fi
} >> "$STATUS_FILE"

# ⑥ Always exit 0 so the hook never blocks a write
exit 0
