#!/usr/bin/env python3
"""Show pages that link to a given wiki page.

Usage:
    backlinks.py <wiki_path> <slug>              # human-readable
    backlinks.py <wiki_path> <slug> --json       # machine-readable
    backlinks.py <wiki_path> <slug> --context    # show the line each link appears on
"""

import json
import re
import sys
from pathlib import Path

WIKI_DIRS = ["entities", "concepts", "comparisons", "queries", "_archive"]
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")


def scan(wiki: Path, target: str, include_context: bool = False):
    hits = []
    for d in WIKI_DIRS:
        for p in (wiki / d).rglob("*.md"):
            if p.name.startswith("lint-"):
                continue
            if p.stem == target:
                continue  # self
            text = p.read_text()
            line_hits = []
            for i, line in enumerate(text.splitlines(), start=1):
                for link in WIKILINK_RE.findall(line):
                    if link.strip() == target:
                        line_hits.append((i, line.strip()))
            if line_hits:
                rel = str(p.relative_to(wiki))
                if include_context:
                    hits.append(
                        {
                            "path": rel,
                            "count": len(line_hits),
                            "lines": [{"line": ln, "text": t} for ln, t in line_hits],
                        }
                    )
                else:
                    hits.append({"path": rel, "count": len(line_hits)})
    return hits


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        print(
            "usage: backlinks.py <wiki_path> <slug> [--json] [--context]",
            file=sys.stderr,
        )
        sys.exit(1)
    as_json = "--json" in args
    include_context = "--context" in args
    args = [a for a in args if not a.startswith("--")]
    wiki = Path(args[0]).expanduser().resolve()
    target = args[1].strip().removesuffix(".md")
    if not wiki.exists():
        print(f"error: {wiki} does not exist", file=sys.stderr)
        sys.exit(2)

    hits = scan(wiki, target, include_context=include_context)

    if as_json:
        print(
            json.dumps({"target": target, "count": len(hits), "pages": hits}, indent=2)
        )
        return

    if not hits:
        print(f"no backlinks to [[{target}]]")
        return

    total = sum(h["count"] for h in hits)
    print(f"{len(hits)} page(s), {total} link(s) → [[{target}]]:")
    for h in sorted(hits, key=lambda x: -x["count"]):
        label = f"  {h['path']} ({h['count']} link{'s' if h['count'] > 1 else ''})"
        print(label)
        if include_context and "lines" in h:
            for ln in h["lines"]:
                print(f"    L{ln['line']}: {ln['text']}")


if __name__ == "__main__":
    main()
