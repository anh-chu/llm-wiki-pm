#!/usr/bin/env python3
"""Update wiki_path in the appropriate Claude Code settings file.

Usage:
    set-wiki-path.py <path>           # auto-detect scope
    set-wiki-path.py <path> --local   # force .claude/settings.local.json
"""

import json
import sys
from pathlib import Path

PLUGIN_ID = "llm-wiki-pm@anh-chu-plugins"


def load(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def set_wiki_path(settings: dict, new_path: str) -> dict:
    (
        settings.setdefault("pluginConfigs", {})
        .setdefault(PLUGIN_ID, {})
        .setdefault("options", {})
    )["wiki_path"] = new_path
    return settings


def find_target(cwd: Path, force_local: bool) -> Path:
    """Return the settings file to write to."""
    if force_local:
        return cwd / ".claude" / "settings.local.json"

    # Check local first (highest project precedence, gitignored)
    local = cwd / ".claude" / "settings.local.json"
    if local.exists():
        d = load(local)
        if d.get("pluginConfigs", {}).get(PLUGIN_ID):
            return local

    # Check project-level shared settings
    project = cwd / ".claude" / "settings.json"
    if project.exists():
        d = load(project)
        if d.get("enabledPlugins", {}).get(PLUGIN_ID):
            return project
        if d.get("pluginConfigs", {}).get(PLUGIN_ID):
            return project

    # Fall back to global user settings
    return Path.home() / ".claude" / "settings.json"


if len(sys.argv) < 2 or not sys.argv[1].strip():
    print("Usage: set-wiki-path.py <path> [--local]")
    sys.exit(1)

raw = sys.argv[1].strip()
force_local = "--local" in sys.argv

new_path = str(Path(raw).expanduser().resolve())
cwd = Path.cwd()
target = find_target(cwd, force_local)

data = load(target)
set_wiki_path(data, new_path)
write(target, data)

scope = (
    "local"
    if target.name == "settings.local.json"
    else "project"
    if target.parent.parent == cwd
    else "user"
)
print(f"ok: wiki_path = {new_path}")
print(f"    written to {target} ({scope} scope)")
