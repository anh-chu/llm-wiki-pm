# Wiki Hooks

Three shell scripts that keep the wiki healthy across sessions. When installed as a Claude Code plugin, they activate automatically via `hooks/hooks.json` at the plugin root. No manual configuration needed.

---

## What these hooks do

**session-start.sh**
Runs at session start. Scaffolds the wiki on first run if it does not exist
(reads `CLAUDE_PLUGIN_OPTION_wiki_path` set at plugin enable time). Then scans
for broken links, orphan pages, stale entries (>30 days), and competitive pages
past their confidence decay threshold (>60 days). Writes `_status.md` and
outputs an `additionalContext` summary directly into Claude's context.

**post-write.sh**
Runs after every file write inside the wiki directory. It reads the file path from stdin JSON (`tool_input.file_path`), then scans the written file for broken `[[wikilinks]]` against the wiki page directories. Results are appended to `_status.md`. The hook always exits 0 so it never blocks a write.

**session-stop.sh**
Guards log rotation at the end of each session. When `log.md` exceeds 500 entries (lines starting with `## [`) it renames the file to `log-YYYY.md` (or `log-YYYY-part-N.md` if that already exists) and creates a fresh `log.md` with a rotation header.

---

## Installation

### Claude Code plugin (automatic)

Hooks are defined in `hooks/hooks.json` at the plugin root and activate automatically when the plugin is enabled. No manual `settings.json` editing required.

Make the scripts executable after cloning:

```bash
chmod +x skills/llm-wiki-pm/hooks/*.sh
```

Script paths in `hooks/hooks.json` use `${CLAUDE_PLUGIN_ROOT}` so they resolve correctly regardless of where the plugin is installed.

**Notes on events:**
- `SessionStart` fires once when the session opens (new, resumed, or cleared). Not on every message.
- `PostToolUse` with `matcher: "Write|Edit|MultiEdit"` fires after file writes. The hook reads the file path from stdin JSON (`tool_input.file_path`).
- `SessionEnd` fires when the session terminates. Not after every Claude response (`Stop` does that).

**Notes on `PostToolUse` matcher:**
The `"matcher"` field is matched against the tool name. `Write|Edit|MultiEdit` covers all file-writing tools. `MultiEdit` is confirmed in the official Anthropic `security-guidance` plugin example.

---

### Standalone use (without plugin)

If using the scripts without the Claude Code plugin system, wire them manually.

**Shell alias approach:**

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Run wiki health check before starting any AI session
alias wiki-start='bash /path/to/skills/llm-wiki-pm/hooks/session-start.sh'
alias wiki-stop='bash /path/to/skills/llm-wiki-pm/hooks/session-stop.sh'
```

Call `wiki-start` before opening your AI tool, `wiki-stop` when you close it.

**Wrapper script approach:**

```bash
#!/usr/bin/env bash
# ai-session.sh -- wrapper that runs hooks around your AI tool

bash /path/to/hooks/session-start.sh
your-ai-tool "$@"
bash /path/to/hooks/session-stop.sh
```

For `post-write.sh`, pass the hook JSON payload on stdin (same format Claude Code uses):

```bash
echo '{"tool_name":"Write","tool_input":{"file_path":"/path/to/wiki/entities/example.md"}}' \
  | WIKI_PATH=/path/to/wiki bash /path/to/hooks/post-write.sh
```

---

## How the agent uses hook output

`session-start.sh` writes `$WIKI/_status.md` before the agent gets your first message. The skill instructs the agent to read `_status.md` during the orient step (before planning any work). This means:

- Broken links are surfaced automatically, not discovered mid-task.
- Confidence decay warnings appear at session start, prompting a review.
- Stale pages are listed so the agent can factor them into recommendations.

`post-write.sh` appends to `_status.md` after each write. If the agent writes multiple files in one session, issues accumulate there. The agent can re-read `_status.md` at the end of a session to summarize what changed.

---

## Skipping auto-commit

Auto-commit is not included in these hooks. Automatic commits can obscure work-in-progress and create noisy git history.

If you want auto-commit on session end, add this to `session-stop.sh` before the final `exit 0`:

```bash
# Optional auto-commit -- add manually if desired
cd "$WIKI" && git add -A && git commit -m "wiki update $(date +%Y-%m-%d)" 2>/dev/null || true
```

The `|| true` prevents the hook from failing if there is nothing to commit or git is not initialized.

---

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `WIKI_PATH` | `$HOME/llm-wiki-pm/wiki` | Override the wiki directory location |
| stdin JSON | (from hook system) | `post-write.sh` reads `.tool_input.file_path` from the JSON Claude Code sends on stdin |
