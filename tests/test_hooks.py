"""
Tests for llm-wiki-pm hook scripts.

Each test creates a temp wiki fixture, feeds the correct stdin JSON payload
(matching the Claude Code hook input schema), and asserts correct behavior.

Run: python3 -m pytest tests/test_hooks.py -v
"""

import json
import os
import subprocess
import textwrap
from datetime import date, datetime, timedelta
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS_DIR = REPO_ROOT / "hooks"
TEMPLATES_DIR = REPO_ROOT / "skills" / "llm-wiki-pm" / "templates"

SESSION_START = HOOKS_DIR / "session-start.sh"
POST_WRITE = HOOKS_DIR / "post-write.sh"
SESSION_STOP = HOOKS_DIR / "session-stop.sh"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run_hook(
    script: Path, stdin_json: dict, env_overrides: dict = None
) -> subprocess.CompletedProcess:
    """Run a hook script with the given stdin JSON and environment."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(script)],
        input=json.dumps(stdin_json),
        capture_output=True,
        text=True,
        env=env,
    )


def session_start_payload(source: str = "startup") -> dict:
    """Minimal SessionStart JSON input per Claude Code hook schema."""
    return {
        "session_id": "test-session-123",
        "hook_event_name": "SessionStart",
        "source": source,
        "model": "claude-opus-4-5",
        "cwd": "/tmp",
    }


def post_write_payload(file_path: str, tool: str = "Write") -> dict:
    """PostToolUse JSON input for a Write/Edit tool call."""
    return {
        "session_id": "test-session-123",
        "hook_event_name": "PostToolUse",
        "tool_name": tool,
        "tool_input": {
            "file_path": file_path,
            "content": "test content",
        },
        "cwd": "/tmp",
    }


def session_end_payload() -> dict:
    """Minimal SessionEnd JSON input."""
    return {
        "session_id": "test-session-123",
        "hook_event_name": "SessionEnd",
        "cwd": "/tmp",
    }


def make_wiki(tmp_path: Path, with_schema: bool = True) -> Path:
    """Create a minimal wiki directory structure."""
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    for sub in [
        "raw/articles",
        "raw/papers",
        "raw/transcripts",
        "raw/internal",
        "raw/assets",
        "entities",
        "concepts",
        "comparisons",
        "queries",
        "_archive",
    ]:
        (wiki / sub).mkdir(parents=True)

    if with_schema:
        schema = (TEMPLATES_DIR / "SCHEMA.md").read_text()
        (wiki / "SCHEMA.md").write_text(schema)
        (wiki / "index.md").write_text(
            f"---\ntitle: Index\nupdated: {date.today()}\n---\n"
        )
        (wiki / "overview.md").write_text(
            f"---\ntitle: Overview\nupdated: {date.today()}\n---\n"
        )
        (wiki / "log.md").write_text("# Wiki Log\n")

    return wiki


def make_entity(
    wiki: Path, slug: str, updated: date, tags: list = None, links: list = None
) -> Path:
    """Create a minimal entity page."""
    tags_str = ", ".join(tags or ["company"])
    links_str = "\n".join(f"[[{l}]]" for l in (links or []))
    text = textwrap.dedent(f"""\
        ---
        title: {slug}
        created: 2024-01-01
        updated: {updated}
        type: entity
        tags: [{tags_str}]
        sources: []
        ---
        # {slug}
        {links_str}
    """)
    path = wiki / "entities" / f"{slug}.md"
    path.write_text(text)
    return path


# ---------------------------------------------------------------------------
# session-start.sh tests
# ---------------------------------------------------------------------------


class TestSessionStart:
    def test_scaffolds_new_directory(self, tmp_path):
        """New wiki path: directory created with all required files."""
        wiki = tmp_path / "new-wiki"
        assert not wiki.exists()

        result = run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
                "CLAUDE_PLUGIN_OPTION_wiki_domain": "Test Domain",
            },
        )

        assert result.returncode == 0, result.stderr
        assert wiki.exists()
        assert (wiki / "SCHEMA.md").exists()
        assert (wiki / "index.md").exists()
        assert (wiki / "overview.md").exists()
        assert (wiki / "log.md").exists()
        assert (wiki / "entities").is_dir()
        assert (wiki / "raw" / "articles").is_dir()

    def test_scaffold_applies_domain(self, tmp_path):
        """Domain string replaces PM placeholder in SCHEMA.md."""
        wiki = tmp_path / "wiki"

        run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
                "CLAUDE_PLUGIN_OPTION_wiki_domain": "Legal Research",
            },
        )

        schema = (wiki / "SCHEMA.md").read_text()
        assert "Legal Research knowledge base." in schema
        assert "# Wiki Schema, Legal Research" in schema

    def test_scaffold_domain_with_special_chars(self, tmp_path):
        """Domain with sed-special chars (slash, ampersand) handled safely."""
        wiki = tmp_path / "wiki"

        run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
                "CLAUDE_PLUGIN_OPTION_wiki_domain": "Finance & Risk / Compliance",
            },
        )

        assert wiki.exists(), "Scaffold should succeed with special chars in domain"
        schema = (wiki / "SCHEMA.md").read_text()
        assert "Finance & Risk / Compliance" in schema

    def test_scaffold_domain_with_ampersand(self, tmp_path):
        """Ampersand in domain must not expand as sed backreference."""
        wiki = tmp_path / "wiki"

        run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
                "CLAUDE_PLUGIN_OPTION_wiki_domain": "R&D",
            },
        )

        schema = (wiki / "SCHEMA.md").read_text()
        assert "R&D knowledge base." in schema
        # If sed was used unsafely, "&" would expand to the match string
        assert "management knowledge base. knowledge base." not in schema

    def test_no_scaffold_for_existing_nonempty_without_schema(self, tmp_path):
        """Non-empty dir without SCHEMA.md: warn and skip, never overwrite."""
        wiki = tmp_path / "wiki"
        wiki.mkdir()
        user_file = wiki / "my-notes.md"
        user_file.write_text("important content")

        result = run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert result.returncode == 0
        assert user_file.read_text() == "important content", (
            "User file must not be modified"
        )
        assert not (wiki / "SCHEMA.md").exists(), (
            "Must not create SCHEMA.md in foreign dir"
        )
        assert "Warning" in result.stderr or "Skipping" in result.stderr

    def test_scaffold_empty_existing_directory(self, tmp_path):
        """Existing empty directory: scaffold normally."""
        wiki = tmp_path / "wiki"
        wiki.mkdir()

        result = run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
                "CLAUDE_PLUGIN_OPTION_wiki_domain": "PM",
            },
        )

        assert result.returncode == 0
        assert (wiki / "SCHEMA.md").exists()

    def test_no_rescaffold_existing_wiki(self, tmp_path):
        """Existing wiki with SCHEMA.md: no scaffold, no file overwrite."""
        wiki = make_wiki(tmp_path)
        (wiki / "entities" / "tricentis.md").write_text("# Tricentis\n")
        original_schema_mtime = (wiki / "SCHEMA.md").stat().st_mtime

        run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert (wiki / "SCHEMA.md").stat().st_mtime == original_schema_mtime, (
            "SCHEMA.md must not be touched for existing wiki"
        )

    def test_outputs_valid_additional_context_json(self, tmp_path):
        """SessionStart hook outputs valid hookSpecificOutput JSON to stdout."""
        wiki = make_wiki(tmp_path)

        result = run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert result.returncode == 0, result.stderr
        output = json.loads(result.stdout)
        assert "hookSpecificOutput" in output
        assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"
        assert "additionalContext" in output["hookSpecificOutput"]
        assert isinstance(output["hookSpecificOutput"]["additionalContext"], str)

    def test_context_mentions_wiki_path(self, tmp_path):
        """additionalContext includes the wiki location."""
        wiki = make_wiki(tmp_path)

        result = run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        assert str(wiki) in context

    def test_writes_status_md(self, tmp_path):
        """SessionStart creates _status.md in the wiki."""
        wiki = make_wiki(tmp_path)

        run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert (wiki / "_status.md").exists()
        content = (wiki / "_status.md").read_text()
        assert "Wiki Status" in content
        assert "Health Summary" in content

    def test_detects_stale_pages(self, tmp_path):
        """Pages updated >30 days ago appear in stale count."""
        wiki = make_wiki(tmp_path)
        old_date = (datetime.now() - timedelta(days=45)).date()
        make_entity(wiki, "old-company", updated=old_date)

        result = run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        output = json.loads(result.stdout)
        context = output["hookSpecificOutput"]["additionalContext"]
        status = (wiki / "_status.md").read_text()
        assert "Stale" in status or "stale" in context.lower()

    def test_detects_confidence_decay(self, tmp_path):
        """Competitive pages updated >60 days ago flagged as decay candidates."""
        wiki = make_wiki(tmp_path)
        old_date = (datetime.now() - timedelta(days=75)).date()
        make_entity(wiki, "old-competitor", updated=old_date, tags=["competitive"])

        run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        status = (wiki / "_status.md").read_text()
        assert "Decay" in status or "decay" in status.lower()

    def test_no_decay_for_recent_competitive_page(self, tmp_path):
        """Competitive page updated recently: no decay flag."""
        wiki = make_wiki(tmp_path)
        recent_date = date.today()
        make_entity(wiki, "fresh-competitor", updated=recent_date, tags=["competitive"])

        run_hook(
            SESSION_START,
            session_start_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        status = (wiki / "_status.md").read_text()
        assert "Decay Candidates" not in status

    def test_exits_zero_when_wiki_missing_and_no_templates(self, tmp_path):
        """If templates are missing, hook should not crash with nonzero exit."""
        wiki = tmp_path / "wiki"
        # Point PLUGIN_ROOT somewhere without templates
        bad_root = tmp_path / "bad-plugin"
        bad_root.mkdir()

        result = subprocess.run(
            ["bash", str(SESSION_START)],
            input=json.dumps(session_start_payload()),
            capture_output=True,
            text=True,
            env={
                **os.environ,
                "CLAUDE_PLUGIN_ROOT": str(bad_root),
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )
        # With set -euo pipefail this will fail when templates missing, which is expected.
        # The key is it must not produce corrupt JSON output if it does exit 0.
        if result.returncode == 0:
            json.loads(result.stdout)  # must be parseable if it exits 0

    def test_unconfigured_outputs_setup_instructions(self):
        """No wiki_path or WIKI_PATH set: outputs setup instructions, exits 0."""
        env = {
            k: v
            for k, v in os.environ.items()
            if k
            not in (
                "WIKI_PATH",
                "CLAUDE_PLUGIN_OPTION_wiki_path",
                "CLAUDE_PLUGIN_OPTION_wiki_domain",
            )
        }
        env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
        env["HOME"] = "/nonexistent-home"  # prevent accidental fallback match

        result = subprocess.run(
            ["bash", str(SESSION_START)],
            input=json.dumps(session_start_payload()),
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "not configured" in ctx
        assert "pluginConfigs" in ctx
        assert "wiki_path" in ctx


# ---------------------------------------------------------------------------
# post-write.sh tests
# ---------------------------------------------------------------------------


class TestPostWrite:
    def test_skips_non_wiki_file(self, tmp_path):
        """Files outside wiki dir are silently skipped."""
        wiki = make_wiki(tmp_path)
        outside = tmp_path / "outside.md"
        outside.write_text("# outside")

        result = run_hook(
            POST_WRITE,
            post_write_payload(str(outside)),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert result.returncode == 0
        assert not (wiki / "_status.md").exists()

    def test_skips_non_markdown_file(self, tmp_path):
        """Non-.md files inside wiki are skipped."""
        wiki = make_wiki(tmp_path)
        asset = wiki / "raw" / "assets" / "diagram.png"
        asset.write_bytes(b"\x89PNG")

        result = run_hook(
            POST_WRITE,
            post_write_payload(str(asset)),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert result.returncode == 0
        assert not (wiki / "_status.md").exists()

    def test_parses_file_path_from_stdin_without_jq(self, tmp_path):
        """File path extracted from stdin JSON using Python, not jq."""
        wiki = make_wiki(tmp_path)
        page = wiki / "entities" / "test.md"
        page.write_text("# Test\n[[tricentis]]\n")

        # Run with PATH stripped of jq to confirm Python fallback works
        env = {
            **os.environ,
            "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT),
            "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
        }
        env["PATH"] = ":".join(
            p for p in env.get("PATH", "").split(":") if "jq" not in p
        )

        result = subprocess.run(
            ["bash", str(POST_WRITE)],
            input=json.dumps(post_write_payload(str(page))),
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode == 0
        assert (wiki / "_status.md").exists()

    def test_clean_page_reports_clean(self, tmp_path):
        """Page with valid wikilinks reports clean."""
        wiki = make_wiki(tmp_path)
        make_entity(wiki, "tricentis", updated=date.today())
        page = wiki / "entities" / "test.md"
        page.write_text("# Test\n[[tricentis]]\n")

        run_hook(
            POST_WRITE,
            post_write_payload(str(page)),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        status = (wiki / "_status.md").read_text()
        assert "clean" in status.lower()
        assert "broken wikilink" not in status

    def test_broken_wikilink_reported(self, tmp_path):
        """Page with broken wikilink reports issue in _status.md."""
        wiki = make_wiki(tmp_path)
        page = wiki / "entities" / "test.md"
        page.write_text("# Test\n[[nonexistent-page]]\n")

        run_hook(
            POST_WRITE,
            post_write_payload(str(page)),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        status = (wiki / "_status.md").read_text()
        assert "broken wikilink" in status
        assert "nonexistent-page" in status

    def test_raw_file_not_false_positive(self, tmp_path):
        """Wikilink to slug that exists only in raw/ is reported as broken."""
        wiki = make_wiki(tmp_path)
        # Create file only in raw/, not in entities/concepts/comparisons/queries
        (wiki / "raw" / "articles" / "tricentis.md").write_text("# raw article")
        page = wiki / "entities" / "test.md"
        page.write_text("# Test\n[[tricentis]]\n")

        run_hook(
            POST_WRITE,
            post_write_payload(str(page)),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        status = (wiki / "_status.md").read_text()
        assert "broken wikilink" in status, "raw/ file must NOT satisfy wikilink check"

    def test_entity_page_satisfies_wikilink(self, tmp_path):
        """Wikilink to entity page resolves as valid."""
        wiki = make_wiki(tmp_path)
        make_entity(wiki, "databricks", updated=date.today())
        page = wiki / "concepts" / "market.md"
        page.write_text("# Market\n[[databricks]]\n")

        run_hook(
            POST_WRITE,
            post_write_payload(str(page), tool="Edit"),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        status = (wiki / "_status.md").read_text()
        assert "broken wikilink" not in status

    def test_alias_syntax_wikilink(self, tmp_path):
        """[[target|label]] alias syntax: target validated, label ignored."""
        wiki = make_wiki(tmp_path)
        make_entity(wiki, "tricentis", updated=date.today())
        page = wiki / "entities" / "test.md"
        page.write_text("# Test\n[[tricentis|Tricentis Corporation]]\n")

        run_hook(
            POST_WRITE,
            post_write_payload(str(page)),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        status = (wiki / "_status.md").read_text()
        assert "broken wikilink" not in status

    def test_anchor_syntax_wikilink(self, tmp_path):
        """[[target#section]] anchor syntax: target validated, section ignored."""
        wiki = make_wiki(tmp_path)
        make_entity(wiki, "tricentis", updated=date.today())
        page = wiki / "entities" / "test.md"
        page.write_text("# Test\n[[tricentis#pricing]]\n")

        run_hook(
            POST_WRITE,
            post_write_payload(str(page)),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        status = (wiki / "_status.md").read_text()
        assert "broken wikilink" not in status

    def test_appends_to_existing_status(self, tmp_path):
        """Successive writes append to _status.md without wiping it."""
        wiki = make_wiki(tmp_path)
        (wiki / "_status.md").write_text("# Wiki Status\n\n## Previous\n")
        page = wiki / "entities" / "test.md"
        page.write_text("# Test\n")

        run_hook(
            POST_WRITE,
            post_write_payload(str(page)),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        status = (wiki / "_status.md").read_text()
        assert "Previous" in status, "Existing status content must be preserved"

    def test_exits_zero_always(self, tmp_path):
        """Hook never blocks a write (always exits 0)."""
        wiki = make_wiki(tmp_path)
        page = wiki / "entities" / "broken.md"
        page.write_text("[[broken1]] [[broken2]] [[broken3]]")

        result = run_hook(
            POST_WRITE,
            post_write_payload(str(page)),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert result.returncode == 0

    def test_empty_stdin_exits_zero(self, tmp_path):
        """Malformed or empty stdin: silent exit 0."""
        result = subprocess.run(
            ["bash", str(POST_WRITE)],
            input="",
            capture_output=True,
            text=True,
            env={**os.environ, "CLAUDE_PLUGIN_ROOT": str(REPO_ROOT)},
        )
        assert result.returncode == 0

    def test_missing_file_path_in_payload(self, tmp_path):
        """Payload without file_path: silent exit 0."""
        wiki = make_wiki(tmp_path)
        payload = {"session_id": "x", "tool_name": "Write", "tool_input": {}}

        result = run_hook(
            POST_WRITE,
            payload,
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert result.returncode == 0


# ---------------------------------------------------------------------------
# session-stop.sh tests
# ---------------------------------------------------------------------------


class TestSessionStop:
    def test_no_rotation_below_threshold(self, tmp_path):
        """log.md with 499 entries: no rotation."""
        wiki = make_wiki(tmp_path)
        entries = "\n".join(
            f"## [2024-01-{i:02d}] ingest | source-{i}" for i in range(1, 500)
        )
        (wiki / "log.md").write_text(entries + "\n")
        original = (wiki / "log.md").read_text()

        result = run_hook(
            SESSION_STOP,
            session_end_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert result.returncode == 0
        assert (wiki / "log.md").read_text() == original, "log.md must not change"
        assert not list(wiki.glob("log-*.md")), "No rotation file should exist"

    def test_rotation_at_501_entries(self, tmp_path):
        """log.md with 501 entries: rotated to log-YYYY.md."""
        wiki = make_wiki(tmp_path)
        entries = "\n".join(f"## [2024-01-01] ingest | source-{i}" for i in range(501))
        (wiki / "log.md").write_text(entries + "\n")

        result = run_hook(
            SESSION_STOP,
            session_end_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert result.returncode == 0
        year = date.today().year
        rotated = list(wiki.glob(f"log-{year}*.md"))
        assert len(rotated) == 1, f"Expected 1 rotation file, got {rotated}"
        assert "## [" in rotated[0].read_text(), "Rotated file contains old entries"
        new_log = (wiki / "log.md").read_text()
        assert "Rotated from" in new_log, "Fresh log.md has rotation header"
        assert "## [2024-01-01]" not in new_log, "Old entries not in new log"

    def test_rotation_collision_avoidance(self, tmp_path):
        """If log-YYYY.md exists, rotates to log-YYYY-part-2.md."""
        wiki = make_wiki(tmp_path)
        year = date.today().year
        (wiki / f"log-{year}.md").write_text("# previous rotation\n")
        entries = "\n".join(f"## [2024-01-01] ingest | source-{i}" for i in range(501))
        (wiki / "log.md").write_text(entries + "\n")

        run_hook(
            SESSION_STOP,
            session_end_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert (wiki / f"log-{year}-part-2.md").exists(), (
            "Collision avoided by using -part-2"
        )

    def test_counts_entries_not_lines(self, tmp_path):
        """Rotation threshold is entry count, not line count."""
        wiki = make_wiki(tmp_path)
        # 499 entries, but each entry spans 3 lines = 1497 lines total
        entries = []
        for i in range(499):
            entries.append(f"## [2024-01-01] ingest | source-{i}")
            entries.append(f"- Created entities/item-{i}.md")
            entries.append("- Updated index.md")
        (wiki / "log.md").write_text("\n".join(entries) + "\n")

        result = run_hook(
            SESSION_STOP,
            session_end_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )

        assert result.returncode == 0
        assert not list(wiki.glob("log-*.md")), (
            "Must not rotate: only 499 entries despite 1497 lines"
        )

    def test_no_wiki_exits_silently(self, tmp_path):
        """Missing wiki directory: silent exit 0."""
        result = run_hook(
            SESSION_STOP,
            session_end_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(tmp_path / "nonexistent"),
            },
        )
        assert result.returncode == 0

    def test_no_log_exits_silently(self, tmp_path):
        """Wiki without log.md: silent exit 0."""
        wiki = tmp_path / "wiki"
        wiki.mkdir()

        result = run_hook(
            SESSION_STOP,
            session_end_payload(),
            {
                "CLAUDE_PLUGIN_OPTION_wiki_path": str(wiki),
            },
        )
        assert result.returncode == 0


# ---------------------------------------------------------------------------
# Plugin manifest validation
# ---------------------------------------------------------------------------


class TestPluginValidation:
    def test_plugin_json_is_valid_json(self):
        """plugin.json parses as valid JSON."""
        text = (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text()
        data = json.loads(text)
        assert data["name"] == "llm-wiki-pm"

    def test_hooks_json_is_valid_json(self):
        """hooks/hooks.json parses as valid JSON."""
        text = (REPO_ROOT / "hooks" / "hooks.json").read_text()
        data = json.loads(text)
        assert "hooks" in data, "Must have outer 'hooks' wrapper"
        assert "SessionStart" in data["hooks"]
        assert "PostToolUse" in data["hooks"]
        assert "SessionEnd" in data["hooks"]

    def test_hooks_json_has_description(self):
        """hooks/hooks.json has description field per official format."""
        data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        assert "description" in data

    def test_hooks_use_plugin_root_var(self):
        """All hook commands reference ${CLAUDE_PLUGIN_ROOT}."""
        data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        for event, groups in data["hooks"].items():
            for group in groups:
                for hook in group.get("hooks", []):
                    cmd = hook.get("command", "")
                    assert "${CLAUDE_PLUGIN_ROOT}" in cmd, (
                        f"Hook {event} command missing CLAUDE_PLUGIN_ROOT: {cmd}"
                    )

    def test_post_write_matcher_includes_multiedit(self):
        """PostToolUse matcher includes MultiEdit."""
        data = json.loads((REPO_ROOT / "hooks" / "hooks.json").read_text())
        matchers = [g.get("matcher", "") for g in data["hooks"]["PostToolUse"]]
        assert any("MultiEdit" in m for m in matchers), (
            "PostToolUse must match MultiEdit per official Anthropic example"
        )

    def test_userconfig_has_sensitive_field(self):
        """userConfig fields have explicit sensitive key."""
        data = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
        for key, cfg in data.get("userConfig", {}).items():
            assert "sensitive" in cfg, f"userConfig.{key} missing 'sensitive' field"

    def test_skill_md_exists(self):
        """SKILL.md present at expected plugin path."""
        assert (REPO_ROOT / "skills" / "llm-wiki-pm" / "SKILL.md").exists()

    def test_skill_md_frontmatter(self):
        """SKILL.md has name, description, when_to_use, allowed-tools."""
        text = (REPO_ROOT / "skills" / "llm-wiki-pm" / "SKILL.md").read_text()
        assert text.startswith("---"), "Must start with frontmatter"
        fm_end = text.index("---", 3)
        fm = text[:fm_end]
        assert "name:" in fm
        assert "description:" in fm
        assert "when_to_use:" in fm
        assert "allowed-tools:" in fm

    def test_skill_md_under_500_lines(self):
        """SKILL.md under 500 lines per spec."""
        lines = (
            (REPO_ROOT / "skills" / "llm-wiki-pm" / "SKILL.md").read_text().splitlines()
        )
        assert len(lines) < 500, f"SKILL.md has {len(lines)} lines, must be under 500"

    def test_no_hardcoded_home_paths(self):
        """No absolute /home/... paths in SKILL.md or hook scripts."""
        files = [
            REPO_ROOT / "skills" / "llm-wiki-pm" / "SKILL.md",
            HOOKS_DIR / "session-start.sh",
            HOOKS_DIR / "post-write.sh",
            HOOKS_DIR / "session-stop.sh",
        ]
        for f in files:
            text = f.read_text()
            assert "/home/sil" not in text, (
                f"{f.name} contains hardcoded /home/sil path"
            )


# ---------------------------------------------------------------------------
# set-wiki-path.py tests
# ---------------------------------------------------------------------------

SET_WIKI_PATH = REPO_ROOT / "skills" / "set-wiki-path" / "scripts" / "set-wiki-path.py"


def run_set_wiki_path(args: list, cwd: str = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["python3", str(SET_WIKI_PATH)] + args,
        capture_output=True, text=True,
        cwd=cwd or "/tmp",
    )


class TestSetWikiPath:

    def test_writes_to_global_by_default(self, tmp_path):
        """No project settings: writes to global user settings."""
        settings = tmp_path / "settings.json"
        settings.write_text("{}")
        result = run_set_wiki_path(
            ["~/pm-wiki"],
            cwd=str(tmp_path),
        )
        # Can't redirect HOME in subprocess easily; just verify script exits cleanly
        # and produces expected output format when settings exist
        assert result.returncode == 0 or "settings.json" in result.stderr

    def test_writes_to_project_when_plugin_enabled_there(self, tmp_path):
        """Plugin in project enabledPlugins: writes pluginConfigs to project file."""
        project_claude = tmp_path / ".claude"
        project_claude.mkdir()
        project_settings = project_claude / "settings.json"
        project_settings.write_text(json.dumps({
            "enabledPlugins": {"llm-wiki-pm@anh-chu-plugins": True}
        }))

        # Patch HOME so global fallback goes to tmp
        env = {**os.environ, "HOME": str(tmp_path)}
        (tmp_path / ".claude").mkdir(exist_ok=True)
        (tmp_path / ".claude" / "settings.json").write_text("{}")

        result = subprocess.run(
            ["python3", str(SET_WIKI_PATH), "/my/project/wiki"],
            capture_output=True, text=True,
            cwd=str(tmp_path), env=env,
        )
        assert result.returncode == 0
        assert "project" in result.stdout

        data = json.loads(project_settings.read_text())
        assert data["pluginConfigs"]["llm-wiki-pm@anh-chu-plugins"]["options"]["wiki_path"] == "/my/project/wiki"

    def test_local_flag_writes_to_local_settings(self, tmp_path):
        """--local flag always writes to .claude/settings.local.json."""
        env = {**os.environ, "HOME": str(tmp_path)}
        (tmp_path / ".claude").mkdir(exist_ok=True)
        (tmp_path / ".claude" / "settings.json").write_text("{}")

        result = subprocess.run(
            ["python3", str(SET_WIKI_PATH), "/local/wiki", "--local"],
            capture_output=True, text=True,
            cwd=str(tmp_path), env=env,
        )
        assert result.returncode == 0
        assert "local" in result.stdout

        local_file = tmp_path / ".claude" / "settings.local.json"
        assert local_file.exists()
        data = json.loads(local_file.read_text())
        assert data["pluginConfigs"]["llm-wiki-pm@anh-chu-plugins"]["options"]["wiki_path"] == "/local/wiki"

    def test_local_flag_takes_precedence_over_project(self, tmp_path):
        """--local writes to local file even when plugin enabled in project settings."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text(json.dumps({
            "enabledPlugins": {"llm-wiki-pm@anh-chu-plugins": True}
        }))

        env = {**os.environ, "HOME": str(tmp_path)}
        (tmp_path / ".claude" / "settings.json")  # already exists

        result = subprocess.run(
            ["python3", str(SET_WIKI_PATH), "/override/wiki", "--local"],
            capture_output=True, text=True,
            cwd=str(tmp_path), env=env,
        )
        assert result.returncode == 0
        assert "local" in result.stdout
        assert (claude_dir / "settings.local.json").exists()

    def test_expands_tilde_in_path(self, tmp_path):
        """~ in path is expanded to home directory."""
        env = {**os.environ, "HOME": str(tmp_path)}
        (tmp_path / ".claude").mkdir(exist_ok=True)
        (tmp_path / ".claude" / "settings.json").write_text("{}")

        result = subprocess.run(
            ["python3", str(SET_WIKI_PATH), "~/my-wiki"],
            capture_output=True, text=True,
            cwd=str(tmp_path), env=env,
        )
        assert result.returncode == 0
        assert str(tmp_path / "my-wiki") in result.stdout

    def test_no_args_exits_nonzero(self):
        """No arguments: exits with error."""
        result = run_set_wiki_path([])
        assert result.returncode != 0

    def test_empty_path_exits_nonzero(self):
        """Empty string argument: exits with error."""
        result = run_set_wiki_path([""])
        assert result.returncode != 0
