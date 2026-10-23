#!/usr/bin/env python3
"""prompt-recall.py — UserPromptSubmit hook: point the model at wiki pages that
match the user's prompt, so it reads them instead of asking for facts the wiki holds.

Two tiers, at most MAX_PAGES pages and MAX_BYTES bytes, name matches first:
  1. name match: the page's file slug or title head appears as a phrase in the prompt
  2. ranked match: BM25 over entities/ concepts/ comparisons/ queries/, title and
     file name weighted 3x, included only above THRESHOLD
Prints only paths, titles, updated dates and confidence; never page bodies.
Every failure exits 0 with no output. Stdlib only.
"""
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter

DIRS = ("entities", "concepts", "comparisons", "queries")
MAX_PAGES = 3
MAX_BYTES = 600
MIN_WORDS = 3  # content words needed for the ranked tier
THRESHOLD = 10.0  # BM25 score; tuned on a 30-prompt eval of a real wiki (247 pages)
TITLE_WEIGHT = 3
K1, B = 1.2, 0.75
HEADER = "Wiki pages that may be relevant (read before asking the user for facts):"
STOP = set("""
a an the and or but not no nor so if then than that this these those there their them they
it its is are was were be been being am do does did done has have had having will would shall
should can could may might must of on in at to for from with by as into onto about over under
up down out off via per i me my we us our you your he she his her who whom whose what which
when where why how all any some each every both few more most other such only own same too
very just also again ever here now get got let make made need want use using please thanks ok
okay yes yeah yep sure go going one two new like know think see look sounds right well still
""".split())
TOKEN = re.compile(r"[a-z0-9][a-z0-9-]*[a-z0-9]|[a-z0-9]{2}")


def tokens(text):
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP]


def phrase(text):
    """Lowercase words joined by single spaces, padded so ' x ' finds whole words."""
    return " " + " ".join(re.findall(r"[a-z0-9]+", text.lower())) + " "


def frontmatter(text):
    """Flat key: value pairs from a leading --- block; {} when absent or malformed."""
    m = re.match(r"---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).splitlines():
        k, sep, v = line.partition(":")
        if sep and k and not k.startswith((" ", "\t", "-")):
            fm[k.strip()] = v.strip().strip("\"'")
    return fm


def resolve_wiki():
    here = os.path.dirname(os.path.abspath(__file__))
    out = subprocess.run(["sh", os.path.join(here, "resolve-wiki.sh")],
                         capture_output=True, text=True, timeout=2).stdout.strip()
    return os.path.expanduser(out) if out else ""


def page_paths(wiki):
    for d in DIRS:
        for root, dirs, files in os.walk(os.path.join(wiki, d)):
            dirs[:] = sorted(x for x in dirs if not x.startswith("."))
            for f in sorted(files):
                if f.endswith(".md"):
                    yield os.path.relpath(os.path.join(root, f), wiki).replace(os.sep, "/")


def read(wiki, rel):
    with open(os.path.join(wiki, rel), encoding="utf-8", errors="replace") as fh:
        return fh.read()


def slug(rel):
    return os.path.basename(rel)[:-3]


def title_head(title):
    """Title before ' — ', without parentheticals: 'Tokio Marine HCC (TMHCC)' -> 'Tokio Marine HCC'."""
    return re.sub(r"\([^)]*\)", " ", title.split(" — ")[0])


def name_hit(p, names):
    return any(len(n.strip()) >= 3 and n in p for n in names)


def bm25(counts, words):
    """{path: score > 0} for the query words over {path: Counter of tokens}."""
    n = len(counts)
    if not n:
        return {}
    lengths = {r: sum(c.values()) for r, c in counts.items()}
    avg = sum(lengths.values()) / n or 1
    query = list(dict.fromkeys(words))
    df = {w: sum(1 for c in counts.values() if c[w]) for w in query}
    scores = {}
    for r, c in counts.items():
        s = 0.0
        for w in query:
            tf = c[w]
            if tf:
                idf = math.log(1 + (n - df[w] + 0.5) / (df[w] + 0.5))
                s += idf * tf * (K1 + 1) / (tf + K1 * (1 - B + B * lengths[r] / avg))
        if s:
            scores[r] = s
    return scores


def recall(wiki, prompt):
    words = tokens(prompt)
    if not words:
        return []
    p = phrase(prompt)
    paths = list(page_paths(wiki))

    if len(words) < MIN_WORDS:
        # Short prompt: file-name match only, no corpus read.
        hits = [r for r in paths if name_hit(p, [phrase(slug(r).replace("-", " "))])]
        hits.sort(key=lambda r: -len(slug(r)))
        return [(r, frontmatter(read(wiki, r))) for r in hits[:MAX_PAGES]]

    docs = {}
    for r in paths:
        text = read(wiki, r)
        fm = frontmatter(text)
        title = fm.get("title") or slug(r)
        head = tokens(title + " " + slug(r).replace("-", " "))
        docs[r] = (fm, title, Counter(head * TITLE_WEIGHT + tokens(text)))
    scores = bm25({r: c for r, (_, _, c) in docs.items()}, words)
    by_score = lambda r: -scores.get(r, 0.0)
    named = sorted((r for r, (_, title, _) in docs.items()
                    if name_hit(p, [phrase(slug(r).replace("-", " ")), phrase(title_head(title))])),
                   key=by_score)
    ranked = [r for r in sorted(scores, key=by_score) if scores[r] >= THRESHOLD and r not in named]
    return [(r, docs[r][0]) for r in (named + ranked)[:MAX_PAGES]]


def render(pages):
    lines = [HEADER]
    for rel, fm in pages:
        title = fm.get("title") or slug(rel)
        if len(title) > 90:
            title = title[:89].rstrip() + "…"
        meta = ", ".join(x for x in (fm.get("updated") and "updated " + fm["updated"],
                                     fm.get("confidence")) if x)
        line = f"- {rel} — {title}" + (f" ({meta})" if meta else "")
        if len("\n".join(lines + [line]).encode()) > MAX_BYTES:
            break
        lines.append(line)
    return "\n".join(lines) if len(lines) > 1 else ""


def main():
    prompt = json.loads(sys.stdin.read()).get("prompt")
    if not isinstance(prompt, str):
        return
    prompt = prompt.strip()
    if not prompt or prompt.startswith(("/", "<")):
        return
    wiki = resolve_wiki()
    if not wiki or not os.path.isdir(wiki):
        return
    ctx = render(recall(wiki, prompt))
    if ctx:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit",
                                                 "additionalContext": ctx}}))


if __name__ == "__main__":
    try:
        main()
    except BaseException:  # fail open: never block or noise up a prompt
        pass
    sys.exit(0)
