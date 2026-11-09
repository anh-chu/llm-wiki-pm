#!/usr/bin/env python3
"""review-gate.py — Stop hook: a turn that read or wrote the wiki must run the
llm-wiki-review skill before it ends.

Looks at the turn since the last user prompt in the transcript. If any tool call
touched the wiki (a path under it, the wiki-search MCP, or any file tool when the
session runs inside the wiki) and the llm-wiki-review skill was not invoked, it
blocks the stop once with a reason that tells the agent to run the review.

Lets the stop through when: stop_hook_active is set (already blocked once this
turn), the prompt says "no review" or "skip review", no wiki is configured, or the
turn did not touch the wiki, or the session is itself a reviewer
(WIKI_REVIEW_RUNNING is set by the llm-wiki-review skill). Every failure exits 0 with no output. Stdlib only.
"""
import json
import os
import re
import subprocess
import sys

INJECTED = re.compile(r"^\s*<(task-notification|system-reminder|local-command|command-)")
SKIP = re.compile(r"\b(no|skip|without)[ -]review\b", re.I)
FILE_TOOLS = {"Read", "Grep", "Glob", "Write", "Edit", "MultiEdit", "NotebookEdit"}
REASON = ("This turn used the wiki, so run the llm-wiki-review skill before you finish: "
          "write your draft answer to a temp file, have the configured reviewer check every "
          "statement against its sources and search for what is missing, revise, and end "
          "with the 'Reviewed by' line. A check you ran another way (your own subagent or "
          "prompt) does not count: run the skill's run-review.sh script. The user can say "
          "'no review' to skip it.")


def resolve_wiki(cwd):
    here = os.path.dirname(os.path.abspath(__file__))
    out = subprocess.run(["sh", os.path.join(here, "resolve-wiki.sh")], cwd=cwd or None,
                         capture_output=True, text=True, timeout=2).stdout.strip()
    return os.path.realpath(os.path.expanduser(out)) if out else ""


def events(path):
    with open(path) as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue


def content(event):
    c = (event.get("message") or {}).get("content")
    return [{"type": "text", "text": c}] if isinstance(c, str) else (c or [])


def is_prompt(event):
    """A real user prompt, not a tool result fed back to the model."""
    if event.get("type") != "user" or event.get("isMeta"):
        return False
    blocks = content(event)
    if any(b.get("type") == "tool_result" for b in blocks):
        return False
    texts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    return bool(texts) and not all(INJECTED.match(t) for t in texts)


def prompt_text(event):
    return " ".join(b.get("text", "") for b in content(event) if b.get("type") == "text")


def tool_uses(turn):
    for e in turn:
        if e.get("type") == "assistant":
            for b in content(e):
                if b.get("type") == "tool_use":
                    yield b.get("name", ""), b.get("input") or {}


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from strings(v)
    elif isinstance(value, list):
        for v in value:
            yield from strings(v)


# Wiki files a turn can touch without reading content: bookkeeping and config.
META_TOP = re.compile(r"^(CLAUDE|index|SCHEMA|_status|channels|MY-INTEGRATIONS)(\.md)?(\.orig)?$"
                      r"|^log(-.*)?\.md$|^\.wiki-path$|^(meta|prompts)$")
# A relative path or search inside the wiki that names content.
RELATIVE_CONTENT = re.compile(
    r"(?:^|[\s\"'=/])(?:\./)?(?:raw|entities|concepts|comparisons|queries|briefings|drafts|exports|_archive)(?:/|\s|$)"
    r"|\b(?:people|overview)\.md\b|\b(?:grep|rg|find)\b[^|;&]*\s\.(?:\s|$)")
PATH_KEYS = ("file_path", "path", "notebook_path")


def is_content(rel):
    """rel is a path inside the wiki; the wiki root itself counts as content."""
    first = rel.strip("/").split("/")[0]
    return first in ("", ".") or not META_TOP.match(first)


def touches_wiki(name, args, wiki, inside, cwd=""):
    """The tool call read or wrote wiki content (not just bookkeeping files)."""
    if "wiki-search" in name:
        return True
    home = os.path.expanduser("~")
    if inside and name in FILE_TOOLS:
        paths = [args[k] for k in PATH_KEYS if isinstance(args.get(k), str)] or [cwd]
        for p in paths:
            full = os.path.realpath(os.path.join(cwd, os.path.expanduser(p)))
            if full == wiki or full.startswith(wiki + os.sep):
                if is_content(os.path.relpath(full, wiki)):
                    return True
    for s in strings(args):
        s = s.replace("~", home)
        for m in re.finditer(re.escape(wiki) + r"((?:/[^\s\"'`;|&)<>]*)?)", s):
            if is_content(m.group(1)):
                return True
        if inside and name == "Bash" and RELATIVE_CONTENT.search(s):
            return True
    return False


def reviewed(name, args):
    """The review script ran. Invoking the skill alone is not enough."""
    return name == "Bash" and "run-review.sh" in str(args.get("command", ""))


def decide(payload):
    if payload.get("stop_hook_active") or os.environ.get("WIKI_REVIEW_RUNNING"):
        return None
    path = payload.get("transcript_path")
    if not path or not os.path.exists(path):
        return None
    cwd = payload.get("cwd") or os.getcwd()
    wiki = resolve_wiki(cwd)
    if not wiki or not os.path.isdir(wiki):
        return None
    all_events = list(events(path))
    start = max((i for i, e in enumerate(all_events) if is_prompt(e)), default=None)
    if start is None or SKIP.search(prompt_text(all_events[start])):
        return None
    inside = os.path.realpath(cwd).startswith(wiki)
    used = list(tool_uses(all_events[start + 1:]))
    if any(reviewed(n, a) for n, a in used):
        return None
    if not any(touches_wiki(n, a, wiki, inside, cwd) for n, a in used):
        return None
    return {"decision": "block", "reason": REASON}


def main():
    try:
        out = decide(json.load(sys.stdin))
    except Exception:
        return
    if out:
        print(json.dumps(out))


if __name__ == "__main__":
    main()
