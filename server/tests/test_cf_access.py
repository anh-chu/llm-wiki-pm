"""Tests for the Cloudflare Access gate (WIKI_AUTH=cf-access) with a stub JWKS. Run with the server venv:
    ~/.local/share/wiki-mcp/venv/bin/python tests/test_cf_access.py
Starts its own server on 37846 and a stub JWKS on 37902; touches no real data."""
import asyncio, json, os, subprocess, sys, tempfile, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx2 as httpx, jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

HERE = os.path.dirname(os.path.abspath(__file__))
PORT, JW = 37846, 37902
URL = f"http://127.0.0.1:{PORT}/mcp"
TEAM, AUD, EMAIL = "team.cloudflareaccess.com", "aud-tag-123", "anh.chu@katalon.com"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        pub = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(KEY.public_key())); pub.update(kid="k1", alg="RS256", use="sig")
        body = json.dumps({"keys": [pub]}).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.end_headers(); self.wfile.write(body)


def mint(key=KEY, **over):
    c = {"iss": f"https://{TEAM}", "aud": [AUD], "email": EMAIL, "sub": "u1", "iat": int(time.time()), "exp": int(time.time()) + 300}
    c.update(over)
    return jwt.encode(c, key, algorithm="RS256", headers={"kid": "k1"})


results = []
def check(name, cond, detail=""):
    results.append(cond); print(("PASS " if cond else "FAIL ") + name + (f"  [{detail}]" if detail and not cond else ""))


def post(token, host=None):
    h = {"Accept": "application/json, text/event-stream", "Content-Type": "application/json"}
    if token is not None: h["Cf-Access-Jwt-Assertion"] = token
    if host: h["Host"] = host
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}}}
    return httpx.post(URL, json=init, headers=h, timeout=10)


async def session(token):
    h = httpx.AsyncClient(headers={"Cf-Access-Jwt-Assertion": token}, timeout=10)
    async with streamable_http_client(URL, http_client=h) as st:
        async with ClientSession(st[0], st[1]) as s:
            await s.initialize(); tl = await s.list_tools(); info = await s.call_tool("wiki_info", {})
            return len(tl.tools), info.content[0].text


def main():
    threading.Thread(target=lambda: HTTPServer(("127.0.0.1", JW), Stub).serve_forever(), daemon=True).start()
    tmp = tempfile.mkdtemp(); vault = os.path.join(tmp, "wiki"); os.makedirs(vault)
    open(os.path.join(vault, "a.md"), "w").write("---\ntitle: A\n---\nhello\n")
    env = dict(os.environ, WIKI_PATH=vault, WIKI_AUTH="cf-access", WIKI_MCP_PORT=str(PORT), CF_ACCESS_TEAM_DOMAIN=TEAM,
               CF_ACCESS_AUD=AUD, WIKI_ALLOWED_EMAILS=EMAIL, CF_ACCESS_JWKS_URL=f"http://127.0.0.1:{JW}/certs",
               WIKI_PUBLIC_HOST="wiki.example.com")
    srv = subprocess.Popen([sys.executable, os.path.join(HERE, "..", "wiki_mcp.py")], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    good = mint()
    try:
        for _ in range(50):
            try: post(None); break
            except Exception: time.sleep(0.2)
        check("no assertion header -> 401", post(None).status_code == 401)
        check("garbage token -> 401", post("not-a-jwt").status_code == 401)
        check("wrong audience -> 401", post(mint(aud=["other"])).status_code == 401)
        check("wrong issuer -> 401", post(mint(iss="https://evil.cloudflareaccess.com")).status_code == 401)
        check("expired -> 401", post(mint(exp=int(time.time()) - 10)).status_code == 401)
        check("email not on allowlist -> 401", post(mint(email="other@katalon.com")).status_code == 401)
        check("missing email claim -> 401", post(mint(email="")).status_code == 401)
        check("signed with a different key -> 401", post(mint(key=OTHER)).status_code == 401)
        forged = jwt.encode({"iss": f"https://{TEAM}", "aud": [AUD], "email": EMAIL, "exp": int(time.time()) + 300, "iat": int(time.time())}, "secret-secret-secret-secret-1234", algorithm="HS256", headers={"kid": "k1"})
        check("HS256-forged token -> 401", post(forged).status_code == 401)
        check("unsigned (alg none) token -> 401", post(jwt.encode({"iss": f"https://{TEAM}", "aud": [AUD], "email": EMAIL, "exp": int(time.time()) + 300, "iat": int(time.time())}, None, algorithm="none")).status_code == 401)
        r = post(good); check("valid assertion -> 200", r.status_code == 200, r.status_code)
        try:
            n, info = asyncio.run(session(good)); check("full MCP session works with a valid assertion", n >= 7 and '"files":1' in info, (n, info[:100]))
        except Exception as e:
            check("full MCP session works with a valid assertion", False, repr(e)[:200])
        check("public hostname accepted with a valid assertion", post(good, host="wiki.example.com").status_code == 200)
        check("unknown Host rejected even with a valid assertion", post(good, host="evil.example").status_code == 421)
    finally:
        srv.terminate()
        try: log = srv.communicate(timeout=5)[1].decode()
        except Exception: log = ""
        check("server log does not contain the token", good not in log and "eyJ" not in log)
    print(f"\n{sum(results)}/{len(results)} passed"); sys.exit(0 if all(results) else 1)


main()
