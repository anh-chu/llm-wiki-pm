---
name: set-wiki-path
description: Change the active wiki directory for llm-wiki-pm.
argument-hint: [path]
disable-model-invocation: true
allowed-tools: Bash(python3 *)
---

Update the wiki path to `$ARGUMENTS`.

Run:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/set-wiki-path.py" "$ARGUMENTS"
```

Always writes to `.claude/settings.local.json` in the current directory.
That file is gitignored and takes precedence over global config for this project.

Tell the user the new path and remind them to restart Claude Code.
If the path does not exist yet, note that the SessionStart hook will create it on next start.
