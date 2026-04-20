#!/usr/bin/env bash
# session-start.sh
# Runs at session start (SessionStart event).
# - Scaffolds the wiki on first run if it does not exist
# - Pre-computes wiki health and writes _status.md
# - Outputs a status summary as additionalContext for Claude
# Hook type: SessionStart (fires once per session, not on every prompt)
# Input: JSON on stdin (session_id, source, model, etc.)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Trust CLAUDE_PLUGIN_ROOT when set (always set during plugin execution).
# Fallback for local dev: script lives at <plugin-root>/skills/llm-wiki-pm/hooks/
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/../../.." && pwd)}"
TEMPLATES_DIR="$PLUGIN_ROOT/skills/llm-wiki-pm/templates"
SCRIPTS_DIR="$PLUGIN_ROOT/skills/llm-wiki-pm/scripts"

# ① Resolve wiki path from plugin config, then env var, then default
WIKI="${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-$HOME/llm-wiki-pm/wiki}}"
DOMAIN="${CLAUDE_PLUGIN_OPTION_wiki_domain:-PM}"

# ② Scaffold wiki on first run — only if dir is new or truly empty
# Never overwrite files in an existing non-empty directory.
SCAFFOLD=false
if [[ ! -e "$WIKI" ]]; then
  SCAFFOLD=true
elif [[ -z "$(find "$WIKI" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
  SCAFFOLD=true
elif [[ ! -f "$WIKI/SCHEMA.md" ]]; then
  echo "Warning: $WIKI exists and is non-empty but has no SCHEMA.md. Skipping scaffold to avoid overwriting files." >&2
fi

if [[ "$SCAFFOLD" == true ]]; then
  mkdir -p "$WIKI"
  for subdir in \
    raw/articles raw/papers raw/transcripts raw/internal raw/assets \
    entities concepts comparisons queries _archive; do
    mkdir -p "$WIKI/$subdir"
  done

  TODAY=$(date '+%Y-%m-%d')

  # Copy and customize SCHEMA.md (Python for safe replacement of any domain string)
  python3 -c "
import sys
text = open(sys.argv[1]).read()
text = text.replace('Product management knowledge base.', sys.argv[2] + ' knowledge base.')
text = text.replace('# Wiki Schema, PM', '# Wiki Schema, ' + sys.argv[2])
open(sys.argv[3], 'w').write(text)
" "$TEMPLATES_DIR/SCHEMA.md" "$DOMAIN" "$WIKI/SCHEMA.md"
  sed "s/YYYY-MM-DD/$TODAY/g" "$TEMPLATES_DIR/index.md" > "$WIKI/index.md"
  sed "s/YYYY-MM-DD/$TODAY/g" "$TEMPLATES_DIR/overview.md" > "$WIKI/overview.md"
  {
    cat "$TEMPLATES_DIR/log.md"
    echo ""
    echo "## [$TODAY] create | Wiki initialized"
    echo "- Domain: $DOMAIN"
    echo "- Structure scaffolded automatically by llm-wiki-pm plugin"
  } > "$WIKI/log.md"
fi

# ③ Gather health metrics
NOW_TS=$(date +%s)
NOW_FMT=$(date '+%Y-%m-%d %H:%M')
THRESHOLD_STALE=$(( NOW_TS - 30 * 86400 ))
THRESHOLD_DECAY=$(( NOW_TS - 60 * 86400 ))

BROKEN_LINKS=0
ORPHANS=0
STALE_PAGES=()
DECAY_PAGES=()

# ④ Run lint if available
if [[ -f "$SCRIPTS_DIR/lint.py" ]]; then
  if LINT_OUT=$(python3 "$SCRIPTS_DIR/lint.py" "$WIKI" --quiet --json 2>/dev/null); then
    BROKEN_LINKS=$(echo "$LINT_OUT" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(len(d.get('broken_links',[])))" 2>/dev/null || echo 0)
    ORPHANS=$(echo "$LINT_OUT" | python3 -c \
      "import sys,json; d=json.load(sys.stdin); print(len(d.get('orphans',[])))" 2>/dev/null || echo 0)
  fi
fi

# ⑤ Scan for stale and decayed pages
scan_dir() {
  local dir="$1"
  [[ -d "$WIKI/$dir" ]] || return 0  # explicit 0: avoid set -e triggering in caller
  while IFS= read -r -d '' file; do
    local slug updated_val updated_ts
    slug=$(basename "$file" .md)
    updated_val=$(grep -m1 '^updated:' "$file" 2>/dev/null \
      | sed 's/updated:[[:space:]]*//' | tr -d '"' | xargs || true)
    [[ -z "$updated_val" ]] && continue
    updated_ts=$(python3 -c "
from datetime import datetime
import sys
try:
    print(int(datetime.fromisoformat(sys.argv[1]).timestamp()))
except Exception:
    print(0)
" "$updated_val" 2>/dev/null || echo 0)
    [[ "$updated_ts" -eq 0 ]] && continue

    if [[ "$updated_ts" -lt "$THRESHOLD_STALE" ]]; then
      STALE_PAGES+=("$dir/$slug ($updated_val)")
    fi
    if grep -q 'competitive' "$file" 2>/dev/null \
        && [[ "$updated_ts" -lt "$THRESHOLD_DECAY" ]]; then
      DECAY_PAGES+=("$dir/$slug ($updated_val)")
    fi
  done < <(find "$WIKI/$dir" -maxdepth 1 -name '*.md' -print0 2>/dev/null)
}

for d in entities concepts comparisons; do
  scan_dir "$d"
done

STALE_COUNT="${#STALE_PAGES[@]}"
DECAY_COUNT="${#DECAY_PAGES[@]}"
TOTAL=$(( BROKEN_LINKS + ORPHANS + STALE_COUNT + DECAY_COUNT ))

# ⑥ Write _status.md
STATUS_FILE="$WIKI/_status.md"
{
  echo "# Wiki Status"
  echo ""
  echo "Last checked: $NOW_FMT"
  echo ""
  echo "## Health Summary"
  echo ""
  echo "| Metric | Count |"
  echo "|--------|-------|"
  echo "| Broken links | $BROKEN_LINKS |"
  echo "| Orphan pages | $ORPHANS |"
  echo "| Stale pages (>30 days) | $STALE_COUNT |"
  echo "| Confidence decay (competitive >60 days) | $DECAY_COUNT |"

  if [[ "$DECAY_COUNT" -gt 0 ]]; then
    echo ""
    echo "## Confidence Decay Candidates"
    echo ""
    for p in "${DECAY_PAGES[@]}"; do echo "- $p"; done
  fi

  if [[ "$STALE_COUNT" -gt 0 ]]; then
    echo ""
    echo "## Stale Pages"
    echo ""
    for p in "${STALE_PAGES[@]}"; do echo "- $p"; done
  fi

  echo ""
  echo "---"
  echo "*Generated by session-start.sh. Do not edit manually.*"
} > "$STATUS_FILE"

# ⑦ Output additionalContext JSON so Claude sees the summary immediately
CONTEXT="Wiki at $WIKI. Health check: $TOTAL issues."
if [[ "$TOTAL" -gt 0 ]]; then
  CONTEXT="$CONTEXT Broken links: $BROKEN_LINKS. Orphans: $ORPHANS."
  CONTEXT="$CONTEXT Stale: $STALE_COUNT. Confidence decay: $DECAY_COUNT."
  CONTEXT="$CONTEXT See _status.md for details."
fi

python3 -c "
import json, sys
print(json.dumps({
  'hookSpecificOutput': {
    'hookEventName': 'SessionStart',
    'additionalContext': sys.argv[1]
  }
}))
" "$CONTEXT"

exit 0
