#!/usr/bin/env bash
# pre-write.sh
# Runs BEFORE a Write/Edit to the wiki. If the target is a knowledge page that
# looks ungrounded (no primary source, no inline provenance), inject a just-in-time
# freshness reminder so the agent sweeps live tools before laundering secondhand
# mentions into the wiki. Non-blocking: emits additionalContext, never denies.
# Hook type: PreToolUse (Write|Edit) in Claude Code.
# Input: JSON on stdin with tool_name and tool_input fields.

set -euo pipefail

# ── Resolve wiki path (must match session-start.sh) ──────────────────────────
FILE_WIKI=$(cat "$(pwd)/.wiki-path" 2>/dev/null | tr -d '[:space:]' || true)
WIKI="${FILE_WIKI:-${CLAUDE_PLUGIN_OPTION_wiki_path:-${WIKI_PATH:-}}}"
[[ -z "$WIKI" ]] && exit 0

INPUT=$(cat)

python3 - "$INPUT" "$WIKI" <<'PY' || true
import datetime, json, os, re, shutil, sys

raw, wiki = sys.argv[1], sys.argv[2]
try:
    data = json.loads(raw)
except Exception:
    sys.exit(0)

ti = data.get("tool_input") or {}
fp = ti.get("file_path", "")
if not fp or not fp.endswith(".md"):
    sys.exit(0)

abs_fp = os.path.realpath(os.path.abspath(fp))
wiki_real = os.path.realpath(os.path.abspath(wiki))
if not abs_fp.startswith(wiki_real + os.sep):
    sys.exit(0)

rel = abs_fp[len(wiki_real) + 1:]
stem = os.path.splitext(os.path.basename(abs_fp))[0]

# Exempt: immutable sources, archives, and structural/generated pages.
EXEMPT_DIRS = ("raw/", "_archive/", "_drafts/", "drafts/")
EXEMPT_STEMS = {"index", "log", "_status", "SCHEMA", "MY-INTEGRATIONS", "overview"}
if rel.startswith(EXEMPT_DIRS) or stem in EXEMPT_STEMS or stem.startswith("lint-"):
    sys.exit(0)
# Only gate the agent-owned knowledge dirs.
if not rel.startswith(("entities/", "concepts/", "comparisons/", "queries/")):
    sys.exit(0)

# Pre-update snapshot (deterministic — replaces the prose "mandatory snapshot" rule).
# If this is an overwrite/edit of an existing page, copy the current version to
# _archive/<slug>-<YYYY-MM-DD>.md before it changes. Idempotent: at most one
# snapshot per page per day, so it never spams and never blocks. Best-effort.
if os.path.exists(abs_fp):
    try:
        day = datetime.date.today().isoformat()
        arc_dir = os.path.join(wiki_real, "_archive")
        os.makedirs(arc_dir, exist_ok=True)
        snap = os.path.join(arc_dir, f"{stem}-{day}.md")
        if not os.path.exists(snap):
            shutil.copy2(abs_fp, snap)
    except Exception:
        pass

# Content to assess: Write carries full content; Edit does not, so read disk.
content = ti.get("content")
if content is None:
    try:
        content = open(abs_fp).read()
    except Exception:
        content = ti.get("new_string", "") or ""

# Extract sources from frontmatter (inline [..] or block - list).
fm_m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
srcs = []
if fm_m:
    lines = fm_m.group(1).splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^sources:", line):
            rest = line.partition(":")[2].strip()
            if rest.startswith("["):
                srcs += [s.strip().strip("'\"") for s in rest.strip("[]").split(",")]
            for nxt in lines[i + 1:]:
                if re.match(r"^\s*-\s+", nxt):
                    srcs.append(re.sub(r"^\s*-\s+", "", nxt).strip().strip("'\""))
                elif re.match(r"^\S", nxt):
                    break
            break
srcs = [s for s in srcs if s]

WIKI_PREFIXES = ("entities/", "concepts/", "comparisons/", "queries/")
primary = [s for s in srcs if not s.startswith(WIKI_PREFIXES)]
has_inline = bool(re.search(r"\[source:", content, re.IGNORECASE))

# Grounded enough → stay silent.
if primary or has_inline:
    sys.exit(0)

msg = (
    f"⚠️ Freshness gate — '{rel}' is being written with no primary source "
    f"(sources are empty or point only to other wiki pages) and no inline "
    f"[source:] markers. Per the Freshness-first protocol: before writing a "
    f"knowledge page, sweep connected tools (Slack, Gmail, Granola, CRM, web) "
    f"for fresh primary information, capture it to raw/, and anchor claims with "
    f"[source: ...]. Don't build a page from the prose of other wiki pages alone "
    f"— that launders secondhand mentions into false confidence. If no tools are "
    f"connected, mark coverage: stub and list unknowns in gaps:."
)
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "additionalContext": msg,
    }
}))
PY
