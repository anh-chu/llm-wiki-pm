"""wiki-search-filter.py — stdio MCP filter between Claude Code and obsidian-mcp.

obsidian-mcp returns every match in every hit file, plus a structuredContent
copy, so one natural-language search can be 100K+ characters. This sits on the
JSON-RPC stream and trims responses to roughly what wiki-mcp's wiki_search
returns (server/wiki_mcp.py): cleaned query, a few snippets per file, match
counts, and a total size cap. Stdlib only.

Usage: python3 wiki-search-filter.py <obsidian-mcp> <vault>
"""
import json
import re
import subprocess
import sys
import threading

STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "that", "this", "with", "from", "what",
    "which", "who", "whom", "how", "did", "does", "has", "have", "had", "can", "will",
    "into", "than", "then", "about", "their", "there", "when", "where", "any", "all",
}
MAX_CHARS = 20000
LIST_CAP = {"vault_list": 400}  # default 100

pending = {}  # request id -> (tool name, arguments), for tools/call and tools/list
out_lock = threading.Lock()  # both threads write to stdout


def clean_query(q):
    """Words only (tantivy chokes on : + [ ] etc.), no stopwords, at most 12 terms."""
    terms = [t for t in re.findall(r"\w+", q) if len(t) > 2 and t.lower() not in STOPWORDS]
    if len(terms) > 12:  # a full sentence: keep the longest (usually rarest) terms, in order
        keep = set(sorted(range(len(terms)), key=lambda i: -len(terms[i]))[:12])
        terms = [t for i, t in enumerate(terms) if i in keep]
    return " ".join(terms)


def rewrite_call(params):
    name, args = params.get("name"), params.setdefault("arguments", {})
    if name == "search_text":
        q = args.get("query", "")
        args["query"] = clean_query(q) or " ".join(re.findall(r"\w+", q)) or q
        args.setdefault("max_results", 8)
        args.setdefault("context_length", 120)
    elif name == "search_regex":
        args.setdefault("max_results", 20)
        args.setdefault("context_length", 120)


def trim_hits(hits, extra=None):
    out = []
    for h in hits:
        seen, snippets = set(), []
        for m in h.get("matches", []):
            if m.get("line") in seen:
                continue
            seen.add(m.get("line"))
            if len(snippets) < 2:
                snippets.append({"line": m.get("line"), "text": re.sub(r"\s+", " ", m.get("context", "")).strip()[:200]})
        out.append({"path": h.get("path"), "matches": len(h.get("matches", [])), "snippets": snippets})
    return dict(extra or {}, results=out)


def trim(name, data, args):
    if name in ("search_text", "search_regex") and isinstance(data, list):
        return trim_hits(data, {"query_used": args.get("query")} if name == "search_text" else None)
    if name == "search_metadata" and isinstance(data, list):
        rows = [{k: r.get(k) for k in ("path", "title", "tags")} for r in data]
        return {"total": len(rows), "results": rows[:100]}
    cap = LIST_CAP.get(name, 100)
    if isinstance(data, list) and len(data) > cap:  # wikilinks, vault_list
        return {"total": len(data), "results": data[:cap], "note": f"first {cap} shown; narrow with path or glob"}
    return data


def filter_result(name, args, result):
    result.pop("structuredContent", None)
    content = result.get("content") or []
    if result.get("isError") or not content or content[0].get("type") != "text":
        return
    text = content[0]["text"]
    try:
        text = json.dumps(trim(name, json.loads(text), args), indent=1, ensure_ascii=False)
    except ValueError:
        pass  # not JSON (e.g. tree view); size cap still applies
    if len(text) > MAX_CHARS and name != "note_read":
        text = text[:MAX_CHARS] + "\n... [truncated: narrow the query, lower max_results, or note_read one file]"
    content[0]["text"] = text


def upstream(child):
    """Claude Code -> obsidian-mcp."""
    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if msg.get("method") == "server/discover":
            # obsidian-mcp 3.1.0 answers Claude Code's 2026-07-28 discovery probe,
            # then rejects the legacy-session tools/list that follows (missing
            # per-request _meta). Declining the probe keeps the session legacy.
            send({"jsonrpc": "2.0", "id": msg.get("id"), "error": {"code": -32601, "message": "Method not found"}})
            continue
        if msg.get("method") == "tools/call" and "id" in msg:
            rewrite_call(msg.get("params", {}))
            pending[msg["id"]] = (msg["params"].get("name"), msg["params"].get("arguments", {}))
        elif msg.get("method") == "tools/list" and "id" in msg:
            pending[msg["id"]] = ("tools/list", None)
        child.stdin.write(json.dumps(msg) + "\n")
        child.stdin.flush()
    child.stdin.close()


def downstream(msg):
    """obsidian-mcp -> Claude Code: strip output schemas, trim tool results."""
    is_response = "id" in msg and "method" not in msg  # not a server-initiated request
    name, args = pending.pop(msg["id"], (None, None)) if is_response else (None, None)
    if name == "tools/list":
        for tool in msg.get("result", {}).get("tools", []):
            tool.pop("outputSchema", None)  # results are reshaped, so the declared schema no longer holds
    elif name and isinstance(msg.get("result"), dict):
        filter_result(name, args, msg["result"])
    return msg


def send(msg):
    with out_lock:
        sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
        sys.stdout.flush()


def main():
    child = subprocess.Popen(sys.argv[1:], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
    threading.Thread(target=upstream, args=(child,), daemon=True).start()
    for line in child.stdout:
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        send(downstream(msg))
    child.wait()


if __name__ == "__main__":
    main()
