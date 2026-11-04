#!/usr/bin/env python3
"""Replay past verification failures against a live agent and grade the answers.

Each case is a question the agent once answered wrongly, with the checked truth and
regexes for the external tool calls that count as checking it. The runner asks a
headless `claude -p` the question in a throwaway copy of the wiki (so ingests and
edits cannot touch the real one), with this repo loaded as the plugin. It grades:

  evidence  did a tool call outside the wiki match the case's evidence regex
  correct   does the answer agree with the truth (judged by a small model)

Cases hold private facts, so keep them outside this public repo. See example-cases.json.

Run: python3 tests/verification-replay/run.py --cases ~/private/cases.json --repeat 3 \
       --wiki ~/wiki --out /tmp/replay [--only id1,id2]
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

# Tools that only read the wiki copy; a match in these is recall, not checking.
WIKI_TOOLS = re.compile(r"^(Read|Grep|Glob|Skill|ToolSearch|TodoWrite|Write|Edit|MultiEdit|"
                        r"mcp__plugin_llm-wiki-pm_wiki-search__.*)$")
EXTERNAL_BASH = re.compile(r"\b(gh|gog|curl|wget)\b")

# Anything that posts, sends or changes state outside the sandbox.
DENY = ",".join([
    "mcp__claude_ai_Slack__slack_send_message", "mcp__claude_ai_Slack__slack_send_message_draft",
    "mcp__claude_ai_Slack__slack_schedule_message", "mcp__claude_ai_Slack__slack_add_reaction",
    "mcp__claude_ai_Slack__slack_create_canvas", "mcp__claude_ai_Slack__slack_update_canvas",
    "mcp__claude_ai_Gmail__send_message", "mcp__claude_ai_Gmail__reply",
    "mcp__claude_ai_Gmail__forward", "mcp__claude_ai_Gmail__create_draft",
    "mcp__claude_ai_Atlassian_Rovo__addCommentToJiraIssue", "mcp__claude_ai_Atlassian_Rovo__editJiraIssue",
    "mcp__claude_ai_Atlassian_Rovo__transitionJiraIssue", "mcp__claude_ai_Atlassian_Rovo__createJiraIssue",
    "mcp__claude_ai_Linear__save_issue", "mcp__claude_ai_Linear__save_comment",
    "Bash(gh issue comment:*)", "Bash(gh pr comment:*)", "Bash(gh pr review:*)",
    "Bash(gh issue edit:*)", "Bash(gh pr edit:*)", "Bash(gh issue close:*)", "Bash(gh pr merge:*)",
    "Bash(gh api -X:*)", "Bash(gh api --method:*)", "Bash(git push:*)",
])

JUDGE = """You grade an agent's answer against a checked truth. Reply with JSON only:
{{"correct": true|false, "deferred": true|false, "why": "<one sentence>"}}
correct = the answer's main conclusion agrees with the truth and nothing in it contradicts
the truth. Detail the truth does not mention is NOT a contradiction; ignore it. A hedged
"could not confirm" on the main question is not correct.
deferred = the answer leaves part of what the QUESTION asks unchecked: it answers that part
from notes it says it did not re-check, or offers to check it instead of checking. Notes on
things the question did not ask about ("I didn't check why it closed") are not deferral.

QUESTION: {prompt}
TRUTH: {truth}
ANSWER:
{answer}"""


def sandbox(wiki):
    root = Path(tempfile.mkdtemp(prefix="replay-wiki-"))
    shutil.copytree(wiki, root / "wiki", ignore=shutil.ignore_patterns(".git", "_archive", "external", ".wiki-lock"))
    (root / "wiki" / ".wiki-path").write_text(str(root / "wiki"))
    return root / "wiki"


def run_agent(prompt, cwd, model, timeout, plugin):
    cmd = ["claude", "-p", prompt, "--plugin-dir", plugin, "--output-format", "stream-json",
           "--verbose", "--permission-mode", "bypassPermissions", "--disallowedTools", DENY]
    if model:
        cmd += ["--model", model]
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout,
                       stdin=subprocess.DEVNULL)
    return [json.loads(line) for line in p.stdout.splitlines() if line.startswith("{")]


def tool_calls(events):
    """(name, input JSON, result text) for each tool call, results matched by tool_use_id."""
    results = {}
    for e in events:
        if e.get("type") == "user":
            for c in e.get("message", {}).get("content", []):
                if isinstance(c, dict) and c.get("type") == "tool_result":
                    body = c.get("content")
                    results[c.get("tool_use_id")] = body if isinstance(body, str) else json.dumps(body)
    for e in events:
        if e.get("type") != "assistant":
            continue
        for c in e.get("message", {}).get("content", []):
            if c.get("type") == "tool_use":
                yield c["name"], json.dumps(c.get("input", {}), ensure_ascii=False), results.get(c["id"], "")


def is_external(name, args):
    if WIKI_TOOLS.match(name):
        return False
    if name == "Bash":
        return bool(EXTERNAL_BASH.search(json.loads(args).get("command", "")))
    return True


def judge(case, answer, timeout):
    p = subprocess.run(["claude", "-p", JUDGE.format(answer=answer or "(no answer)", **case),
                        "--model", "sonnet", "--output-format", "json", "--strict-mcp-config"],
                       capture_output=True, text=True, timeout=timeout, cwd=tempfile.gettempdir(),
                       stdin=subprocess.DEVNULL)
    try:
        text = next(o["result"] for o in map(json.loads, reversed(p.stdout.splitlines()))
                    if o.get("type") == "result")
        return json.JSONDecoder().raw_decode(text[text.index("{"):])[0]
    except Exception as exc:  # judge output is not JSON: record it, don't crash the run
        return {"correct": None, "why": f"judge failed: {exc}: {p.stdout[-300:]}"}


def vote(case, answer, n):
    """Majority of n judge calls; one judge call flips on the same answer too often."""
    votes = [judge(case, answer, 300) for _ in range(n)]
    pick = lambda k: sum(bool(v.get(k)) for v in votes) * 2 > n
    return {"correct": pick("correct"), "deferred": pick("deferred"), "why": votes[0].get("why", "")}


def grade(case, events, judges):
    final = next((e for e in reversed(events) if e.get("type") == "result"), {})
    answer = final.get("result", "")
    calls = list(tool_calls(events))
    # Evidence: the outside call asked for the record, or the record came back in its result.
    external = [(n, x, r) for n, x, r in calls if is_external(n, x)]
    hit = any(re.search(rx, f"{n} {x} {r}", re.I) for rx in case["evidence"] for n, x, r in external)
    v = vote(case, answer, judges)
    # Deferring a check the agent could have run is the failure being measured:
    # it costs the user another turn to ask for it.
    passed = hit and v["correct"] and not v["deferred"]
    return {"passed": passed, "evidence": hit, "correct": v["correct"], "deferred": v["deferred"],
            "why": v["why"], "tools": len(calls), "external": len(external),
            "cost": final.get("total_cost_usd", 0), "answer": answer}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", required=True)
    ap.add_argument("--wiki", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    ap.add_argument("--model", default="")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--plugin-dir", default=str(REPO), help="plugin under test (default: this repo)")
    ap.add_argument("--repeat", type=int, default=1, help="agent runs per case")
    ap.add_argument("--judges", type=int, default=3, help="judge calls per answer (majority)")
    ap.add_argument("--jobs", type=int, default=3, help="agent runs in parallel")
    ap.add_argument("--regrade", action="store_true", help="grade saved transcripts in --out again")
    a = ap.parse_args()

    cases = json.loads(Path(a.cases).expanduser().read_text())
    if a.only:
        keep = set(a.only.split(","))
        cases = [c for c in cases if c["id"] in keep]
    out = Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)
    wiki = None if a.regrade else sandbox(Path(a.wiki).expanduser())

    def one(job):
        case, log = job
        if a.regrade:
            events = [json.loads(line) for line in log.read_text().splitlines() if line]
        else:
            try:
                events = run_agent(case["prompt"], wiki, a.model, a.timeout, a.plugin_dir)
            except subprocess.TimeoutExpired:
                events = []
            log.write_text("\n".join(json.dumps(e) for e in events))
        g = grade(case, events, a.judges)
        print(f"{'passed' if g['passed'] else 'failed':6} {log.stem}: evidence={g['evidence']} "
              f"correct={g['correct']} deferred={g['deferred']} | {g['why'][:160]}", flush=True)
        return case["id"], log.stem, g

    if a.regrade:
        jobs = [(c, log) for c in cases for log in sorted(out.glob(f"{c['id']}.*jsonl"))
                if log.stem.split(".")[0] == c["id"]]
    else:
        jobs = [(c, out / f"{c['id']}.r{i}.jsonl") for c in cases for i in range(a.repeat)]
    with ThreadPoolExecutor(a.jobs) as pool:
        graded = list(pool.map(one, jobs))

    results = []
    for c in cases:
        runs = [g for cid, _, g in graded if cid == c["id"]]
        n, ok = len(runs), sum(g["passed"] for g in runs)
        rate = lambda k: sum(bool(g[k]) for g in runs)
        msg = (f"passed {ok}/{n} | evidence {rate('evidence')}/{n}, correct {rate('correct')}/{n}, "
               f"deferred {rate('deferred')}/{n} | cost ${sum(g['cost'] for g in runs) / max(n, 1):.2f}/run")
        results.append({"name": f"{c['kind']}: {c['id']}", "status": "passed" if n and ok * 2 > n else "failed",
                        "message": msg, "runs": runs})
    (out / "results.json").write_text(json.dumps(results, indent=2, ensure_ascii=False))
    if wiki:
        shutil.rmtree(wiki.parent, ignore_errors=True)
    total = sum(len(r["runs"]) for r in results)
    print(f"{sum(g['passed'] for r in results for g in r['runs'])}/{total} runs passed; "
          f"{sum(r['status'] == 'passed' for r in results)}/{len(results)} cases pass by majority; "
          f"{out}/results.json")


if __name__ == "__main__":
    sys.exit(main())
