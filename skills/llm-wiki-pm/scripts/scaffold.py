#!/usr/bin/env python3
"""Bootstrap a new PM wiki. Usage: scaffold.py <wiki_path> <domain>"""

import json
import sys
from pathlib import Path
from datetime import date

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
TEMPLATES = REPO_DIR / "templates"

SUBDIRS = [
    "raw/articles",
    "raw/papers",
    "raw/transcripts",
    "raw/internal",
    "raw/assets",
    "entities",
    "concepts",
    "comparisons",
    "queries",
    "_archive",
]


HOOK_CONFIG = {
    "UserPromptSubmit": [
        {"hooks": [{"type": "command", "command": "{hooks_dir}/session-start.sh"}]}
    ],
    "PostToolUse": [
        {
            "matcher": "Write|Edit",
            "hooks": [{"type": "command", "command": "{hooks_dir}/post-write.sh"}],
        }
    ],
    "Stop": [
        {"hooks": [{"type": "command", "command": "{hooks_dir}/session-stop.sh"}]}
    ],
}


def install_hooks(hooks_dir: Path, wiki: Path) -> bool:
    """Merge hook config into project-level .claude/settings.json.

    Always writes to the project-level file next to the wiki directory.
    Never modifies the global ~/.claude/settings.json.
    """
    hooks_dir = hooks_dir.resolve()
    # Build hook entries with resolved script paths
    config_str = json.dumps(HOOK_CONFIG).replace("{hooks_dir}", str(hooks_dir))
    new_hooks = json.loads(config_str)
    # Always use project-level settings, create if absent
    target = wiki.parent / ".claude" / "settings.json"

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        existing = {}
        if target.exists():
            with contextlib.suppress(json.JSONDecodeError):
                existing = json.loads(target.read_text())
        current_hooks = existing.setdefault("hooks", {})

        for event, entries in new_hooks.items():
            if event not in current_hooks:
                current_hooks[event] = entries
            else:
                # Avoid duplicating if already installed (check by command)
                existing_cmds = {
                    h.get("command", "")
                    for group in current_hooks[event]
                    for h in group.get("hooks", [])
                }
                for entry in entries:
                    for hook in entry.get("hooks", []):
                        if hook.get("command") not in existing_cmds:
                            current_hooks[event].append(entry)

        target.write_text(json.dumps(existing, indent=2))
        return True
    except OSError:
        return False


def main():
    if len(sys.argv) < 2:
        print("usage: scaffold.py <wiki_path> [domain]", file=sys.stderr)
        sys.exit(1)
    wiki = Path(sys.argv[1]).expanduser().resolve()
    domain = sys.argv[2] if len(sys.argv) > 2 else "PM"
    today = date.today().isoformat()

    if wiki.exists() and any(wiki.iterdir()):
        print(f"warning: {wiki} is not empty. refusing to scaffold.", file=sys.stderr)
        sys.exit(2)

    wiki.mkdir(parents=True, exist_ok=True)
    for sub in SUBDIRS:
        (wiki / sub).mkdir(parents=True, exist_ok=True)

    # SCHEMA.md
    schema = (TEMPLATES / "SCHEMA.md").read_text()
    schema = schema.replace(
        "Product management knowledge base.",
        f"{domain} knowledge base.",
    )
    (wiki / "SCHEMA.md").write_text(schema)

    # index.md
    idx = (TEMPLATES / "index.md").read_text().replace("YYYY-MM-DD", today)
    (wiki / "index.md").write_text(idx)

    # log.md
    log = (TEMPLATES / "log.md").read_text()
    log += f"\n## [{today}] create | Wiki initialized\n"
    log += f"- Domain: {domain}\n"
    log += "- Structure scaffolded with SCHEMA.md, index.md, overview.md, log.md\n"
    (wiki / "log.md").write_text(log)

    # overview.md
    ov = (TEMPLATES / "overview.md").read_text().replace("YYYY-MM-DD", today)
    (wiki / "overview.md").write_text(ov)

    # Install Claude Code hooks into .claude/settings.json
    hooks_installed = install_hooks(SCRIPT_DIR.parent / "hooks", wiki)
    print(f"ok: wiki scaffolded at {wiki}")
    print("next: review SCHEMA.md tag taxonomy, then ingest first source.")
    print(f"  export WIKI_PATH={wiki}")
    if hooks_installed:
        print("hooks: installed into .claude/settings.json")
    else:
        print("hooks: could not install automatically. See hooks/README.md.")


if __name__ == "__main__":
    main()
