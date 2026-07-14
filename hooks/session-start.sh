#!/usr/bin/env bash
# session-start.sh
# Runs at session start (SessionStart event).
# - Scaffolds the wiki on first run if it does not exist
# - Pre-computes wiki health and writes _status.md
# - Outputs a status summary as additionalContext for Claude
# Hook type: SessionStart (fires once per session, not on every prompt)
# Input: JSON on stdin (session_id, source, model, etc.)

set -euo pipefail

# Save stdin (JSON input) for later use
STDIN_JSON=$(cat)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Trust CLAUDE_PLUGIN_ROOT when set (always set during plugin execution).
# Fallback for local dev: script lives at <plugin-root>/hooks/
PLUGIN_ROOT="${CLAUDE_PLUGIN_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
TEMPLATES_DIR="$PLUGIN_ROOT/skills/llm-wiki-pm/templates"
SCRIPTS_DIR="$PLUGIN_ROOT/skills/llm-wiki-pm/scripts"

# ① Resolve wiki path
# Priority: .wiki-path file (project) > CLAUDE_PLUGIN_OPTION_wiki_path (global) > WIKI_PATH env > cwd fallback
WIKI_PATH_FILE="$(pwd)/.wiki-path"
FILE_WIKI=$(cat "$WIKI_PATH_FILE" 2>/dev/null | tr -d '[:space:]' || true)

WIKI="${FILE_WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-}}}"
DOMAIN="${CLAUDE_PLUGIN_OPTION_wiki_domain:-PM}"
GLOBAL_WARNING=""
if [[ -z "$WIKI" ]]; then
  WIKI="$(pwd)"
  GLOBAL_WARNING="llm-wiki-pm: no wiki path configured. Falling back to current directory ($WIKI). Run /llm-wiki-pm:set-wiki-path ~/your-path to set a permanent path."
elif [[ -z "$FILE_WIKI" ]]; then
  GLOBAL_WARNING="llm-wiki-pm: using global wiki path ($WIKI). Run /llm-wiki-pm:set-wiki-path ~/your-path from your project directory to set a project-specific path."
fi

# ①b Ensure wiki-search package is in npx cache (background, non-blocking)
# First session after install will use npx (slow); this ensures the cache
# exists for wiki-search.sh's fast path on subsequent runs.
if ! find "${HOME}/.npm/_npx" -path "*/@wirux/mcp-markdown-vault/dist/index.js" -print -quit 2>/dev/null | grep -q .; then
  npx -y @wirux/mcp-markdown-vault --version &>/dev/null &
fi

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

# ②b Concurrent session lock
LOCKFILE="$WIKI/.wiki-lock"
LOCK_WARNING=""
if [[ -f "$LOCKFILE" ]]; then
  LOCK_OWNER=$(cat "$LOCKFILE" 2>/dev/null || true)
  LOCK_AGE=0
  if [[ -n "$LOCK_OWNER" ]]; then
    LOCK_TS=$(echo "$LOCK_OWNER" | cut -d: -f2- || true)
    if [[ -n "$LOCK_TS" ]]; then
      LOCK_EPOCH=$(python3 -c "
from datetime import datetime
import sys
try:
    print(int(datetime.fromisoformat(sys.argv[1].replace('Z','+00:00')).timestamp()))
except Exception:
    print(0)
" "$LOCK_TS" 2>/dev/null || echo 0)
      if [[ "$LOCK_EPOCH" -gt 0 ]]; then
        LOCK_AGE=$(( $(date +%s) - LOCK_EPOCH ))
      fi
    fi
  fi
  # Stale lock threshold: 2 hours (session probably crashed)
  if [[ "$LOCK_AGE" -gt 7200 ]]; then
    rm -f "$LOCKFILE"
  else
    LOCK_WARNING="Another wiki session may be active (lock: $LOCK_OWNER). Concurrent writes risk data loss. Proceed with caution or wait for the other session to end."
  fi
fi
# Write our lock
SESSION_ID=$(echo "$STDIN_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('session_id','unknown'))" 2>/dev/null || echo "$$")
echo "${SESSION_ID}:$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$LOCKFILE" 2>/dev/null || true

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

    # Confidence decay: honor frontmatter, not a body-text word match.
    # A page decays if it is competitive-tagged (default 60d) OR sets an explicit
    # confidence_decay_days. Non-competitive pages without the field never decay.
    local fm decay_days is_comp decay_thresh
    fm=$(awk 'NR==1 && /^---[[:space:]]*$/ {f=1; next} f && /^---[[:space:]]*$/ {exit} f {print}' "$file" 2>/dev/null || true)
    decay_days=$(printf '%s\n' "$fm" | grep -m1 '^confidence_decay_days:' | sed 's/[^0-9]//g' || true)
    is_comp=$(printf '%s\n' "$fm" | grep -m1 '^tags:' | grep -c 'competitive' || true)
    is_comp=${is_comp:-0}
    if [[ -n "$decay_days" ]]; then
      decay_thresh=$(( NOW_TS - decay_days * 86400 ))
      [[ "$updated_ts" -lt "$decay_thresh" ]] && DECAY_PAGES+=("$dir/$slug ($updated_val)")
    elif [[ "$is_comp" -gt 0 && "$updated_ts" -lt "$THRESHOLD_DECAY" ]]; then
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
  echo "> ⚠️ Session-start snapshot only — frozen at the timestamp above. Counts go"
  echo "> stale as soon as you create or edit pages this session. For live numbers,"
  echo "> re-run \`lint.py\`; do not quote these figures after a bulk ingest."
  echo ""
  echo "## Health Summary"
  echo ""
  echo "| Metric | Count |"
  echo "|--------|-------|"
  echo "| Broken links | $BROKEN_LINKS |"
  echo "| Orphan pages | $ORPHANS |"
  echo "| Stale pages (>30 days) | $STALE_COUNT |"
  echo "| Confidence decay (past decay window) | $DECAY_COUNT |"

  if [[ "$DECAY_COUNT" -gt 0 ]]; then
    echo ""
    echo "## Confidence Decay Candidates"
    echo ""
    i=0
    for p in "${DECAY_PAGES[@]}"; do
      [[ "$i" -ge 20 ]] && { echo "- (+$(( DECAY_COUNT - 20 )) more)"; break; }
      echo "- $p"; i=$(( i + 1 ))
    done
  fi

  if [[ "$STALE_COUNT" -gt 0 ]]; then
    echo ""
    echo "## Stale Pages"
    echo ""
    i=0
    for p in "${STALE_PAGES[@]}"; do
      [[ "$i" -ge 20 ]] && { echo "- (+$(( STALE_COUNT - 20 )) more)"; break; }
      echo "- $p"; i=$(( i + 1 ))
    done
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
if [[ -n "$LOCK_WARNING" ]]; then
  CONTEXT="$CONTEXT LOCK WARNING: $LOCK_WARNING"
fi

# Slim always-on "watcher" primer. Keeps the ambient proactive behaviors alive
# (set-and-forget) without force-loading the full ~8k-token SKILL.md every
# session. The skill loads only when a trigger below actually fires.
PRIMER="llm-wiki-pm (a PM second-brain wiki) is available at the path above but is NOT loaded yet. Invoke the llm-wiki-pm skill (Skill tool) as soon as the conversation touches PM knowledge work, so its full instructions and proactive behaviors load. Triggers — invoke on ANY of:
- the user asks to ingest/query/update/lint the wiki, catch up, brief, run a digest, coverage audit, or pre-meeting prep, or references 'my wiki / knowledge base / notes';
- the user drops a wikifiable PM fact in passing: a named company/person/product, a decision ('we decided', 'going with X'), a competitor move, a customer or roadmap fact, or an open question the wiki should hold;
- natural-memory phrases: 'remember that', 'note that', \"don't forget\", 'log this', 'what do we know about X', 'what am I missing'.
Do NOT load it for unrelated coding or chit-chat. When unsure and a PM entity or decision was mentioned, load it — ambient capture is the whole point of a set-and-forget second brain."

python3 -c "
import json, sys
out = {
  'hookSpecificOutput': {
    'hookEventName': 'SessionStart',
    'additionalContext': sys.argv[1] + '\n\n' + sys.argv[3]
  }
}
if sys.argv[2]:
    out['systemMessage'] = sys.argv[2]
print(json.dumps(out))
" "$CONTEXT" "$GLOBAL_WARNING" "$PRIMER"

exit 0
