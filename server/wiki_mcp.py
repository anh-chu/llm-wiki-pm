#!/usr/bin/env python3
"""wiki-mcp: bounded MCP server over a Markdown wiki. Read-only unless WIKI_WRITE=1 (see wiki_write.py).

Ranked search is delegated to a local obsidian-mcp daemon (BM25). Everything
else (read, list, exhaustive scan, links) runs directly over the files, so a
scan always covers every file in scope and reports a total. Every response is
capped at MAX_BYTES and says when it was truncated.

Run:  WIKI_PATH=~/workspace/wiki python wiki_mcp.py
Env:  WIKI_PATH, WIKI_MCP_HOST (127.0.0.1), WIKI_MCP_PORT (37843), WIKI_AUTH (cf-access), WIKI_PUBLIC_HOST,
      WIKI_SEARCH_BACKEND (http://127.0.0.1:37842/mcp), WIKI_WRITE (1 enables create/edit/append)
"""

import asyncio
import fnmatch
import hashlib
import json
import os
import re
import time
from pathlib import Path

import yaml
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

VAULT = Path(os.environ.get("WIKI_PATH", "~/workspace/wiki")).expanduser().resolve()
BACKEND = os.environ.get("WIKI_SEARCH_BACKEND", "http://127.0.0.1:37842/mcp")
MAX_BYTES = 24000
SKIP_DIRS = {".git", "node_modules", ".obsidian", ".obsidian-mcp", ".markdown_vault_mcp"}
TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".csv", ".html"}
STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "that", "this", "with", "from", "what",
    "which", "who", "whom", "how", "did", "does", "has", "have", "had", "can", "will",
    "into", "than", "then", "about", "their", "there", "when", "where", "any", "all",
}
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---(?:\n|$)", re.DOTALL)

_cache = {}  # relpath -> (mtime_ns, text, frontmatter dict, frontmatter error)

READ_ONLY = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)

WRITE = os.environ.get("WIKI_WRITE") == "1"  # guarded write tools, see wiki_write.py

# WIKI_AUTH=cf-access requires a valid Cloudflare Access assertion on every request (wiki_cfaccess.py).
# Run the authenticated instance on its own port and expose ONLY that one through a tunnel;
# the plain instance is for local clients.
mcp = MCPServer(
    "wiki-mcp",
    instructions=(
        "Read-only access to a PM knowledge wiki. Use wiki_search for ranked lookup "
        "with a few distinctive keywords (not full questions). Use wiki_scan when you "
        "must cover everything in a scope: it reports the total number of matching files "
        "and pages through them. Use wiki_read / wiki_read_many for page text. Every "
        "response is size-capped; follow next_offset when truncated is true. "
        "Call wiki_guide once at the start of a conversation for how to answer from this wiki."
        + (" Writes are enabled: read a page with wiki_read first, then use wiki_edit or wiki_append with its hash; "
           "wiki_create_page only for a new topic; wiki_archive_page to remove one." if WRITE else "")
    ),
)


def _dump(obj):
    """Serialize and keep the result under MAX_BYTES by trimming its main list."""
    s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    key = next((k for k in ("results", "files", "notes") if isinstance(obj.get(k), list)), None)
    while len(s.encode()) > MAX_BYTES and key and obj[key]:
        obj[key] = obj[key][: max(1, int(len(obj[key]) * 0.8))] if len(obj[key]) > 1 else []
        obj["truncated"] = True
        if "offset" in obj and "next_offset" in obj:
            obj["next_offset"] = obj["offset"] + len(obj[key])
        s = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return s


def _files(prefix=""):
    """Every text file under VAULT/prefix as relative paths, with cached content."""
    base = _safe(prefix) if prefix else VAULT
    out = []
    for root, dirs, names in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for n in sorted(names):
            if Path(n).suffix.lower() in TEXT_SUFFIXES:
                out.append(str((Path(root) / n).relative_to(VAULT)))
    return out


def _safe(rel):
    p = (VAULT / rel).resolve()
    if p != VAULT and VAULT not in p.parents:
        raise ValueError("path is outside the wiki")
    if any(part in SKIP_DIRS for part in p.relative_to(VAULT).parts):
        raise ValueError("path is in an excluded directory")
    return p


def _load(rel):
    p = VAULT / rel
    m = p.stat().st_mtime_ns
    hit = _cache.get(rel)
    if hit and hit[0] == m:
        return hit
    text = p.read_text(encoding="utf-8", errors="replace")
    fm, err = {}, None
    mm = FRONTMATTER_RE.match(text) if rel.endswith(".md") else None
    if mm:
        try:
            parsed = yaml.safe_load(mm.group(1))
            fm = parsed if isinstance(parsed, dict) else {}
        except yaml.YAMLError as e:
            err = str(e).splitlines()[0]
    _cache[rel] = (m, text, fm, err)
    return _cache[rel]


def _as_list(v):
    return [str(x) for x in v] if isinstance(v, list) else ([] if v is None else [str(v)])


def _snippet(text, start, width=160):
    a = max(0, start - width // 2)
    return re.sub(r"\s+", " ", text[a : a + width]).strip()


@mcp.tool(annotations=READ_ONLY)
async def wiki_search(query: str, limit: int = 8) -> str:
    """Ranked keyword search (BM25). Pass 2-6 distinctive terms, not a sentence.
    Returns the best files with a few snippets each and the match count per file."""
    limit = max(1, min(limit, 20))
    terms = [t for t in re.findall(r"\w+", query) if len(t) > 2 and t.lower() not in STOPWORDS]
    if len(terms) > 12:  # a full sentence: keep the longest (usually rarest) terms, in original order
        keep = set(sorted(range(len(terms)), key=lambda i: -len(terms[i]))[:12])
        terms = [t for i, t in enumerate(terms) if i in keep]
    if not terms:
        return _dump({"error": "no usable search terms (words of 3+ letters)", "results": []})
    used = " ".join(terms)
    try:
        async with streamable_http_client(BACKEND) as streams:
            async with ClientSession(streams[0], streams[1]) as sess:
                await asyncio.wait_for(sess.initialize(), 10)
                res = await asyncio.wait_for(
                    sess.call_tool("search_text", {"query": used, "max_results": limit, "context_length": 120}), 30
                )
        hits = json.loads(res.content[0].text)
    except Exception as e:  # backend down, timeout, or tantivy parse error
        return _dump({"error": f"search backend failed: {type(e).__name__}", "query_used": used, "results": []})
    results = []
    for h in hits[:limit]:
        seen, snippets = set(), []
        for m in h.get("matches", []):
            if m["line"] in seen:
                continue
            seen.add(m["line"])
            if len(snippets) < 2:
                snippets.append({"line": m["line"], "text": re.sub(r"\s+", " ", m["context"]).strip()[:200]})
        results.append({"path": h["path"], "matches": len(h.get("matches", [])), "snippets": snippets})
    return _dump({"query_used": used, "results": results, "truncated": False})


@mcp.tool(annotations=READ_ONLY)
def wiki_read(path: str, offset: int = 0, max_chars: int = 12000) -> str:
    """Read one file. Returns up to max_chars from offset and next_offset when more remains."""
    try:
        p = _safe(path)
        rel = str(p.relative_to(VAULT))
        if p.suffix.lower() not in TEXT_SUFFIXES or not p.is_file():
            return json.dumps({"error": "not a readable text file", "path": path})
    except (ValueError, OSError) as e:
        return json.dumps({"error": str(e), "path": path})
    _, text, _, err = _load(rel)
    max_chars = max(100, min(max_chars, 20000))
    chunk = text[offset : offset + max_chars]
    nxt = offset + len(chunk)
    out = {"path": rel, "hash": hashlib.sha256(p.read_bytes()).hexdigest()[:16], "total_chars": len(text), "offset": offset,
           "next_offset": nxt if nxt < len(text) else None, "content": chunk}
    if err:
        out["frontmatter_error"] = err
    return json.dumps(out, ensure_ascii=False, separators=(",", ":"))


@mcp.tool(annotations=READ_ONLY)
def wiki_read_many(paths: list[str], max_chars_each: int = 3000) -> str:
    """Read the start of up to 10 files at once. Use wiki_read with an offset for the rest."""
    paths = paths[:10]
    budget = max(200, min(max_chars_each, 6000, (MAX_BYTES - 1000) // max(1, len(paths)) - 150))
    notes = []
    for path in paths:
        try:
            p = _safe(path)
            rel = str(p.relative_to(VAULT))
            _, text, _, _ = _load(rel)
            notes.append({"path": rel, "hash": hashlib.sha256(p.read_bytes()).hexdigest()[:16],
                          "total_chars": len(text), "truncated": len(text) > budget,
                          "content": text[:budget]})
        except (ValueError, OSError) as e:
            notes.append({"path": path, "error": str(e)})
    return _dump({"notes": notes, "truncated": False})


@mcp.tool(annotations=READ_ONLY)
def wiki_list(path: str = "", glob: str = "*.md", recursive: bool = True, offset: int = 0, limit: int = 200) -> str:
    """List files under a folder (glob matches the file name). Reports the total count and pages with offset."""
    try:
        rels = _files(path)
    except (ValueError, OSError) as e:
        return json.dumps({"error": str(e)})
    base = str(_safe(path).relative_to(VAULT)) if path else ""
    rels = [r for r in rels if fnmatch.fnmatch(os.path.basename(r), glob)]
    if not recursive:
        rels = [r for r in rels if os.path.dirname(r) == base]
    page = rels[offset : offset + max(1, min(limit, 500))]
    nxt = offset + len(page)
    return _dump({"total": len(rels), "offset": offset, "next_offset": nxt if nxt < len(rels) else None,
                  "files": page, "truncated": False})


@mcp.tool(annotations=READ_ONLY)
def wiki_scan(regex: str = "", tag: str = "", field: str = "", value: str = "", path: str = "",
              ignore_case: bool = True, offset: int = 0, limit: int = 100) -> str:
    """Exhaustive scan of every file in scope (path prefix). Filters: regex over the full file text,
    tag in frontmatter tags, or frontmatter field equal to value. Combine filters to AND them.
    Always returns scope_files (files examined) and total (files matching), then pages through matches."""
    if not (regex or tag or field):
        return json.dumps({"error": "give at least one of regex, tag, or field"})
    try:
        pat = re.compile(regex, re.I | re.M if ignore_case else re.M) if regex else None
        rels = _files(path)
    except (re.error, ValueError, OSError) as e:
        return json.dumps({"error": str(e)})
    hits, fm_errors = [], 0
    for rel in rels:
        _, text, fm, err = _load(rel)
        fm_errors += bool(err)
        if tag and tag.lower() not in [t.lower() for t in _as_list(fm.get("tags"))]:
            continue
        if field and value.lower() not in [v.lower() for v in _as_list(fm.get(field))]:
            continue
        item = {"path": rel}
        if pat:
            ms = list(pat.finditer(text))
            if not ms:
                continue
            item["matches"] = len(ms)
            item["snippet"] = _snippet(text, ms[0].start())
        hits.append(item)
    page = hits[offset : offset + max(1, min(limit, 300))]
    nxt = offset + len(page)
    return _dump({"scope_files": len(rels), "total": len(hits), "offset": offset,
                  "next_offset": nxt if nxt < len(hits) else None, "frontmatter_errors_in_scope": fm_errors,
                  "results": page, "truncated": False})


@mcp.tool(annotations=READ_ONLY)
def wiki_links(path: str) -> str:
    """Outgoing [[wikilinks]] of a page and the pages that link to it (backlinks)."""
    try:
        rel = str(_safe(path).relative_to(VAULT))
        _, text, _, _ = _load(rel)
    except (ValueError, OSError) as e:
        return json.dumps({"error": str(e)})
    stem = Path(rel).stem
    outgoing = sorted({m.strip() for m in WIKILINK_RE.findall(text)})
    back = []
    for r in _files():
        if r != rel and r.endswith(".md") and any(
            m.strip() in (stem, str(Path(rel).with_suffix(""))) for m in WIKILINK_RE.findall(_load(r)[1])
        ):
            back.append(r)
    return _dump({"path": rel, "outgoing_total": len(outgoing), "outgoing": outgoing[:100],
                  "backlinks_total": len(back), "results": back[:100], "truncated": False})


@mcp.tool(annotations=READ_ONLY)
def wiki_guide() -> str:
    """How to answer from this wiki: tool choice, citation, staleness and privacy rules. Call once at the start of a conversation."""
    here = Path(__file__).parent
    return (here / "wiki_guide.md").read_text() + ((here / "wiki_guide_write.md").read_text() if WRITE else "")


@mcp.tool(annotations=READ_ONLY)
def wiki_info() -> str:
    """Wiki size and health: file counts, pages whose frontmatter fails to parse, newest change."""
    rels = _files()
    bad, newest = [], ("", 0)
    for r in rels:
        m, _, _, err = _load(r)
        if err:
            bad.append(r)
        if m > newest[1]:
            newest = (r, m)
    return _dump({"wiki": VAULT.name, "files": len(rels), "markdown": sum(r.endswith(".md") for r in rels),
                  "frontmatter_parse_errors": len(bad), "results": bad[:20],
                  "newest_file": newest[0], "newest_age_seconds": int(time.time() - newest[1] / 1e9) if newest[1] else None,
                  "truncated": False})


if WRITE:
    import wiki_write

    wiki_write.register(mcp, VAULT)


def _allowed_hosts(host, port):
    hosts = [f"127.0.0.1:{port}", f"localhost:{port}"]
    if host not in ("127.0.0.1", "localhost", "0.0.0.0"):  # LAN bind: a proxy that rewrites Host to the upstream address
        hosts.append(f"{host}:{port}")
    if os.environ.get("WIKI_PUBLIC_HOST"):  # requests arrive through the tunnel carrying the public hostname
        hosts.append(os.environ["WIKI_PUBLIC_HOST"])
    return hosts


if __name__ == "__main__":
    from mcp.server.transport_security import TransportSecuritySettings

    host = os.environ.get("WIKI_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("WIKI_MCP_PORT", "37843"))
    security = TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=_allowed_hosts(host, port))
    if os.environ.get("WIKI_AUTH") == "cf-access":
        import uvicorn

        from wiki_cfaccess import CfAccessMiddleware

        app = mcp.streamable_http_app(host=host, transport_security=security)
        gated = CfAccessMiddleware.from_env(app)
        uvicorn.run(gated, host=host, port=port, log_level="info")
    else:
        mcp.run(transport="streamable-http", host=host, port=port, transport_security=security)
