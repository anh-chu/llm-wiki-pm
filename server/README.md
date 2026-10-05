# wiki-mcp

A small MCP server over a Markdown wiki, so a remote client such as ChatGPT can search, read and (optionally) edit it. It is separate from the plugin: the plugin runs inside Claude Code, this serves the same wiki over HTTP.

## What runs where

| Service | Port | Auth | Tools | Who connects |
|---|---|---|---|---|
| `wiki-mcp` | 37843, loopback | none | read-only | Claude Code and other local clients |
| `wiki-mcp-public` | 37844, loopback or LAN | Cloudflare Access JWT on every request | read, plus write with `WIKI_WRITE=1` | ChatGPT, through Cloudflare |
| `obsidian-mcp` | 37842, loopback | none | search backend only | the two servers above |

Never expose 37843 or 37842. Only 37844 may sit behind a public route.

## Tools

Read: `wiki_search` (ranked BM25), `wiki_scan` (exhaustive regex, tag or frontmatter scan with a total), `wiki_read`, `wiki_read_many`, `wiki_list`, `wiki_links`, `wiki_info`, `wiki_guide` (instructions the client should follow).

Write, only when `WIKI_WRITE=1`: `wiki_create_page`, `wiki_edit`, `wiki_append`, `wiki_archive_page`. Rules, enforced in `wiki_write.py`:

- Pages only under `entities/`, `concepts/`, `comparisons/`, `queries/`. Never `raw/`, `_archive/`, root files, `..` or symlink escapes.
- `wiki_read` returns a content `hash`. Edit, append and archive must pass it, so a stale read is refused.
- Frontmatter must parse and carry the required fields, tags must exist in `SCHEMA.md`, at least 2 `[[wikilinks]]`, no em-dashes, no `private:`, and `shareable: true` cannot be set. Create and append need an inline `[source: ...]`. Only problems a change introduces are blocked, so legacy pages stay editable.
- Every write snapshots the old page to `_archive/`, writes atomically, re-reads to verify, appends to `log.md`, and updates `index.md` on create and archive. Archive moves a page to `_archive/` and never hard-deletes.

## Setup

Needs [uv](https://docs.astral.sh/uv/) and the wiki at `WIKI_PATH` (default `~/workspace/wiki`). The write tools import helpers from `../skills/llm-wiki-pm/scripts/lint.py`, so keep this directory inside the plugin checkout.

```bash
uv venv ~/.local/share/wiki-mcp/venv
uv pip install --python ~/.local/share/wiki-mcp/venv/bin/python -r requirements.txt
```

The pinned `mcp` 2.x needs a recent Python (the reference setup runs 3.14). The unit files expect the venv at that path.

Install [obsidian-mcp](https://github.com/lstpsche/obsidian-mcp) so the binary is at `~/.local/bin/obsidian-mcp`, then copy the units, edit paths if yours differ, and start them:

```bash
cp systemd/*.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now obsidian-mcp wiki-mcp
```

Point Claude Code at `http://127.0.0.1:37843/mcp` (streamable HTTP).

## Public instance for ChatGPT

Cloudflare Access does the OAuth sign-in with ChatGPT at the edge (Managed OAuth) and forwards a signed `Cf-Access-Jwt-Assertion` header. `wiki_cfaccess.py` checks it on every request: signature against your team keys, audience, issuer, expiry and an email allowlist. Anything that reaches the origin without a valid assertion gets 401, including a LAN path that skips Cloudflare.

1. **Access application.** In Zero Trust create a self-hosted application for a new hostname such as `wiki-mcp.example.com`, with an allow policy for your email. Copy its Audience (AUD) tag. In Advanced settings turn on Managed OAuth and allow the redirect URIs `https://chatgpt.com/connector_platform_oauth_redirect` and `https://chatgpt.com/connector/oauth/*`. Cloudflare recommends a 5 to 15 minute access token lifetime with a one to two week grant session. The same can be done with the `cf` CLI: `cf zero-trust access applications create --body '<json>'`, then `update` with an `oauth_configuration` object (`enabled`, `dynamic_client_registration.allowed_uris`, `grant.access_token_lifetime`, `grant.session_duration`).
2. **Env file.** `cp systemd/cf-access.env.example ~/.config/wiki-mcp/cf-access.env`, fill in the team domain, AUD tag, your email and the public hostname, then `chmod 600` it.
3. **Bind address.** In `wiki-mcp-public.service` set `WIKI_MCP_HOST` to `127.0.0.1` if your reverse proxy runs on this machine, or to this machine's LAN address if it runs elsewhere (and open port 37844 to that host only). Remove `WIKI_WRITE=1` for a read-only public instance.
4. **Route.** Point your tunnel or reverse proxy for the hostname at `127.0.0.1:37844` (or the LAN address). Proxies must forward the original `Host` header, or add the upstream address as an allowed host (the server already allows `<bind-ip>:37844`).
5. **Start.** `systemctl --user enable --now wiki-mcp-public`.
6. **Check.** `curl -s https://<host>/.well-known/oauth-authorization-server` must list `S256` under `code_challenge_methods_supported` and a `registration_endpoint`; ChatGPT needs both. An unauthenticated `POST /mcp` should return 401.
7. **ChatGPT.** Enable Developer Mode, add a custom MCP app with `https://<host>/mcp`, and sign in. Ask it to call `wiki_guide` first.

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `WIKI_PATH` | `~/workspace/wiki` | Wiki directory |
| `WIKI_MCP_HOST`, `WIKI_MCP_PORT` | `127.0.0.1`, `37843` | Bind address |
| `WIKI_SEARCH_BACKEND` | `http://127.0.0.1:37842/mcp` | obsidian-mcp endpoint |
| `WIKI_AUTH` | unset | `cf-access` requires a valid Access assertion |
| `CF_ACCESS_TEAM_DOMAIN`, `CF_ACCESS_AUD`, `WIKI_ALLOWED_EMAILS` | | Required with `cf-access` |
| `WIKI_PUBLIC_HOST` | unset | Public hostname the proxy forwards (allowed Host value) |
| `WIKI_WRITE` | unset | `1` registers the write tools |

## Tests

Both suites start their own server on a spare port against a temp vault and touch no real data. They use only the packages in the venv above.

```bash
~/.local/share/wiki-mcp/venv/bin/python tests/test_cf_access.py
~/.local/share/wiki-mcp/venv/bin/python tests/test_write.py
```

## Troubleshooting

- **421 Misdirected Request:** the `Host` header is not allowed. Set `WIKI_PUBLIC_HOST` to the public hostname, or make the proxy forward the original Host.
- **401 on every request:** the token is missing or for another application. Check the AUD tag, the team domain, and that the request really went through Cloudflare Access.
- **Service will not start:** `journalctl --user -u wiki-mcp-public`. Common causes are the unreplaced `WIKI_MCP_HOST` placeholder, a missing env file, or a LAN address that changed.
- **A new page is not searchable:** confirm `OBSIDIAN_WATCH=true` on the search backend.
- **Undo a write:** the previous version is in `_archive/`, and `log.md` records each change as "via wiki-mcp (ChatGPT)".
