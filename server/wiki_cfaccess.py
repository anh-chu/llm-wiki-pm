"""Cloudflare Access gate for wiki-mcp (WIKI_AUTH=cf-access).

Access (with Managed OAuth turned on for the application) does the OAuth dance with ChatGPT and
the Google sign-in at the edge, then forwards a signed assertion in the Cf-Access-Jwt-Assertion
header. This middleware is the origin-side check Cloudflare requires: every request must carry a
valid assertion for THIS application and an allowlisted email. Requests that reach the origin
without going through Access (for example a LAN path straight to Caddy) get a 401.

Env:
  CF_ACCESS_TEAM_DOMAIN  e.g. myteam.cloudflareaccess.com
  CF_ACCESS_AUD          the Access application's Audience (AUD) tag
  WIKI_ALLOWED_EMAILS    comma-separated exact addresses
  CF_ACCESS_JWKS_URL     default https://<team domain>/cdn-cgi/access/certs (override for tests)
"""

import asyncio
import json
import os
import sys

import jwt


def _log(msg):
    print(f"[wiki-cfaccess] {msg}", file=sys.stderr, flush=True)


class CfAccessMiddleware:
    def __init__(self, app, team_domain, aud, emails, jwks_url=None):
        self.app = app
        self.issuer = f"https://{team_domain}"
        self.aud = aud
        self.emails = {e.strip().lower() for e in emails if e.strip()}
        if not self.emails:
            raise ValueError("WIKI_ALLOWED_EMAILS must list at least one address")
        self.jwks = jwt.PyJWKClient(jwks_url or f"{self.issuer}/cdn-cgi/access/certs")

    @classmethod
    def from_env(cls, app, env=os.environ):
        return cls(app, env["CF_ACCESS_TEAM_DOMAIN"], env["CF_ACCESS_AUD"],
                   env["WIKI_ALLOWED_EMAILS"].split(","), env.get("CF_ACCESS_JWKS_URL"))

    def _check(self, token):
        try:
            key = self.jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(token, key.key, algorithms=["RS256"], audience=self.aud, issuer=self.issuer,
                                options={"require": ["exp", "iat", "iss", "aud"]})
        except Exception as e:
            return f"invalid token ({type(e).__name__})"
        if str(claims.get("email", "")).lower() not in self.emails:
            return "email not on the allowlist"
        return None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        token = dict(scope["headers"]).get(b"cf-access-jwt-assertion", b"").decode()
        problem = await asyncio.to_thread(self._check, token) if token else "no Access assertion"
        if problem:
            _log(f"refused {scope['method']} {scope['path']}: {problem}")
            body = json.dumps({"error": "unauthorized"}).encode()
            await send({"type": "http.response.start", "status": 401,
                        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
            await send({"type": "http.response.body", "body": body})
            return
        await self.app(scope, receive, send)
