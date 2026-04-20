#!/usr/bin/env bash
# session-stop.sh
# Runs at session end. Guards log rotation to keep log.md manageable.
# Hook type: SessionEnd (fires when session terminates, not after every turn)

set -euo pipefail

# ── Resolve WIKI path ──────────────────────────────────────────────────────────
WIKI="${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$HOME/llm-wiki-pm/wiki}}"

# ① Exit silently if wiki not initialized yet
if [[ ! -d "$WIKI" ]]; then
  exit 0
fi

LOG_FILE="$WIKI/log.md"

# ② Exit silently if log.md does not exist
if [[ ! -f "$LOG_FILE" ]]; then
  exit 0
fi

# ③ Count lines in log.md
LINE_COUNT=$(wc -l < "$LOG_FILE")

# ④ Only rotate if log exceeds 500 lines
if [[ "$LINE_COUNT" -le 500 ]]; then
  exit 0
fi

# ── Determine rotation target filename ────────────────────────────────────────
YEAR=$(date +%Y)
BASE_NAME="log-${YEAR}.md"
DEST="$WIKI/$BASE_NAME"

# If log-YYYY.md already exists, find the next available part number
if [[ -f "$DEST" ]]; then
  PART=2
  while [[ -f "$WIKI/log-${YEAR}-part-${PART}.md" ]]; do
    PART=$(( PART + 1 ))
  done
  BASE_NAME="log-${YEAR}-part-${PART}.md"
  DEST="$WIKI/$BASE_NAME"
fi

# ⑤ Rotate: move log.md to the archive name
mv "$LOG_FILE" "$DEST"

# ⑥ Create fresh log.md with a rotation header
TODAY=$(date '+%Y-%m-%d')
printf '# Wiki Log\n\nRotated from %s on %s.\n' "$BASE_NAME" "$TODAY" > "$LOG_FILE"

# ⑦ Report the rotation to stderr
echo "Wiki log rotated: log.md -> $BASE_NAME (was $LINE_COUNT lines)" >&2

exit 0
