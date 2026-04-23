#!/usr/bin/env bash
# update-safe.sh — safe upgrade helper for llm-wiki-pm
# Detects user customizations before overwriting files during skill updates.
#
# Usage:
#   ./scripts/update-safe.sh --check                    # report customized files, no changes
#   ./scripts/update-safe.sh --dry-run <upstream-dir>   # show what would be updated
#   ./scripts/update-safe.sh --force <upstream-dir>     # overwrite all (backup first, no prompts)
#   ./scripts/update-safe.sh <upstream-dir>             # interactive per-file prompts
#
# <upstream-dir>: path to a cloned newer version of the skill repo

set -euo pipefail

SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"

MODE="interactive"
UPSTREAM_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --check)   MODE="check"; shift ;;
    --dry-run) MODE="dryrun"; shift ;;
    --force)   MODE="force"; shift ;;
    *)         UPSTREAM_DIR="$1"; shift ;;
  esac
done

# Files that are safe to overwrite (no user content expected)
OVERWRITE_SAFE=(
  "skills/llm-wiki-pm/SKILL.md"
  "skills/set-wiki-path/SKILL.md"
  "scripts/lint.py"
  "scripts/backlinks.py"
  "scripts/update-safe.sh"
  ".claude/agents/worker-wiki-indexer.md"
  ".claude/agents/worker-source-fetcher.md"
  ".claude/agents/worker-link-validator.md"
  ".claude/agents/worker-lint.md"
  "AGENTS.md"
  "CLAUDE.md"
)

# Files that may contain user customizations — handle carefully
USER_CUSTOMIZABLE=(
  "skills/llm-wiki-pm/templates/SCHEMA.md"
  "skills/llm-wiki-pm/templates/index.md"
  "skills/llm-wiki-pm/templates/overview.md"
  "skills/llm-wiki-pm/templates/log.md"
  "skills/llm-wiki-pm/templates/persona.md"
  ".claude/roles/product-manager.md"
  ".claude/roles/researcher.md"
  ".claude/roles/executive.md"
  ".claude/roles/founder.md"
  ".claude-plugin/plugin.json"
)

# Directories that are NEVER touched (user wiki content)
PROTECTED_DIRS=()
if [ -f "$SKILL_DIR/.wiki-path" ]; then
  WIKI_PATH=$(cat "$SKILL_DIR/.wiki-path" | tr -d '[:space:]')
  PROTECTED_DIRS+=("$WIKI_PATH")
fi

echo "=== llm-wiki-pm update-safe ==="
echo "Mode: $MODE"
echo ""

CUSTOMIZED=()
CLEAN=()

for file in "${USER_CUSTOMIZABLE[@]}"; do
  full_path="$SKILL_DIR/$file"
  if [ ! -f "$full_path" ]; then
    CLEAN+=("$file (not present)")
    continue
  fi

  # Detect customization: check git status if in a repo
  if git -C "$SKILL_DIR" diff --quiet HEAD -- "$file" 2>/dev/null; then
    CLEAN+=("$file")
  else
    CUSTOMIZED+=("$file")
  fi
done

echo "--- Customized files (require attention) ---"
if [ ${#CUSTOMIZED[@]} -eq 0 ]; then
  echo "  None. All user-customizable files match upstream."
else
  for f in "${CUSTOMIZED[@]}"; do
    echo "  * $f"
  done
fi
echo ""

if [ "$MODE" == "check" ]; then
  echo "Check complete. Run without --check to proceed with update."
  exit 0
fi

if [ -z "$UPSTREAM_DIR" ]; then
  echo "No upstream directory provided. Detection only — no files will be copied."
  echo "To update files: ./scripts/update-safe.sh [--force] <path-to-newer-repo>"
  [ "$MODE" != "check" ] && exit 0
fi

echo "--- Safe-to-overwrite files ---"
for file in "${OVERWRITE_SAFE[@]}"; do
  if [ -n "$UPSTREAM_DIR" ] && [ -f "$UPSTREAM_DIR/$file" ]; then
    echo "  $file → will overwrite"
  else
    echo "  $file (upstream not found, skip)"
  fi
done
echo ""

if [ "$MODE" == "dryrun" ]; then
  echo "Dry run complete. No files modified."
  exit 0
fi

# Apply safe-to-overwrite files first
if [ -n "$UPSTREAM_DIR" ]; then
  for file in "${OVERWRITE_SAFE[@]}"; do
    src="$UPSTREAM_DIR/$file"
    dst="$SKILL_DIR/$file"
    [ -f "$src" ] || continue
    cp "$src" "$dst"
    echo "UPDATED: $file"
  done
fi

# Handle user-customizable files interactively or with force
for file in "${CUSTOMIZED[@]}"; do
  full_path="$SKILL_DIR/$file"
  upstream_path="${UPSTREAM_DIR:+$UPSTREAM_DIR/$file}"
  backup_path="${full_path}.backup-$(date +%Y%m%d)"

  if [ "$MODE" == "force" ]; then
    cp "$full_path" "$backup_path"
    echo "BACKUP: $file → $(basename "$backup_path")"
    if [ -n "$upstream_path" ] && [ -f "$upstream_path" ]; then
      cp "$upstream_path" "$full_path"
      echo "UPDATED: $file"
    fi
  else
    echo "Customized: $file"
    echo "  Options: [k]eep (default) | [o]verwrite | [b]ackup and overwrite"
    read -r -p "  Choice [k/o/b]: " choice
    case "${choice:-k}" in
      o)
        if [ -n "$upstream_path" ] && [ -f "$upstream_path" ]; then
          cp "$upstream_path" "$full_path"; echo "  → overwritten"
        else
          echo "  → no upstream source found, kept"
        fi ;;
      b)
        cp "$full_path" "$backup_path"
        echo "  → backed up to $(basename "$backup_path")"
        if [ -n "$upstream_path" ] && [ -f "$upstream_path" ]; then
          cp "$upstream_path" "$full_path"; echo "  → overwritten"
        fi ;;
      *) echo "  → kept (no changes)" ;;
    esac
  fi
done

echo ""
echo "Update complete. Wiki content directories were not touched."
if [ ${#PROTECTED_DIRS[@]} -gt 0 ]; then
  echo "Protected: ${PROTECTED_DIRS[*]}"
fi
