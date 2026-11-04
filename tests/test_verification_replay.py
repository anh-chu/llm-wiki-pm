"""verification-replay/run.py: the evidence check reads outside calls and their results.

Run: python3 -m pytest tests/test_verification_replay.py -v
"""

import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "replay", Path(__file__).resolve().parent / "verification-replay" / "run.py")
replay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(replay)


def call(i, name, args, result):
    return [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": f"t{i}", "name": name, "input": args}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result", "tool_use_id": f"t{i}", "content": result}]}},
    ]


EVENTS = (call(1, "Bash", {"command": "gh search prs Xray --merged"}, "test-management#4488 merged")
          + call(2, "Bash", {"command": "grep -rn 4511 entities/"}, "test-management#4511")
          + call(3, "mcp__plugin_llm-wiki-pm_wiki-search__search_text", {"query": "4511"}, "4511")
          + [{"type": "result", "result": "Yes", "total_cost_usd": 0.1}])


def external():
    return [(n, x, r) for n, x, r in replay.tool_calls(EVENTS) if replay.is_external(n, x)]


def test_results_are_matched_to_calls():
    assert [r for _, _, r in replay.tool_calls(EVENTS)] == [
        "test-management#4488 merged", "test-management#4511", "4511"]


def test_wiki_reads_are_not_outside_checks():
    assert [json.loads(x).get("command") for _, x, _ in external()] == ["gh search prs Xray --merged"]


def test_record_in_result_counts_as_evidence(monkeypatch):
    monkeypatch.setattr(replay, "vote", lambda case, answer, n: {"correct": True, "deferred": False, "why": ""})
    hit = lambda rx: replay.grade({"evidence": [rx]}, EVENTS, 1)["evidence"]
    assert hit("4488")      # came back in the gh search result
    assert not hit("4511")  # only seen through grep and wiki-search over the wiki copy
