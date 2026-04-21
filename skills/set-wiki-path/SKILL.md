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

Writes the resolved path to `.wiki-path` in the current directory.
That file is read by the SessionStart hook to set the wiki location for this project.
Add `.wiki-path` to `.gitignore` if the path is personal; commit it if the whole team shares the same wiki location.

Tell the user the new path and remind them to restart Claude Code.
If the path does not exist yet, the SessionStart hook will create it on next start.
