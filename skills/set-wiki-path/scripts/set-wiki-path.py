#!/usr/bin/env python3
"""Update wiki_path in ~/.claude/settings.json pluginConfigs."""

import json
import sys
from pathlib import Path

if len(sys.argv) < 2 or not sys.argv[1].strip():
    print("Usage: set-wiki-path.py <path>")
    sys.exit(1)

new_path = str(Path(sys.argv[1].strip()).expanduser().resolve())
settings_path = Path.home() / ".claude" / "settings.json"

with open(settings_path) as f:
    settings = json.load(f)

(
    settings.setdefault("pluginConfigs", {})
    .setdefault("llm-wiki-pm@anh-chu-plugins", {})
    .setdefault("options", {})
)["wiki_path"] = new_path

with open(settings_path, "w") as f:
    json.dump(settings, f, indent=2)

print(f"ok: wiki_path = {new_path}")
