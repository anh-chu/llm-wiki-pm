#!/bin/sh
# obsidian-mcp-fetch.sh — Print the path of a usable obsidian-mcp binary,
# downloading the pinned release on first use.
# Order: obsidian-mcp 3.x on PATH > cached pinned binary > download + verify.
# Used by wiki-search.sh (launch) and session-start.sh (background pre-fetch,
# so the first MCP connect does not wait on a download).
# POSIX sh only (see wiki-search.sh).

set -eu

VERSION=3.1.0

# User-managed install (cargo, package manager) wins if it is a 3.x build.
if command -v obsidian-mcp >/dev/null 2>&1; then
  case "$(obsidian-mcp --version 2>/dev/null)" in
    "obsidian-mcp 3."*) command -v obsidian-mcp; exit 0 ;;
  esac
fi

DIR="${XDG_CACHE_HOME:-$HOME/.cache}/llm-wiki-pm/obsidian-mcp-$VERSION"
BIN="$DIR/obsidian-mcp"
[ -x "$BIN" ] && { echo "$BIN"; exit 0; }

# Checksums pinned here rather than fetched from the same release.
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64)          TARGET=x86_64-unknown-linux-gnu   SUM=308ff9ac0052bc7d1f13fa81e19cc019736113ca98910ebf0fcc8c057acb9e63 ;;
  Linux-aarch64|Linux-arm64) TARGET=aarch64-unknown-linux-gnu SUM=b8d16a052a5dbcfcb2bbd02c7ec9a8be889ac82bc8eec8aaf611b96b3ae47422 ;;
  Darwin-arm64)          TARGET=aarch64-apple-darwin       SUM=6a7794f7e6bf5e823a4dce023f18601f03c8cd87350113895c1579b058ac15dc ;;
  Darwin-x86_64)         TARGET=x86_64-apple-darwin        SUM=9fe7f330f540acd3593ce261a13ef5c8da347667ca59bcedb8a016f45a20ceb7 ;;
  *) echo "wiki-search: no prebuilt obsidian-mcp for $(uname -s)-$(uname -m); run 'cargo install obsidian-mcp' and put it on PATH" >&2; exit 1 ;;
esac

ASSET="obsidian-mcp-$VERSION-$TARGET.tar.gz"
URL="https://github.com/lstpsche/obsidian-mcp/releases/download/v$VERSION/$ASSET"

mkdir -p "$DIR"
TMP=$(mktemp -d "$DIR/.dl.XXXXXX")
trap 'rm -rf "$TMP"' EXIT

if command -v curl >/dev/null 2>&1; then
  curl -fsSL -o "$TMP/$ASSET" "$URL"
elif command -v wget >/dev/null 2>&1; then
  wget -q -O "$TMP/$ASSET" "$URL"
else
  echo "wiki-search: need curl or wget to download obsidian-mcp" >&2; exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  GOT=$(sha256sum "$TMP/$ASSET" | cut -d' ' -f1)
else
  GOT=$(shasum -a 256 "$TMP/$ASSET" | cut -d' ' -f1)
fi
[ "$GOT" = "$SUM" ] || { echo "wiki-search: checksum mismatch for $ASSET" >&2; exit 1; }

tar -xzf "$TMP/$ASSET" -C "$TMP" obsidian-mcp
chmod +x "$TMP/obsidian-mcp"
mv -f "$TMP/obsidian-mcp" "$BIN"  # atomic within $DIR, safe if two sessions race
echo "$BIN"
