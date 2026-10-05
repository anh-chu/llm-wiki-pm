"""Guarded write tools for wiki-mcp (enabled only with WIKI_WRITE=1).

Three operations on knowledge pages (entities/ concepts/ comparisons/ queries/ only): create, exact
edit, append. Edit and append must present the content hash from wiki_read, so a stale read can never
overwrite newer text. Each write is validated against the wiki's own rules (frontmatter, SCHEMA.md tag
taxonomy, >=2 wikilinks, provenance), snapshotted to _archive/, written atomically, re-read to verify,
and logged in log.md. raw/, _archive/, root files and anything outside the four dirs are unreachable.
"""

import datetime
import difflib
import functools
import hashlib
import importlib.util
import json
import os
import re
import tempfile
import threading
from pathlib import Path

import yaml
from mcp.types import ToolAnnotations

ALLOWED_DIRS = ("entities", "concepts", "comparisons", "queries")
INDEX_SECTIONS = {d: f"## {d.capitalize()}" for d in ALLOWED_DIRS}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\.md$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
EM_DASH = "—"
MAX_DIFF = 6000
VIA = "via wiki-mcp (ChatGPT)"

_lock = threading.Lock()


class Refused(Exception):
    def __init__(self, *errors):
        self.errors = list(errors)


@functools.lru_cache(maxsize=1)
def _lint():
    p = Path(__file__).resolve().parents[1] / "skills" / "llm-wiki-pm" / "scripts" / "lint.py"
    spec = importlib.util.spec_from_file_location("wiki_lint", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def sha(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode()).hexdigest()[:16]


def _atomic(path, data):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".wiki-mcp-")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data if isinstance(data, bytes) else data.encode())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _resolve(vault, path, create):
    rel = Path(path)
    if rel.is_absolute() or ".." in rel.parts or len(rel.parts) < 2 or rel.parts[0] not in ALLOWED_DIRS:
        raise Refused(f"path must be inside one of: {', '.join(d + '/' for d in ALLOWED_DIRS)} (no '..', no absolute paths)")
    real_vault = vault.resolve()
    top = (vault / rel.parts[0]).resolve()
    p = (vault / rel).resolve()
    if top.parent != real_vault or top not in p.parents:
        raise Refused("path resolves outside the wiki directory")
    if rel.suffix != ".md" or rel.name.startswith("lint-"):
        raise Refused("only .md knowledge pages can be written (lint reports are generated)")
    if create:
        if len(rel.parts) != 2 or not NAME_RE.match(rel.name):
            raise Refused("new pages go directly in a directory with a lowercase-hyphen name, e.g. entities/acme-corp.md")
        if os.path.lexists(vault / rel):
            raise Refused(f"{path} already exists; use wiki_edit or wiki_append (read it first with wiki_read)")
    elif not p.is_file():
        raise Refused(f"{path} does not exist")
    return rel.as_posix(), p


def _problems(text, taxonomy, lint):
    m = lint.FRONTMATTER_RE.match(text)
    if not m:
        return ["page must start with a '---' YAML frontmatter block"]
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as e:
        return [f"frontmatter is not valid YAML: {str(e).splitlines()[0]}"]
    if not isinstance(fm, dict):
        return ["frontmatter must be a YAML mapping"]
    errs = []
    missing = sorted(lint.REQUIRED_FRONTMATTER - set(fm))
    if missing:
        errs.append(f"missing frontmatter fields: {', '.join(missing)}")
    if "private" in fm:
        errs.append("remove the `private:` field; pages are private by default (use shareable: true only for public-safe pages)")
    if str(fm.get("shareable")).lower() in ("true", "yes"):
        errs.append("shareable: true cannot be set through this connector (it publishes the page to exports); set it in the wiki directly")
    tags = fm.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            errs.append("tags must be a list, e.g. tags: [company, competitive]")
        else:
            bad = sorted(str(t) for t in tags if str(t) not in taxonomy)
            if bad:
                errs.append(f"tags not in the SCHEMA.md taxonomy: {', '.join(bad)}")
    for k in ("created", "updated"):
        if k in fm and not DATE_RE.match(str(fm[k])):
            errs.append(f"{k} must be YYYY-MM-DD")
    if len({x.strip() for x in lint.WIKILINK_RE.findall(text)}) < 2:
        errs.append("page needs at least 2 distinct outbound [[wikilinks]]")
    return errs


def _grounded(text, lint):
    m = lint.FRONTMATTER_RE.match(text)
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except Exception:
        fm = {}
    srcs = fm.get("sources") if isinstance(fm, dict) else None
    primary = [s for s in srcs if not str(s).startswith(lint.WIKI_PAGE_PREFIXES)] if isinstance(srcs, list) else []
    return bool(primary) or bool(lint.INLINE_PROVENANCE_RE.search(text))


def _stamp(text, today):
    m = _lint().FRONTMATTER_RE.match(text)
    if not m:
        return text
    fm = m.group(1)
    fm2 = re.sub(r"^updated:.*$", f"updated: {today}", fm, count=1, flags=re.M) if re.search(r"^updated:", fm, re.M) \
        else fm + f"\nupdated: {today}"
    return text[: m.start(1)] + fm2 + text[m.end(1):]


def _snapshot(vault, p):
    arc = vault / "_archive"
    arc.mkdir(exist_ok=True)
    data = p.read_bytes()
    base = f"{p.stem}-{datetime.date.today().isoformat()}"
    snap, n = arc / f"{base}.md", 0
    while snap.exists():  # never overwrite an earlier pre-image; identical content is already saved
        if snap.read_bytes() == data:
            return snap.relative_to(vault).as_posix()
        n += 1
        snap = arc / f"{base}-{n}.md"
    _atomic(snap, data)
    return snap.relative_to(vault).as_posix()


def _log(vault, action, rel, reason, today):
    lp = vault / "log.md"
    prev = lp.read_text() if lp.exists() else ""
    lead = "" if not prev or prev.endswith("\n") else "\n"
    with open(lp, "a") as f:
        f.write(f"{lead}\n## [{today}] {action} | {rel} | source: {VIA}\n{reason.strip()}\n")


def _index_add(vault, rel, title, summary):
    ip = vault / "index.md"
    if not ip.exists():
        return "no index.md"
    text = ip.read_text()
    if f"({rel})" in text or f"[[{Path(rel).stem}]]" in text:
        return "already listed"
    lines = text.split("\n")
    header = INDEX_SECTIONS[rel.split("/")[0]]
    start = next((i for i, ln in enumerate(lines) if ln.rstrip() == header), None)
    if start is None:
        return f"section '{header}' not found; add the index line manually"
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    bullets = [i for i in range(start + 1, end) if lines[i].startswith("- ")]
    last = bullets[-1] if bullets else (start + 1 if lines[start + 1].startswith("<!--") else start)
    summary = " ".join(summary.split()).replace(EM_DASH, "-")[:220]
    lines.insert(last + 1, f"- [{title}]({rel}) - {summary}")
    _atomic(ip, "\n".join(lines))
    return "added"


def _diff(old, new, rel):
    d = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), f"a/{rel}", f"b/{rel}", n=2))
    return d if len(d) <= MAX_DIFF else d[:MAX_DIFF] + "\n... diff truncated"


def _commit(vault, rel, p, old, new, action, reason, extra_errors_before=None, index=None):
    """Validate (new problems only), snapshot, write, verify, log. Returns the result dict."""
    lint = _lint()
    today = datetime.date.today().isoformat()
    taxonomy = lint.load_taxonomy(vault / "SCHEMA.md")
    if not taxonomy:
        raise Refused("SCHEMA.md with a tag taxonomy is missing; writes are disabled until it exists")
    new = _stamp(new, today)
    before = set(_problems(_stamp(old, today), taxonomy, lint)) if old is not None else set()
    after = _problems(new, taxonomy, lint)
    errors = [e for e in after if e not in before]
    if errors:
        raise Refused(*errors)
    snap = _snapshot(vault, p) if old is not None else None
    _atomic(p, new)
    back = p.read_bytes()
    if sha(back) != sha(new) or [e for e in _problems(back.decode(), taxonomy, lint) if e not in before]:
        if old is not None:
            _atomic(p, old)
        else:
            p.unlink()
        raise Refused("write verification failed; the change was rolled back")
    out = {"ok": True, "path": rel, "action": action, "hash": sha(back), "snapshot": snap,
           "diff": _diff(old or "", new, rel)}
    for what, step in (("index", lambda: _index_add(vault, rel, index[0], index[1]) if index else None),
                       ("log", lambda: _log(vault, action, rel, reason, today))):
        try:
            res = step()
            if res:
                out[what] = res
        except Exception as e:  # the page is already written and verified; say what bookkeeping is missing
            out.setdefault("warnings", []).append(f"page written but {what}.md update failed ({type(e).__name__}); add the entry manually")
    return out


def _guard(fn):
    @functools.wraps(fn)
    def run(*a, **k):
        try:
            with _lock:
                return json.dumps(fn(*a, **k), ensure_ascii=False)
        except Refused as r:
            return json.dumps({"ok": False, "errors": r.errors, "written": False}, ensure_ascii=False)
        except (OSError, UnicodeDecodeError) as e:
            return json.dumps({"ok": False, "errors": [f"write failed: {type(e).__name__}"], "written": False})
    return run


def _index_remove(vault, rel):
    ip = vault / "index.md"
    if not ip.exists():
        return "no index.md"
    stem = Path(rel).stem
    lines = ip.read_text().split("\n")
    keep = [ln for ln in lines if not (ln.startswith("- ") and (f"({rel})" in ln or f"[[{stem}]]" in ln))]
    if len(keep) == len(lines):
        return "not listed"
    _atomic(ip, "\n".join(keep))
    return f"removed {len(lines) - len(keep)} line(s)"


def _inbound(vault, rel, limit=30):
    stem, hits = Path(rel).stem, []
    for d in ALLOWED_DIRS:
        for f in sorted((vault / d).rglob("*.md")):
            r = f.relative_to(vault).as_posix()
            if r != rel and not f.name.startswith("lint-"):
                try:
                    t = f.read_text(errors="replace")
                except OSError:
                    continue
                if f"[[{stem}]]" in t or f"[[{stem}|" in t or f"({rel})" in t:
                    hits.append(r)
    return hits[:limit]


def _check_prose(text, what):
    if EM_DASH in text:
        raise Refused(f"{what} contains an em-dash; use a comma, colon or hyphen instead")


def register(mcp, vault):
    lint = _lint()

    def _existing(path, expected_hash):
        rel, p = _resolve(vault, path, create=False)
        raw = p.read_bytes()
        if sha(raw) != expected_hash:
            raise Refused("the page changed since you read it (hash mismatch); wiki_read it again and redo the change")
        return rel, p, raw.decode("utf-8")

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False))
    @_guard
    def wiki_create_page(path: str, content: str, summary: str, reason: str) -> str:
        """Create a NEW knowledge page (fails if it exists). path: entities|concepts|comparisons|queries/<lowercase-hyphen>.md.
        content: the whole page including YAML frontmatter (title, created, updated, type, tags from SCHEMA.md, sources),
        at least 2 [[wikilinks]], and inline [source: ...] markers (use [source: conversation, YYYY-MM-DD] for chat facts).
        summary: one line for index.md. reason: one line for log.md. Errors come back as a list; fix them and retry."""
        rel, p = _resolve(vault, path, create=True)
        content = content.replace("\r\n", "\n")
        _check_prose(content, "content")
        if not _grounded(content, lint):
            raise Refused("page has no primary source: add a non-wiki entry to sources: or inline [source: ...] markers")
        m = lint.FRONTMATTER_RE.match(content)
        title = (yaml.safe_load(m.group(1)) or {}).get("title", p.stem) if m else p.stem
        return _commit(vault, rel, p, None, content if content.endswith("\n") else content + "\n", "create", reason,
                       index=(str(title), summary))

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
    @_guard
    def wiki_edit(path: str, old_string: str, new_string: str, expected_hash: str, reason: str) -> str:
        """Replace one exact passage in an existing page. old_string must match exactly once (include enough context).
        expected_hash is the 'hash' returned by wiki_read for this page; a stale hash is refused. The previous version is
        snapshotted to _archive/ and `updated:` is set to today. New facts need an inline [source: ...] marker."""
        rel, p, text = _existing(path, expected_hash)
        _check_prose(new_string, "new_string")
        n = text.count(old_string) if old_string else 0
        if n != 1:
            raise Refused(f"old_string must match exactly once; it matched {n} times")
        return _commit(vault, rel, p, text, text.replace(old_string, new_string, 1), "update", reason)

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=False, idempotent_hint=False, open_world_hint=False))
    @_guard
    def wiki_append(path: str, text: str, expected_hash: str, reason: str) -> str:
        """Append text to the end of an existing page, e.g. a dated section for a new fact. text must carry an inline
        [source: ...] marker. expected_hash is the 'hash' from wiki_read. The previous version is snapshotted and
        `updated:` is set to today."""
        rel, p, old = _existing(path, expected_hash)
        _check_prose(text, "text")
        if not lint.INLINE_PROVENANCE_RE.search(text):
            raise Refused("appended text needs an inline [source: ...] marker (e.g. [source: conversation, YYYY-MM-DD])")
        return _commit(vault, rel, p, old, old.rstrip("\n") + "\n\n" + text.strip("\n") + "\n", "update", reason)

    @mcp.tool(annotations=ToolAnnotations(read_only_hint=False, destructive_hint=True, idempotent_hint=False, open_world_hint=False))
    @_guard
    def wiki_archive_page(path: str, expected_hash: str, reason: str) -> str:
        """Remove a page from the wiki by archiving it: the file moves to _archive/ with its path preserved (never hard-deleted),
        its index.md line is removed, and the move is logged. expected_hash is the 'hash' from wiki_read. Pages that still link
        to it are listed in 'inbound_links' (they are NOT rewritten, so fix or tell the user). The user can move the file back."""
        rel, p, _ = _existing(path, expected_hash)
        if (vault / rel).is_symlink():
            raise Refused("refusing to archive a symlink")
        today = datetime.date.today().isoformat()
        dest, n = vault / "_archive" / rel, 0
        while dest.exists():
            n += 1
            dest = vault / "_archive" / f"{Path(rel).with_suffix('').as_posix()}-{today}-{n}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        data = p.read_bytes()
        os.replace(p, dest)
        if dest.read_bytes() != data or p.exists():
            raise Refused("archive verification failed; check the page and _archive/ manually")
        out = {"ok": True, "path": rel, "action": "archive", "archived_to": dest.relative_to(vault).as_posix(),
               "inbound_links": _inbound(vault, rel)}
        for what, step in (("index", lambda: _index_remove(vault, rel)),
                           ("log", lambda: _log(vault, "archive", rel, reason, today))):
            try:
                res = step()
                if res:
                    out[what] = res
            except Exception as e:
                out.setdefault("warnings", []).append(f"page archived but {what}.md update failed ({type(e).__name__}); fix it manually")
        return out
