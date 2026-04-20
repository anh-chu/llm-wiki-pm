#!/usr/bin/env python3
"""Tiered lint for PM wiki. Writes report to queries/lint-YYYY-MM-DD.md.

Usage:
    lint.py <wiki_path>              # report only
    lint.py <wiki_path> --auto-fix   # report + repair safe issues
"""

import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

REQUIRED_FRONTMATTER = {"title", "created", "updated", "type", "tags", "sources"}
WIKI_DIRS = ["entities", "concepts", "comparisons", "queries"]
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
TAG_LINE_RE = re.compile(r"tags:\s*\[(.*?)\]")
TAXONOMY_TAG_RE = re.compile(r"^- `([a-z0-9\-]+)`", re.MULTILINE)


def parse_frontmatter(text):
    m = FRONTMATTER_RE.match(text)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip()
    return fm


def extract_tags(fm):
    if not fm or "tags" not in fm:
        return []
    m = TAG_LINE_RE.search(f"tags: {fm['tags']}")
    if not m:
        return []
    return [t.strip().strip("'\"") for t in m.group(1).split(",") if t.strip()]


def load_taxonomy(schema_path):
    if not schema_path.exists():
        return set()
    return set(TAXONOMY_TAG_RE.findall(schema_path.read_text()))


def slug(path):
    return path.stem


def is_private(fm):
    return fm and fm.get("private", "").lower() in ("true", "yes")


def get_superseded_by(fm):
    if not fm:
        return None
    v = fm.get("superseded_by", "").strip()
    if v in ("", "null", "none", "~"):
        return None
    return v.strip("'\"")


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: lint.py <wiki_path> [--auto-fix]", file=sys.stderr)
        sys.exit(1)
    auto_fix = "--auto-fix" in args
    output_json = "--json" in args
    quiet = "--quiet" in args
    args = [a for a in args if not a.startswith("--")]
    wiki = Path(args[0]).expanduser().resolve()
    if not wiki.exists():
        print(f"error: {wiki} does not exist", file=sys.stderr)
        sys.exit(2)

    today = date.today().isoformat()
    pages = []
    for d in WIKI_DIRS:
        for p in (wiki / d).rglob("*.md"):
            # skip lint reports — self-generated, would cause false positives
            if p.name.startswith("lint-"):
                continue
            pages.append(p)

    slugs = {slug(p): p for p in pages}
    taxonomy = load_taxonomy(wiki / "SCHEMA.md")

    errors, warnings, info = [], [], []
    orphans_list = []
    fixes_applied = []

    inbound = defaultdict(set)
    broken = []
    tag_usage = Counter()
    superseded_pages = set()
    supersede_map = {}  # old-slug -> new-slug

    for p in pages:
        text = p.read_text()
        fm = parse_frontmatter(text)

        if fm is None:
            errors.append(f"missing frontmatter: {p.relative_to(wiki)}")
            continue
        missing = REQUIRED_FRONTMATTER - set(fm.keys())
        if missing:
            errors.append(
                f"frontmatter missing {sorted(missing)}: {p.relative_to(wiki)}"
            )

        # supersession tracking
        sb = get_superseded_by(fm)
        if sb:
            superseded_pages.add(slug(p))
            supersede_map[slug(p)] = sb
            if sb not in slugs:
                errors.append(
                    f"superseded_by points to unknown page '{sb}': {p.relative_to(wiki)}"
                )

        # tags
        tags = extract_tags(fm)
        for t in tags:
            tag_usage[t] += 1
            if taxonomy and t not in taxonomy:
                errors.append(
                    f"tag '{t}' not in SCHEMA.md taxonomy: {p.relative_to(wiki)}"
                )

        # wikilinks
        for link in WIKILINK_RE.findall(text):
            target = link.strip()
            if target in slugs and slugs[target] != p:
                inbound[target].add(slug(p))
            elif target not in slugs:
                broken.append((p, target))

        # page size
        lines = text.count("\n")
        if lines > 200:
            warnings.append(
                f"page > 200 lines ({lines}): {p.relative_to(wiki)} — split candidate"
            )

        # contradictions flagged
        if "contradictions:" in text and not re.search(
            r"contradictions:\s*\[\s*\]", text
        ):
            warnings.append(f"unresolved contradictions flag: {p.relative_to(wiki)}")

        # stale
        try:
            updated_str = fm.get("updated", "").strip()
            updated_dt = datetime.fromisoformat(updated_str).replace(
                tzinfo=timezone.utc
            )
            age_days = (datetime.now(timezone.utc) - updated_dt).days
            if age_days > 90:
                warnings.append(
                    f"stale ({age_days}d since update): {p.relative_to(wiki)}"
                )
        except Exception:
            pass

    # broken links → auto-fix if possible
    for p, target in broken:
        if auto_fix and target in supersede_map:
            new_target = supersede_map[target]
            t = p.read_text()
            t2 = re.sub(
                rf"\[\[{re.escape(target)}(\|[^\]]+)?\]\]",
                f"[[{new_target}]]",
                t,
            )
            if t2 != t:
                p.write_text(t2)
                fixes_applied.append(
                    f"rewrote broken [[{target}]] → [[{new_target}]] in {p.relative_to(wiki)}"
                )
                continue
        errors.append(f"broken [[{target}]] in {p.relative_to(wiki)}")

    # redirect links pointing to superseded pages (even if not broken)
    if auto_fix and supersede_map:
        for p in pages:
            if slug(p) in superseded_pages:
                continue  # don't rewrite the archive-bound old page itself
            text = p.read_text()
            new_text = text
            for old, new in supersede_map.items():
                new_text = re.sub(
                    rf"\[\[{re.escape(old)}(\|[^\]]+)?\]\]",
                    f"[[{new}]]",
                    new_text,
                )
            if new_text != text:
                p.write_text(new_text)
                fixes_applied.append(
                    f"redirected superseded links in {p.relative_to(wiki)}"
                )

    # orphans (superseded pages are allowed to be orphans)
    for p in pages:
        s = slug(p)
        if s in superseded_pages:
            continue
        if s not in inbound:
            warnings.append(f"orphan (zero inbound links): {p.relative_to(wiki)}")
            orphans_list.append(str(p.relative_to(wiki)))

    # index completeness → auto-fix by appending missing entries
    idx_path = wiki / "index.md"
    missing_in_index = []
    if idx_path.exists():
        idx_text = idx_path.read_text()
        for p in pages:
            s = slug(p)
            if s in superseded_pages:
                continue
            if f"[[{s}]]" not in idx_text and s not in idx_text:
                missing_in_index.append(p)
                warnings.append(f"not in index.md: {p.relative_to(wiki)}")

        if auto_fix and missing_in_index:
            # naive append: add under matching type section
            by_type = defaultdict(list)
            for p in missing_in_index:
                fm = parse_frontmatter(p.read_text()) or {}
                t = fm.get("type", "entity").strip()
                by_type[t].append(slug(p))
            section_map = {
                "entity": "## Entities",
                "concept": "## Concepts",
                "comparison": "## Comparisons",
                "query": "## Queries",
                "summary": "## Entities",
            }
            new_idx = idx_text
            for t, ss in by_type.items():
                header = section_map.get(t, "## Entities")
                for s in sorted(ss):
                    entry = f"- [[{s}]]"
                    # append entry right after the header line
                    new_idx = re.sub(
                        rf"({re.escape(header)}\n(?:<!--.*?-->\n)?)",
                        rf"\1{entry}\n",
                        new_idx,
                        count=1,
                    )
            if new_idx != idx_text:
                idx_path.write_text(new_idx)
                fixes_applied.append(
                    f"added {len(missing_in_index)} missing entries to index.md"
                )

    # log rotation
    log_path = wiki / "log.md"
    if log_path.exists():
        entries = log_path.read_text().count("\n## [")
        if entries > 500:
            info.append(f"log.md has {entries} entries — rotate to log-YYYY.md")

    # tag frequency
    for t, n in tag_usage.most_common(10):
        info.append(f"tag '{t}': {n} uses")
    rare = [t for t, n in tag_usage.items() if n == 1]
    if rare:
        info.append(f"singleton tags (consolidate?): {', '.join(sorted(rare))}")

    # report
    report_dir = wiki / "queries"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"lint-{today}.md"

    out = [
        "---",
        f"title: Lint Report {today}",
        f"created: {today}",
        f"updated: {today}",
        "type: query",
        "tags: [question]",
        "sources: []",
        "---",
        "",
        f"# Lint Report — {today}",
        "",
        f"Pages scanned: {len(pages)} | Errors: {len(errors)} | "
        f"Warnings: {len(warnings)} | Info: {len(info)}",
        f"Auto-fix: {'ON' if auto_fix else 'off'} | Fixes applied: {len(fixes_applied)}",
        "",
        f"## 🔴 Errors ({len(errors)})",
        "",
    ]
    out += [f"- {e}" for e in errors] or ["- none"]
    out += ["", f"## 🟡 Warnings ({len(warnings)})", ""]
    out += [f"- {w}" for w in warnings] or ["- none"]
    out += ["", f"## 🔵 Info ({len(info)})", ""]
    out += [f"- {i}" for i in info] or ["- none"]
    if fixes_applied:
        out += ["", f"## 🔧 Auto-fixes Applied ({len(fixes_applied)})", ""]
        out += [f"- {f}" for f in fixes_applied]
    out += ["", "## Suggested Actions", ""]
    if errors:
        out.append(
            "1. Fix 🔴 errors — broken links and missing frontmatter block navigation."
        )
    if warnings:
        out.append("2. Triage 🟡 warnings — orphans may need backlinks or archival.")
    if info:
        out.append("3. Note 🔵 info for quarterly taxonomy review.")

    report_path.write_text("\n".join(out) + "\n")

    # Output structured JSON when requested (used by hooks for health checks).
    # Using --json implies no prose on stdout.
    if output_json:
        import json

        broken_list = [e for e in errors if e.startswith("broken [[")]
        print(
            json.dumps(
                {
                    "broken_links": broken_list,
                    "orphans": orphans_list,
                    "errors": len(errors),
                    "warnings": len(warnings),
                }
            )
        )
        return
    if log_path.exists():
        with log_path.open("a") as f:
            f.write(
                f"\n## [{today}] lint | {len(errors)}E {len(warnings)}W "
                f"{len(info)}I {len(fixes_applied)}F\n"
            )
            f.write(f"- Report: queries/lint-{today}.md\n")
            if auto_fix:
                f.write(f"- Auto-fix applied {len(fixes_applied)} repairs\n")

    if not quiet:
        print(f"ok: {report_path.relative_to(wiki)}")
        print(
            f"  🔴 {len(errors)}  🟡 {len(warnings)}  🔵 {len(info)}  "
            f"🔧 {len(fixes_applied)}"
        )


if __name__ == "__main__":
    main()
