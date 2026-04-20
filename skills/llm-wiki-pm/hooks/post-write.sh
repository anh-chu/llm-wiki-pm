#!/usr/bin/env bash
# post-write.sh
# Runs after any file write to the wiki directory. Checks backlinks for the written file.
# Hook type: PostToolUse (Write / Edit tools) in Claude Code

set -euo pipefail

# ── Resolve paths ─────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/../scripts"

WIKI="${WIKI_PATH:-$HOME/llm-wiki-pm/wiki}"

# ① Determine which file was written
# Claude Code passes the file path via $TOOL_INPUT_FILE or as $1
WRITTEN_FILE="${TOOL_INPUT_FILE:-${1:-}}"

if [[ -z "$WRITTEN_FILE" ]]; then
  # No file passed; nothing to check
  exit 0
fi

# Normalize to absolute path
WRITTEN_FILE="$(realpath "$WRITTEN_FILE" 2>/dev/null || echo "$WRITTEN_FILE")"

# ② Skip if file is not inside the wiki directory
WIKI_REAL="$(realpath "$WIKI" 2>/dev/null || echo "$WIKI")"
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

# ④ Run backlinks check via backlinks.py
BACKLINK_ISSUES=0
if [[ -f "$SCRIPTS_DIR/backlinks.py" ]]; then
  BL_OUTPUT=$(python3 "$SCRIPTS_DIR/backlinks.py" "$WIKI" "$SLUG" --json 2>/dev/null || true)
  if [[ -n "$BL_OUTPUT" ]]; then
    BL_COUNT=$(echo "$BL_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
broken = d.get('broken', [])
print(len(broken))
" 2>/dev/null || echo 0)
    if [[ "$BL_COUNT" -gt 0 ]]; then
      BACKLINK_ISSUES="$BL_COUNT"
      BL_LIST=$(echo "$BL_OUTPUT" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for b in d.get('broken', []):
    print('  - ' + str(b))
" 2>/dev/null || true)
      ISSUES+=("Broken backlinks ($BL_COUNT):" "$BL_LIST")
    fi
  fi
fi

# ⑤ Check for broken [[wikilinks]] in the written file itself
WIKILINK_ISSUES=0
if [[ -f "$WRITTEN_FILE" ]]; then
  while IFS= read -r link; do
    # Strip [[ and ]] and handle aliases: [[target|label]] -> target
    TARGET=$(echo "$link" | sed 's/\[\[//;s/\]\]//;s/|.*//')
    TARGET_SLUG=$(echo "$TARGET" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')

    # Search for the target .md file anywhere in the wiki
    FOUND=$(find "$WIKI" -name "${TARGET}.md" -o -name "${TARGET_SLUG}.md" 2>/dev/null | head -1 || true)
    if [[ -z "$FOUND" ]]; then
      WIKILINK_ISSUES=$(( WIKILINK_ISSUES + 1 ))
      ISSUES+=("  - broken wikilink: [[$TARGET]]")
    fi
  done < <(grep -oP '\[\[[^\]]+\]\]' "$WRITTEN_FILE" 2>/dev/null || true)
fi

# ⑥ Append to _status.md
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

# ⑦ Always exit 0 so the hook never blocks a write
exit 0
