"""Tests for hooks/wiki-search-filter.py (trims obsidian-mcp responses)."""

import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path

FILTER = Path(__file__).resolve().parent.parent / "hooks" / "wiki-search-filter.py"
spec = importlib.util.spec_from_file_location("wiki_search_filter", FILTER)
wsf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wsf)


def hit(path, n):
    return {"path": path, "score": 1.0, "matches": [{"line": i, "context": f"ctx {i} " + "x" * 300} for i in range(n)]}


def call(name, args, id_=1):
    return {"jsonrpc": "2.0", "id": id_, "method": "tools/call", "params": {"name": name, "arguments": args}}


def response(id_, data):
    text = json.dumps(data)
    return {"jsonrpc": "2.0", "id": id_, "result": {"content": [{"type": "text", "text": text}], "structuredContent": {"results": data}}}


class TestCleanQuery:
    def test_drops_stopwords_and_punctuation(self):
        assert wsf.clean_query("what is the 272k limit?") == "272k limit"

    def test_strips_tantivy_syntax(self):
        assert wsf.clean_query("pricing: tiers") == "pricing tiers"

    def test_long_sentence_keeps_twelve_terms_in_order(self):
        q = " ".join(f"term{i:02d}" for i in range(20))
        assert wsf.clean_query(q).split() == [f"term{i:02d}" for i in range(12)]


class TestRewriteCall:
    def test_search_text_defaults(self):
        params = {"name": "search_text", "arguments": {"query": "what is Kai?"}}
        wsf.rewrite_call(params)
        assert params["arguments"] == {"query": "Kai", "max_results": 8, "context_length": 120}

    def test_short_words_fall_back_to_plain_words(self):
        params = {"name": "search_text", "arguments": {"query": "AI + QA"}}
        wsf.rewrite_call(params)
        assert params["arguments"]["query"] == "AI QA"

    def test_explicit_max_results_kept(self):
        params = {"name": "search_text", "arguments": {"query": "pricing", "max_results": 3}}
        wsf.rewrite_call(params)
        assert params["arguments"]["max_results"] == 3


class TestDownstream:
    def setup_method(self):
        wsf.pending.clear()

    def test_search_text_trimmed_to_two_snippets_and_count(self):
        wsf.pending[1] = ("search_text", {"query": "pricing"})
        msg = wsf.downstream(response(1, [hit("a.md", 50), hit("b.md", 1)]))
        assert "structuredContent" not in msg["result"]
        data = json.loads(msg["result"]["content"][0]["text"])
        assert data["query_used"] == "pricing"
        assert [r["matches"] for r in data["results"]] == [50, 1]
        assert len(data["results"][0]["snippets"]) == 2
        assert all(len(s["text"]) <= 200 for s in data["results"][0]["snippets"])

    def test_tools_list_drops_output_schema(self):
        wsf.pending[7] = ("tools/list", None)
        msg = {"jsonrpc": "2.0", "id": 7, "result": {"tools": [{"name": "search_text", "outputSchema": {}}]}}
        assert "outputSchema" not in wsf.downstream(msg)["result"]["tools"][0]

    def test_long_list_capped_with_total(self):
        wsf.pending[2] = ("wikilinks", {"query": "orphans"})
        data = json.loads(wsf.downstream(response(2, [{"path": f"p{i}.md"} for i in range(250)]))["result"]["content"][0]["text"])
        assert data["total"] == 250 and len(data["results"]) == 100

    def test_size_cap(self):
        wsf.pending[3] = ("vault_list", {})
        msg = response(3, [{"path": "x" * 200} for i in range(399)])
        text = wsf.downstream(msg)["result"]["content"][0]["text"]
        assert len(text) < wsf.MAX_CHARS + 200 and text.endswith("one file]")

    def test_errors_pass_through(self):
        wsf.pending[4] = ("search_text", {"query": "x"})
        err = {"jsonrpc": "2.0", "id": 4, "error": {"code": -32603, "message": "tantivy query parse error"}}
        assert wsf.downstream(json.loads(json.dumps(err))) == err

    def test_server_request_does_not_consume_pending_id(self):
        wsf.pending[5] = ("search_text", {"query": "x"})
        ping = {"jsonrpc": "2.0", "id": 5, "method": "ping"}
        assert wsf.downstream(dict(ping)) == ping
        assert 5 in wsf.pending

    def test_unrelated_messages_untouched(self):
        note = {"jsonrpc": "2.0", "method": "notifications/tools/list_changed"}
        assert wsf.downstream(dict(note)) == note


def test_end_to_end_with_fake_server(tmp_path):
    """Pipe plumbing: the filter rewrites the request and trims the reply."""
    fake = tmp_path / "fake_server.py"
    fake.write_text(textwrap.dedent(f"""
        import json, sys
        for line in sys.stdin:
            msg = json.loads(line)
            if msg.get("method") == "tools/call":
                args = msg["params"]["arguments"]
                hits = [{{"path": "seen-" + args["query"].replace(" ", "_") + ".md", "matches": [{{"line": i, "context": "c"}} for i in range(9)]}}]
                out = {{"jsonrpc": "2.0", "id": msg["id"], "result": {{"content": [{{"type": "text", "text": json.dumps(hits)}}], "structuredContent": {{}}}}}}
                print(json.dumps(out), flush=True)
    """))
    probe = {"jsonrpc": "2.0", "id": "probe-1", "method": "server/discover", "params": {}}
    proc = subprocess.run(
        [sys.executable, str(FILTER), sys.executable, str(fake)],
        input=json.dumps(probe) + "\n" + json.dumps(call("search_text", {"query": "what is the 272k limit?"})) + "\n",
        capture_output=True, text=True, timeout=30,
    )
    replies = {m["id"]: m for m in map(json.loads, proc.stdout.strip().splitlines())}
    assert replies["probe-1"]["error"]["code"] == -32601  # discovery declined, never forwarded
    msg = replies[1]
    assert "structuredContent" not in msg["result"]
    data = json.loads(msg["result"]["content"][0]["text"])
    assert data["results"][0] == {"path": "seen-272k_limit.md", "matches": 9, "snippets": [{"line": 0, "text": "c"}, {"line": 1, "text": "c"}]}
