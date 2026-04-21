---
name: set-wiki-path
description: Change the active wiki directory for llm-wiki-pm.
argument-hint: [path] [--local]
disable-model-invocation: true
allowed-tools: Bash(python3 *)
---

Update the wiki path to `$ARGUMENTS`.

Run:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/set-wiki-path.py" $ARGUMENTS
```

The script auto-detects the right settings file:
- `--local` flag: writes to `.claude/settings.local.json` in cwd (project-specific, gitignored, takes precedence over global)
- No flag: checks if plugin is enabled at project scope (`.claude/settings.json`), then falls back to global (`~/.claude/settings.json`)

Tell the user the new path, which file was updated, and the scope (local/project/user).
Remind them to restart Claude Code for the change to take effect.
If the path does not exist yet, note that the SessionStart hook will create it on next start.
