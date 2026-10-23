"""prompt-recall.py (UserPromptSubmit): feed stdin JSON and a wiki, check stdout.

Run: python3 -m pytest tests/test_prompt_recall.py -v
"""

import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / "hooks" / "prompt-recall.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
WIKI = FIXTURES / "recall-wiki"
OPTION_VARS = ("WIKI_PATH", "CLAUDE_PLUGIN_OPTION_WIKI_PATH", "CLAUDE_PLUGIN_OPTION_wiki_path")


def run(payload, wiki=WIKI, cwd=None, raw=None):
    env = {k: v for k, v in os.environ.items() if k not in OPTION_VARS}
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    if wiki is not None:
        env["CLAUDE_PLUGIN_OPTION_WIKI_PATH"] = str(wiki)
    stdin = raw if raw is not None else json.dumps(payload)
    return subprocess.run(["python3", str(HOOK)], input=stdin, capture_output=True, text=True,
                          env=env, cwd=cwd or str(FIXTURES))


def prompt(text):
    return {"session_id": "s1", "hook_event_name": "UserPromptSubmit", "cwd": "/tmp", "prompt": text}


def pages(out):
    """Page paths from the hook's additionalContext, in order."""
    if not out.stdout.strip():
        return []
    data = json.loads(out.stdout)
    assert data["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    lines = data["hookSpecificOutput"]["additionalContext"].splitlines()[1:]
    return [line[2:].split(" — ")[0] for line in lines]


def context(out):
    return json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]


def assert_silent(out):
    assert out.returncode == 0
    assert out.stdout == ""


class TestMatching:
    def test_name_match_first(self):
        out = run(prompt("what's the status with Globex"))
        assert out.returncode == 0
        assert pages(out)[0] == "entities/globex.md"

    def test_name_match_line_shape(self):
        ctx = context(run(prompt("how is Acme Corp doing")))
        assert ctx.startswith("Wiki pages that may be relevant (read before asking the user for facts):\n")
        assert "- entities/acme-corp.md — Acme Corp (updated 2026-09-30, verified)" in ctx

    def test_title_head_match(self):
        # Title "Data binding — parameterised manual tests": the head before " — " is a name.
        assert pages(run(prompt("any news on data binding for the release?")))[0] == "concepts/data-binding.md"

    def test_title_parenthetical_ignored(self):
        assert pages(run(prompt("Umbrella Health asks")))[0] == "entities/umbrella-health.md"

    def test_ranked_match_above_threshold(self):
        got = pages(run(prompt("what is the Q4 roadmap for data binding and versioning")))
        assert "queries/roadmap-q4-2026.md" in got

    def test_at_most_three_pages_within_600_bytes(self):
        out = run(prompt("compare Acme Corp, Globex, Initech, Umbrella Health, Jane Doe and John Roe"))
        assert len(pages(out)) == 3
        assert len(context(out).encode()) <= 600

    def test_long_titles_still_fit(self, tmp_path):
        wiki = tmp_path / "wiki"
        (wiki / "entities").mkdir(parents=True)
        for name in ("alpha", "bravo", "charlie", "delta"):
            (wiki / "entities" / f"{name}.md").write_text(
                f"---\ntitle: {name.title()} {'x' * 300}\nupdated: 2026-01-01\nconfidence: likely\n---\n\nbody\n")
        out = run(prompt("alpha bravo charlie delta overview"), wiki=wiki)
        assert 1 <= len(pages(out)) <= 3
        assert len(context(out).encode()) <= 600

    def test_malformed_frontmatter_uses_file_name(self):
        assert "- entities/hooli.md — hooli\n" in context(run(prompt("tell me about Hooli and their QA team"))) + "\n"


class TestSilent:
    @pytest.mark.parametrize("text", ["yes", "go ahead", "1", "ok", "push to main please"])
    def test_trivial_prompt(self, text):
        assert_silent(run(prompt(text)))

    def test_slash_command(self):
        assert_silent(run(prompt("/llm-wiki-pm:set-wiki-path Acme Corp Globex")))

    def test_task_notification(self):
        assert_silent(run(prompt("<task-notification>Globex pilot agent finished: Acme Corp</task-notification>")))

    def test_no_relevant_page(self):
        assert_silent(run(prompt("fix the typo in line 3")))

    def test_excluded_dirs_never_returned(self):
        got = pages(run(prompt("Acme Corp call notes and the Acme Corp brief draft")))
        assert got and all(p.split("/")[0] in ("entities", "concepts", "comparisons", "queries") for p in got)

    def test_no_wiki_configured(self, tmp_path):
        assert_silent(run(prompt("how is Acme Corp doing"), wiki=None, cwd=str(tmp_path)))

    def test_wiki_path_missing_on_disk(self, tmp_path):
        assert_silent(run(prompt("how is Acme Corp doing"), wiki=tmp_path / "nope"))

    def test_invalid_stdin(self):
        assert_silent(run(None, raw="not json {"))

    def test_missing_prompt_field(self):
        assert_silent(run({"session_id": "s1", "hook_event_name": "UserPromptSubmit"}))


class TestEval:
    """Synthetic copy of the real-wiki eval: same pass bar as the spec."""

    def test_pass_bar(self):
        cases = [json.loads(l) for l in (FIXTURES / "recall-eval.jsonl").read_text().splitlines() if l.strip()]
        none = [c for c in cases if c["expected"] == "none"]
        match = [c for c in cases if c["expected"] != "none"]
        quiet = sum(not pages(run(prompt(c["prompt"]))) for c in none)
        hits = sum(any(e in pages(run(prompt(c["prompt"])))[:3] for e in c["expected"]) for c in match)
        assert quiet / len(none) >= 0.8
        assert hits / len(match) >= 0.7


class TestSpeed:
    def test_500_pages_under_one_second(self, tmp_path):
        wiki = tmp_path / "wiki"
        words = ("release roadmap customer pilot sync migration onboarding pricing reporting "
                 "versioning binding latency import audit renewal sponsor escalation").split()
        for i in range(500):
            d = wiki / ("entities", "concepts", "comparisons", "queries")[i % 4]
            d.mkdir(parents=True, exist_ok=True)
            body = " ".join(words[(i * 7 + j) % len(words)] + str(j % 50) for j in range(1400))
            (d / f"page-{i}.md").write_text(
                f"---\ntitle: Page {i}\nupdated: 2026-10-01\nconfidence: likely\n---\n\n{body}\n")
        run(prompt("warm the disk cache"), wiki=wiki)
        start = time.monotonic()
        out = run(prompt("what is the roadmap for customer pilot migration and versioning"), wiki=wiki)
        assert out.returncode == 0
        assert time.monotonic() - start < 1.0
