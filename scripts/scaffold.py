#!/usr/bin/env python3
"""Bootstrap a new PM wiki. Usage: scaffold.py <wiki_path> <domain>"""

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

    print(f"ok: wiki scaffolded at {wiki}")
    print("next: review SCHEMA.md tag taxonomy, then ingest first source.")
    print(f"  export WIKI_PATH={wiki}")


if __name__ == "__main__":
    main()
