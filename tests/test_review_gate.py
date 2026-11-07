"""review-gate.py (Stop): feed stdin JSON with a transcript, check the decision.

Run: python3 -m pytest tests/test_review_gate.py -v
"""

import json
import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "hooks" / "review-gate.py"
OPTION_VARS = ("WIKI_PATH", "CLAUDE_PLUGIN_OPTION_WIKI_PATH", "CLAUDE_PLUGIN_OPTION_wiki_path")


def prompt(text):
    return {"type": "user", "message": {"role": "user", "content": text}}


def tool(name, args, i=1):
    return [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": f"t{i}", "name": name, "input": args}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"t{i}", "content": "ok"}]}},
    ]


def answer(text="Customer A asked for SSO."):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def run(tmp_path, events, wiki=True, cwd=None, active=False):
    wiki_dir = tmp_path / "wiki"
    wiki_dir.mkdir(exist_ok=True)
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    env = {k: v for k, v in os.environ.items() if k not in OPTION_VARS}
    if wiki:
        env["CLAUDE_PLUGIN_OPTION_WIKI_PATH"] = str(wiki_dir)
    payload = {"session_id": "s1", "hook_event_name": "Stop", "transcript_path": str(transcript),
               "cwd": str(cwd or tmp_path), "stop_hook_active": active}
    out = subprocess.run(["python3", str(HOOK)], input=json.dumps(payload), capture_output=True,
                         text=True, env=env, cwd=str(cwd or tmp_path))
    assert out.returncode == 0
    return json.loads(out.stdout) if out.stdout.strip() else None


def blocked(result):
    return bool(result) and result.get("decision") == "block"


def test_wiki_read_without_review_blocks(tmp_path):
    wiki = tmp_path / "wiki"
    events = [prompt("what did customer A ask for in Q4?"),
              *tool("Read", {"file_path": f"{wiki}/entities/customer-a.md"}), answer()]
    result = run(tmp_path, events)
    assert blocked(result)
    assert "llm-wiki-review" in result["reason"]


def test_review_skill_lets_stop_through(tmp_path):
    wiki = tmp_path / "wiki"
    events = [prompt("what did customer A ask for in Q4?"),
              *tool("Read", {"file_path": f"{wiki}/entities/customer-a.md"}, 1),
              *tool("Skill", {"skill": "llm-wiki-pm:llm-wiki-review"}, 2), answer()]
    assert run(tmp_path, events) is None


def test_second_stop_in_same_turn_is_allowed(tmp_path):
    wiki = tmp_path / "wiki"
    events = [prompt("what did customer A ask for?"),
              *tool("Read", {"file_path": f"{wiki}/entities/customer-a.md"}), answer()]
    assert run(tmp_path, events, active=True) is None


def test_no_review_phrase_skips(tmp_path):
    wiki = tmp_path / "wiki"
    events = [prompt("quick, no review: list customer pages"),
              *tool("Glob", {"pattern": "*.md", "path": f"{wiki}/entities"}), answer()]
    assert run(tmp_path, events) is None


def test_turn_without_wiki_use_passes(tmp_path):
    events = [prompt("fix the build"), *tool("Read", {"file_path": "/etc/hosts"}), answer("done")]
    assert run(tmp_path, events) is None


def test_no_wiki_configured_passes(tmp_path):
    events = [prompt("what did customer A ask for?"),
              *tool("Read", {"file_path": f"{tmp_path}/wiki/entities/a.md"}), answer()]
    assert run(tmp_path, events, wiki=False) is None


def test_wiki_search_mcp_counts(tmp_path):
    events = [prompt("what did customer A ask for?"),
              *tool("mcp__plugin_llm-wiki-pm_wiki-search__search_text", {"query": "customer a"}), answer()]
    assert blocked(run(tmp_path, events))


def test_bash_with_tilde_path_counts(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    events = [prompt("what did customer A ask for?"),
              *tool("Bash", {"command": "grep -rn SSO ~/wiki/entities"}), answer()]
    assert blocked(run(tmp_path, events))


def test_relative_paths_count_inside_the_wiki(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    events = [prompt("what did customer A ask for?"),
              *tool("Grep", {"pattern": "SSO", "path": "entities"}), answer()]
    assert blocked(run(tmp_path, events, cwd=wiki))


def test_relative_bash_counts_inside_the_wiki(tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    events = [prompt("what did customer A ask for?"),
              *tool("Bash", {"command": "grep -rli customer-a --include=*.md ."}), answer()]
    assert blocked(run(tmp_path, events, cwd=wiki))


def test_reviewer_session_is_not_gated(tmp_path, monkeypatch):
    monkeypatch.setenv("WIKI_REVIEW_RUNNING", "1")
    wiki = tmp_path / "wiki"
    events = [prompt("review this draft"),
              *tool("Read", {"file_path": f"{wiki}/entities/customer-a.md"}), answer()]
    assert run(tmp_path, events) is None


def test_only_the_latest_turn_counts(tmp_path):
    wiki = tmp_path / "wiki"
    events = [prompt("what did customer A ask for?"),
              *tool("Read", {"file_path": f"{wiki}/entities/customer-a.md"}, 1),
              *tool("Skill", {"skill": "llm-wiki-review"}, 2), answer(),
              prompt("thanks, now fix the build"),
              *tool("Read", {"file_path": "/etc/hosts"}, 3), answer("done")]
    assert run(tmp_path, events) is None
    events += [prompt("and what about customer B?"),
               *tool("Read", {"file_path": f"{wiki}/entities/customer-b.md"}, 4), answer()]
    assert blocked(run(tmp_path, events))


def test_background_task_notification_is_not_a_new_prompt(tmp_path):
    wiki = tmp_path / "wiki"
    events = [prompt("what did customer A ask for?"),
              *tool("Read", {"file_path": f"{wiki}/entities/customer-a.md"}, 1),
              *tool("Agent", {"description": "fact-check", "run_in_background": True}, 2),
              answer("waiting for the check"),
              prompt("<task-notification>\n<task-id>a1</task-id>\n</task-notification>"),
              answer()]
    assert blocked(run(tmp_path, events))


def test_bad_input_is_silent(tmp_path):
    out = subprocess.run(["python3", str(HOOK)], input="not json", capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout == ""
