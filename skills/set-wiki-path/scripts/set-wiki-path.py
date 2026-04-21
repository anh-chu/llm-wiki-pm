#!/usr/bin/env python3
"""Write wiki_path to .claude/settings.local.json in the current directory."""

import contextlib
import json
import sys
from pathlib import Path

PLUGIN_ID = "llm-wiki-pm@anh-chu-plugins"

if len(sys.argv) < 2 or not sys.argv[1].strip():
    print("Usage: set-wiki-path.py <path>")
    sys.exit(1)

new_path = str(Path(sys.argv[1].strip()).expanduser().resolve())
target = Path.cwd() / ".claude" / "settings.local.json"

target.parent.mkdir(parents=True, exist_ok=True)

data = {}
if target.exists():
    with contextlib.suppress(json.JSONDecodeError):
        data = json.loads(target.read_text())

(
    data.setdefault("pluginConfigs", {})
    .setdefault(PLUGIN_ID, {})
    .setdefault("options", {})
)["wiki_path"] = new_path

target.write_text(json.dumps(data, indent=2))

print(f"ok: wiki_path = {new_path}")
print(f"    written to {target}")
