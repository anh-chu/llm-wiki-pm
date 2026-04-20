---
description: Change the active wiki directory path. Updates pluginConfigs in ~/.claude/settings.json and confirms the new path.
argument-hint: [path]
disable-model-invocation: true
allowed-tools: Bash
---

Change the wiki path to `$ARGUMENTS`.

Run exactly this and nothing else:

```bash
python3 - "$ARGUMENTS" << 'PY'
import json, sys
from pathlib import Path

raw = sys.argv[1].strip()
if not raw:
    print("Usage: /llm-wiki-pm:llm-wiki-path ~/your/path")
    sys.exit(1)

new_path = str(Path(raw).expanduser().resolve())
settings_path = Path.home() / ".claude" / "settings.json"

with open(settings_path) as f:
    settings = json.load(f)

(settings
    .setdefault("pluginConfigs", {})
    .setdefault("llm-wiki-pm@anh-chu-plugins", {})
    .setdefault("options", {})
)["wiki_path"] = new_path

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2)

print(f"ok: wiki_path = {new_path}")
PY
```

Then tell the user: "Wiki path set to [new path]. Restart Claude Code for the change to take effect."
If the path does not exist yet, note that the SessionStart hook will create it on next session start.
