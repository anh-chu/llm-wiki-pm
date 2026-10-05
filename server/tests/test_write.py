"""Tests for the guarded write tools (WIKI_WRITE=1) against a temp vault. Run with the server venv:
    ~/.local/share/wiki-mcp/venv/bin/python tests/test_write.py
Starts its own server on 37847 (no auth, loopback); touches no real data."""
import asyncio, json, os, re, subprocess, sys, tempfile, time

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

HERE = os.path.dirname(os.path.abspath(__file__))
PORT = 37847
URL = f"http://127.0.0.1:{PORT}/mcp"
TODAY = time.strftime("%Y-%m-%d")

SCHEMA = "# Schema\n\n## Tag Taxonomy\n- `company`, org\n- `competitive`, rivals\n- `strategy`, direction\n"
INDEX = "# Wiki Index\n\n## Entities\n<!-- Alphabetical. -->\n- [[acme]]\n\n## Concepts\n\n## Comparisons\n\n## Queries\n"
PAGE = lambda title, body="Acme sells widgets [source: conversation, 2026-10-01]. See [[beta]] and [[gamma]].\n", tags="[company]", extra="": (
    f"---\ntitle: {title}\ncreated: 2026-10-01\nupdated: 2026-10-01\ntype: entity\ntags: {tags}\nsources: [raw/internal/x.md]\n{extra}---\n\n# {title}\n\n{body}")

results = []
def check(name, cond, detail=""):
    results.append(bool(cond)); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


async def run(steps):
    async with streamable_http_client(URL) as st:
        async with ClientSession(st[0], st[1]) as s:
            await s.initialize()
            async def call(tool, **a):
                return json.loads((await s.call_tool(tool, a)).content[0].text)
            return await steps(call, s)


def main():
    tmp = tempfile.mkdtemp(); vault = os.path.join(tmp, "wiki"); outside = os.path.join(tmp, "outside"); os.makedirs(outside)
    for d in ("entities", "concepts", "comparisons", "queries", "raw/internal", "_archive"):
        os.makedirs(os.path.join(vault, d))
    w = lambda rel, t: open(os.path.join(vault, rel), "w").write(t)
    rd = lambda rel: open(os.path.join(vault, rel)).read()
    w("SCHEMA.md", SCHEMA); w("index.md", INDEX); w("log.md", "# Log\n"); w("raw/internal/x.md", "raw source\n")
    w("overview.md", PAGE("Overview", body="Synthesis of [[acme]] and [[beta]] [source: conversation, 2026-10-01].\n")); w("entities/acme.md", PAGE("Acme")); w("entities/old.md", "---\ntitle: Old\n---\nno links, off schema\n")
    os.symlink(outside, os.path.join(vault, "concepts", "escape"))
    env = dict(os.environ, WIKI_PATH=vault, WIKI_MCP_PORT=str(PORT), WIKI_WRITE="1")
    env.pop("WIKI_AUTH", None)
    srv = subprocess.Popen([sys.executable, os.path.join(HERE, "..", "wiki_mcp.py")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        for _ in range(50):
            try: asyncio.run(run(lambda c, s: s.list_tools())); break
            except Exception: time.sleep(0.2)

        async def steps(call, s):
            names = {t.name for t in (await s.list_tools()).tools}
            check("write tools registered", {"wiki_create_page", "wiki_edit", "wiki_append", "wiki_archive_page"} <= names, names)
            ann = {t.name: t.annotations for t in (await s.list_tools()).tools}
            check("write tools are not marked read-only", all(not ann[n].read_only_hint for n in ("wiki_create_page", "wiki_edit", "wiki_append", "wiki_archive_page")))
            check("wiki_guide mentions writing", "Writing to the wiki" in (await s.call_tool("wiki_guide", {})).content[0].text)

            r = await call("wiki_read", path="entities/acme.md"); h0 = r["hash"]
            check("wiki_read returns a hash", bool(h0))

            # create
            r = await call("wiki_create_page", path="entities/beta.md", content=PAGE("Beta", tags="[company, competitive]"), summary="Beta, a rival", reason="test create")
            check("create ok", r.get("ok"), r)
            check("create stamps updated to today", f"updated: {TODAY}" in rd("entities/beta.md"))
            check("create adds index line under Entities after last bullet", "- [Beta](entities/beta.md) - Beta, a rival" in rd("index.md") and rd("index.md").index("[[acme]]") < rd("index.md").index("[Beta]"))
            check("create logs with provenance", f"## [{TODAY}] create | entities/beta.md | source: via wiki-mcp (ChatGPT)" in rd("log.md"))
            r = await call("wiki_create_page", path="entities/beta.md", content=PAGE("Beta"), summary="x", reason="dup")
            check("create refuses an existing page", not r["ok"] and "already exists" in r["errors"][0], r)
            check("create refuses off-taxonomy tag", "not in the SCHEMA.md taxonomy: nope" in " ".join((await call("wiki_create_page", path="entities/c1.md", content=PAGE("C", tags="[nope]"), summary="x", reason="t"))["errors"]))
            check("create refuses <2 wikilinks", "2 distinct" in " ".join((await call("wiki_create_page", path="entities/c2.md", content=PAGE("C", body="One [[beta]] [source: conversation, 2026-10-01]\n"), summary="x", reason="t"))["errors"]))
            check("create refuses em-dash", "em-dash" in " ".join((await call("wiki_create_page", path="entities/c3.md", content=PAGE("C", body="A — B [[beta]] [[acme]] [source: x]\n"), summary="x", reason="t"))["errors"]))
            check("create refuses private: field", "private" in " ".join((await call("wiki_create_page", path="entities/c4.md", content=PAGE("C", extra="private: true\n"), summary="x", reason="t"))["errors"]))
            ungrounded = PAGE("C", body="Claim without source [[beta]] [[acme]]\n").replace("sources: [raw/internal/x.md]", "sources: [entities/acme.md]")
            check("create refuses an ungrounded page", "primary source" in " ".join((await call("wiki_create_page", path="entities/c5.md", content=ungrounded, summary="x", reason="t"))["errors"]))
            check("create refuses bad filename", not (await call("wiki_create_page", path="entities/Bad_Name.md", content=PAGE("C"), summary="x", reason="t"))["ok"])
            check("no half-written files left", not [f for f in os.listdir(os.path.join(vault, "entities")) if f.startswith((".wiki-mcp-", "c1", "c2", "c3", "c4", "c5", "Bad"))], os.listdir(os.path.join(vault, "entities")))

            # path safety
            for p in ("raw/internal/new.md", "_archive/x.md", "index.md", "../escape.md", "entities/../raw/x.md", "/etc/passwd", "concepts/escape/pwn.md", "entities/sub/deep.md"):
                r = await call("wiki_create_page", path=p, content=PAGE("C"), summary="x", reason="t")
                check(f"create refuses path {p}", not r["ok"], r)
            check("symlink escape wrote nothing outside", os.listdir(outside) == [])
            r = await call("wiki_append", path="raw/internal/x.md", text="x [source: a]", expected_hash="0", reason="t")
            check("append refuses raw/", not r["ok"], r)

            # edit
            before = rd("entities/acme.md")
            r = await call("wiki_edit", path="entities/acme.md", old_string="sells widgets", new_string="sells gadgets", expected_hash="deadbeefdeadbeef", reason="t")
            check("edit with a stale hash is refused", not r["ok"] and "hash mismatch" in r["errors"][0] and rd("entities/acme.md") == before, r)
            r = await call("wiki_edit", path="entities/acme.md", old_string="nonexistent text", new_string="x", expected_hash=h0, reason="t")
            check("edit with no match is refused", not r["ok"] and "0 times" in r["errors"][0], r)
            r = await call("wiki_edit", path="entities/acme.md", old_string="sells widgets", new_string="sells gadgets", expected_hash=h0, reason="fix product word")
            check("edit ok", r.get("ok") and "sells gadgets" in rd("entities/acme.md"), r)
            check("edit snapshots the previous version", r.get("snapshot") and rd(r["snapshot"]) == before, r)
            check("edit returns a diff", "-Acme sells widgets" in r.get("diff", "") and "+Acme sells gadgets" in r.get("diff", ""))
            check("edit bumps updated", f"updated: {TODAY}" in rd("entities/acme.md"))
            r2 = await call("wiki_edit", path="entities/acme.md", old_string="sells gadgets", new_string="sells things", expected_hash=h0, reason="reuse old hash")
            check("edit with the previous hash is refused after a change", not r2["ok"], r2)
            r3 = await call("wiki_edit", path="entities/acme.md", old_string="[[beta]]", new_string="[[beta]] and x", expected_hash=r["hash"], reason="t")
            check("edit with the fresh hash works", r3.get("ok"), r3)
            r4 = await call("wiki_edit", path="entities/acme.md", old_string="[[gamma]]", new_string="plain", expected_hash=r3["hash"], reason="drops a link")
            check("edit that breaks the page rules is refused and unchanged", not r4["ok"] and "2 distinct" in " ".join(r4["errors"]) and "[[gamma]]" in rd("entities/acme.md"), r4)
            r5 = await call("wiki_edit", path="entities/acme.md", old_string="Acme", new_string="Acme", expected_hash=r3["hash"], reason="ambiguous")
            check("edit needing a unique match is refused when ambiguous", not r5["ok"] and "times" in r5["errors"][0], r5)

            # append
            h = (await call("wiki_read", path="entities/acme.md"))["hash"]
            r = await call("wiki_append", path="entities/acme.md", text="## 2026-10-06 note\nNew fact.", expected_hash=h, reason="t")
            check("append without a source marker is refused", not r["ok"] and "source" in r["errors"][0], r)
            r = await call("wiki_append", path="entities/acme.md", text="## 2026-10-06 note\nNew fact [source: conversation, 2026-10-06].", expected_hash=h, reason="add note")
            check("append ok", r.get("ok") and rd("entities/acme.md").rstrip().endswith("[source: conversation, 2026-10-06]."), r)
            check("append logged as update", f"## [{TODAY}] update | entities/acme.md" in rd("log.md"))

            # legacy page that already violates the rules can still be edited without making it worse
            ho = (await call("wiki_read", path="entities/old.md"))["hash"]
            r = await call("wiki_edit", path="entities/old.md", old_string="no links", new_string="fixed text", expected_hash=ho, reason="t")
            check("pre-existing violations do not block an unrelated edit", r.get("ok"), r)
            arc = sorted(os.listdir(os.path.join(vault, "_archive")))
            check("every pre-image kept under a distinct name", len(arc) >= 4 and "acme-%s-2.md" % TODAY in arc, arc)
            # symlink escapes on edit/append, with a CORRECT hash so only the guard can refuse
            import hashlib
            hsh = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()[:16]
            secret = os.path.join(outside, "secret.md"); open(secret, "w").write(PAGE("Secret"))
            os.symlink(secret, os.path.join(vault, "entities", "link.md"))
            r = await call("wiki_edit", path="concepts/escape/secret.md", old_string="Secret", new_string="Pwned", expected_hash=hsh(secret), reason="t")
            check("edit through a symlinked directory is refused", not r["ok"] and open(secret).read() == PAGE("Secret"), r)
            r = await call("wiki_append", path="entities/link.md", text="x [source: a]", expected_hash=hsh(secret), reason="t")
            check("append to a symlinked file is refused", not r["ok"] and open(secret).read() == PAGE("Secret"), r)
            check("nothing created outside by symlink attempts", sorted(os.listdir(outside)) == ["secret.md"])

            # archive (remove)
            await call("wiki_create_page", path="entities/gone.md", content=PAGE("Gone", body="About [[acme]] and [[beta]] [source: conversation, 2026-10-01]\n"), summary="to be archived", reason="t")
            await call("wiki_create_page", path="entities/ref.md", content=PAGE("Ref", body="Points to [[gone]] and [[acme]] [source: conversation, 2026-10-01]\n"), summary="refers", reason="t")
            hg = (await call("wiki_read", path="entities/gone.md"))["hash"]
            r = await call("wiki_archive_page", path="entities/gone.md", expected_hash="0" * 16, reason="t")
            check("archive with a stale hash is refused", not r["ok"] and os.path.exists(os.path.join(vault, "entities/gone.md")), r)
            gone_text = rd("entities/gone.md")
            r = await call("wiki_archive_page", path="entities/gone.md", expected_hash=hg, reason="superseded in test")
            check("archive ok", r.get("ok") and r["archived_to"] == "_archive/entities/gone.md", r)
            check("archived file moved intact", not os.path.exists(os.path.join(vault, "entities/gone.md")) and rd("_archive/entities/gone.md") == gone_text)
            check("archive removes the index line", "(entities/gone.md)" not in rd("index.md") and "(entities/beta.md)" in rd("index.md"))
            check("archive logs it", f"## [{TODAY}] archive | entities/gone.md | source: via wiki-mcp (ChatGPT)" in rd("log.md"))
            check("archive lists inbound links without rewriting them", r["inbound_links"] == ["entities/ref.md"] and "[[gone]]" in rd("entities/ref.md"), r)
            await call("wiki_create_page", path="entities/gone.md", content=PAGE("Gone"), summary="again", reason="t")
            r = await call("wiki_archive_page", path="entities/gone.md", expected_hash=(await call("wiki_read", path="entities/gone.md"))["hash"], reason="t")
            check("second archive of the same name never overwrites the first", r.get("ok") and r["archived_to"] != "_archive/entities/gone.md" and os.path.exists(os.path.join(vault, "_archive/entities/gone.md")), r)
            for p in ("raw/internal/x.md", "index.md", "concepts/escape/secret.md", "entities/link.md"):
                r = await call("wiki_archive_page", path=p, expected_hash=hsh(os.path.join(vault, p)) if os.path.exists(os.path.join(vault, p)) else "0", reason="t")
                check(f"archive refuses {p}", not r["ok"], r)
            check("symlink target untouched by archive attempts", open(secret).read() == PAGE("Secret") and os.path.lexists(os.path.join(vault, "entities/link.md")))

            # shareable cannot be flipped on
            h = (await call("wiki_read", path="entities/beta.md"))["hash"]
            r = await call("wiki_edit", path="entities/beta.md", old_string="type: entity", new_string="type: entity\nshareable: true", expected_hash=h, reason="t")
            check("edit cannot set shareable: true", not r["ok"] and "shareable" in " ".join(r["errors"]), r)
            r = await call("wiki_create_page", path="entities/pub.md", content=PAGE("Pub", extra="shareable: true\n"), summary="x", reason="t")
            check("create cannot set shareable: true", not r["ok"], r)

            # ---- wiki_lint is read-only
            snap = lambda: sorted((dp, f, os.path.getmtime(os.path.join(dp, f))) for dp, _, fs in os.walk(vault) for f in fs)
            before_files = snap(); r = await call("wiki_lint", tier="errors")
            check("wiki_lint returns counts per tier", set(r.get("counts", {})) == {"errors", "warnings", "info"}, r)
            check("wiki_lint writes nothing to the wiki", snap() == before_files)
            check("wiki_lint pages a tier", isinstance(r.get("results"), list) and "next_offset" in r)

            # ---- wiki_save_raw
            r = await call("wiki_save_raw", path="raw/articles/gartner-note.md", content="# Note\nPublic fact.\n", reason="capture test")
            check("save_raw ok", r.get("ok") and rd("raw/articles/gartner-note.md").startswith("# Note"), r)
            check("save_raw logs a capture", f"## [{TODAY}] capture | raw/articles/gartner-note.md" in rd("log.md"))
            check("save_raw refuses to overwrite", not (await call("wiki_save_raw", path="raw/articles/gartner-note.md", content="x", reason="t"))["ok"])
            for p in ("raw/other/x.md", "raw/internal/Bad Name.md", "raw/internal/x.exe", "raw/articles/sub/x.md", "raw/../entities/x.md", "entities/x.md", "raw/x.md"):
                check(f"save_raw refuses {p}", not (await call("wiki_save_raw", path=p, content="x", reason="t"))["ok"])
            for label, body in (("AWS key", "key AKIA" + "ABCDEFGHIJKLMNOP"), ("password", "password: hunter2hunter2hunter2"), ("private key", "-----BEGIN RSA PRIVATE KEY-----\nabc")):
                r = await call("wiki_save_raw", path="raw/internal/secret-test.md", content=body, reason="t")
                check(f"save_raw refuses content with a {label}", not r["ok"] and "secrets" in r["errors"][0] and not os.path.exists(os.path.join(vault, "raw/internal/secret-test.md")), r)
            check("save_raw error does not echo the secret", "hunter2" not in json.dumps(r))
            await call("wiki_save_raw", path="raw/internal/slack-a-2026-10-01.md", content="---\nsource_thread_id: 1712.345\n---\nthread\n", reason="t")
            r = await call("wiki_save_raw", path="raw/internal/slack-b-2026-10-01.md", content="---\nsource_thread_id: 1712.345\n---\nsame thread\n", reason="t")
            check("save_raw refuses a duplicate source_thread_id", not r["ok"] and "already captured" in r["errors"][0], r)
            r = await call("wiki_edit", path="raw/articles/gartner-note.md", old_string="Public", new_string="Private", expected_hash="0", reason="t")
            check("raw/ stays immutable through edit", not r["ok"] and "Public fact" in rd("raw/articles/gartner-note.md"))

            # ---- wiki_supersede
            mk = lambda name, body, extra="": call("wiki_create_page", path=f"entities/{name}.md", content=PAGE(name, body=body + " [source: conversation, 2026-10-01]\n", extra=extra), summary=f"{name} page", reason="t")
            await mk("v1", "Old version, see [[acme]] and [[beta]]."); await mk("v2", "New version, see [[acme]] and [[beta]].")
            await mk("p1", "Uses [[v1|the old one]] and [[v1#history]] and [link](entities/v1.md) plus [[acme]]."); await mk("p2", "Plain [[v1]] and [[beta]].")
            hv1 = (await call("wiki_read", path="entities/v1.md"))["hash"]; hv2 = (await call("wiki_read", path="entities/v2.md"))["hash"]
            files_before = {f: rd(f"entities/{f}") for f in ("v1.md", "v2.md", "p1.md", "p2.md")}; idx_before = rd("index.md")
            r = await call("wiki_supersede", old_path="entities/v1.md", new_path="entities/v2.md", old_hash=hv1, new_hash=hv2, reason="v2 replaces v1")
            check("supersede dry-run returns the plan", r.get("ok") and r["applied"] is False and r["plan"]["rewrite_links_in"] == ["entities/p1.md", "entities/p2.md"], r)
            check("supersede dry-run changes nothing", all(rd(f"entities/{f}") == v for f, v in files_before.items()) and rd("index.md") == idx_before)
            r = await call("wiki_supersede", old_path="entities/v1.md", new_path="entities/v2.md", old_hash="0" * 16, new_hash=hv2, reason="t", apply=True)
            check("supersede with a stale old_hash is refused", not r["ok"] and "hash mismatch" in r["errors"][0], r)
            r = await call("wiki_supersede", old_path="entities/v1.md", new_path="entities/v1.md", old_hash=hv1, new_hash=hv1, reason="t", apply=True)
            check("supersede refuses old == new", not r["ok"], r)
            r = await call("wiki_supersede", old_path="raw/articles/gartner-note.md", new_path="entities/v2.md", old_hash="0", new_hash=hv2, reason="t", apply=True)
            check("supersede refuses raw/", not r["ok"], r)
            r = await call("wiki_supersede", old_path="entities/v1.md", new_path="entities/v2.md", old_hash=hv1, new_hash=hv2, reason="v2 replaces v1", apply=True)
            check("supersede applies", r.get("ok") and r["applied"] and r["archived_to"] == "_archive/entities/v1.md", r)
            check("old page archived with superseded_by", not os.path.exists(os.path.join(vault, "entities/v1.md")) and "superseded_by: v2" in rd("_archive/entities/v1.md"))
            check("new page gains supersedes", "supersedes: [v1]" in rd("entities/v2.md") and f"updated: {TODAY}" in rd("entities/v2.md"))
            p1 = rd("entities/p1.md")
            check("inbound links rewritten, alias, heading and path kept", "[[v2|the old one]]" in p1 and "[[v2#history]]" in p1 and "(entities/v2.md)" in p1 and "v1" not in p1 and "[[v2]]" in rd("entities/p2.md"), p1)
            check("supersede removes the old index line and logs it", "(entities/v1.md)" not in rd("index.md") and f"## [{TODAY}] supersede | v1 \u2192 v2" in rd("log.md") and "entities/p1.md" in rd("log.md"))
            check("supersede snapshots rewritten pages", rd("_archive/p1-%s.md" % TODAY) == files_before["p1.md"])

            # ten or more inbound pages need an explicit count
            await mk("big-old", "Old, see [[acme]] and [[beta]]."); await mk("big-new", "New, see [[acme]] and [[beta]].")
            for i in range(10):
                await mk(f"ref{i}", f"Refers to [[big-old]] and [[acme]].")
            hb1 = (await call("wiki_read", path="entities/big-old.md"))["hash"]; hb2 = (await call("wiki_read", path="entities/big-new.md"))["hash"]
            kw = dict(old_path="entities/big-old.md", new_path="entities/big-new.md", old_hash=hb1, new_hash=hb2, reason="t", apply=True)
            check("10+ inbound pages: apply without a count is refused", not (await call("wiki_supersede", **kw))["ok"] and os.path.exists(os.path.join(vault, "entities/big-old.md")))
            check("10+ inbound pages: wrong count is refused", not (await call("wiki_supersede", confirm_rewrite_count=3, **kw))["ok"])
            r = await call("wiki_supersede", confirm_rewrite_count=10, **kw)
            check("10+ inbound pages: correct count applies", r.get("ok") and "[[big-new]]" in rd("entities/ref0.md") and "[[big-new]]" in rd("entities/ref9.md"), r)

            # ---- index matching only looks at a bullet's own link target
            await call("wiki_create_page", path="entities/mention.md", content=PAGE("Mention", body="x [[acme]] [[beta]] [source: conversation, 2026-10-01]\n"), summary="rival of [[tgt]] and see (entities/tgt.md)", reason="t")
            r = await call("wiki_create_page", path="entities/tgt.md", content=PAGE("Tgt", body="x [[acme]] [[beta]] [source: conversation, 2026-10-01]\n"), summary="target page", reason="t")
            check("create indexes a page whose stem appears only in another summary", r.get("index") == "added" and "- [Tgt](entities/tgt.md) - target page" in rd("index.md"), r)
            r = await call("wiki_archive_page", path="entities/tgt.md", expected_hash=r["hash"], reason="t")
            check("archive removes only the page's own index line", r.get("ok") and "(entities/tgt.md)" not in rd("index.md").replace("see (entities/tgt.md)", "") and "- [Mention](entities/mention.md) - rival of [[tgt]]" in rd("index.md"), r)

            # ---- overview.md is editable, nothing else at the root is
            ho = (await call("wiki_read", path="overview.md"))["hash"]
            r = await call("wiki_edit", path="overview.md", old_string="Synthesis of", new_string="Updated synthesis of", expected_hash=ho, reason="refresh overview")
            check("overview.md can be edited", r.get("ok") and "Updated synthesis" in rd("overview.md"), r)
            check("overview.md cannot be created or archived", not (await call("wiki_create_page", path="overview.md", content=PAGE("O"), summary="x", reason="t"))["ok"]
                  and not (await call("wiki_archive_page", path="overview.md", expected_hash=r["hash"], reason="t"))["ok"] and os.path.exists(os.path.join(vault, "overview.md")))
            for p in ("index.md", "log.md", "SCHEMA.md"):
                check(f"{p} cannot be edited", not (await call("wiki_edit", path=p, old_string="#", new_string="##", expected_hash=hsh(os.path.join(vault, p)), reason="t"))["ok"])
        asyncio.run(run(steps))
    finally:
        srv.terminate()
        try: srv.communicate(timeout=5)
        except Exception: pass
    print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)


main()
