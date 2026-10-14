"""Wiki path resolution: hooks, the wiki-search launcher and the skill snippet
must never treat an arbitrary working directory as the wiki."""

import json
import os
import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOKS = REPO_ROOT / "hooks"
OPTION_VARS = ("WIKI_PATH", "CLAUDE_PLUGIN_OPTION_WIKI_PATH", "CLAUDE_PLUGIN_OPTION_wiki_path",
               "CLAUDE_PLUGIN_OPTION_WIKI_DOMAIN", "CLAUDE_PLUGIN_OPTION_wiki_domain", "WIKI_CONFIGURED_PATH")


def clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in OPTION_VARS}
    env["CLAUDE_PLUGIN_ROOT"] = str(REPO_ROOT)
    env.update(extra)
    return env


def resolve(cwd, *args, **env):
    out = subprocess.run(["sh", str(HOOKS / "resolve-wiki.sh"), *args], cwd=cwd,
                         capture_output=True, text=True, env=clean_env(**env))
    return out.stdout.strip()


def code_dir(tmp_path):
    d = tmp_path / "project"
    d.mkdir()
    (d / "app.py").write_text("print(1)\n")
    return d


class TestResolver:
    def test_plain_project_is_not_a_wiki(self, tmp_path):
        assert resolve(code_dir(tmp_path)) == ""

    def test_empty_dir_is_not_a_wiki(self, tmp_path):
        assert resolve(tmp_path) == ""

    def test_cwd_used_when_it_has_schema(self, tmp_path):
        (tmp_path / "SCHEMA.md").write_text("# Schema\n")
        assert resolve(tmp_path) == str(tmp_path)

    def test_option_uppercase(self, tmp_path):
        assert resolve(code_dir(tmp_path), CLAUDE_PLUGIN_OPTION_WIKI_PATH="/w") == "/w"

    def test_option_lowercase_still_read(self, tmp_path):
        assert resolve(code_dir(tmp_path), CLAUDE_PLUGIN_OPTION_wiki_path="/w") == "/w"

    def test_argument_used_by_launcher(self, tmp_path):
        assert resolve(code_dir(tmp_path), "/w") == "/w"

    def test_unsubstituted_option_ignored(self, tmp_path):
        assert resolve(code_dir(tmp_path), "${user_config.wiki_path}") == ""

    def test_wiki_path_file_wins(self, tmp_path):
        d = code_dir(tmp_path)
        (d / ".wiki-path").write_text("/from-file\n")
        assert resolve(d, "/w", WIKI_PATH="/env") == "/from-file"

    def test_option_beats_env_and_schema(self, tmp_path):
        (tmp_path / "SCHEMA.md").write_text("# Schema\n")
        assert resolve(tmp_path, CLAUDE_PLUGIN_OPTION_WIKI_PATH="/w", WIKI_PATH="/env") == "/w"


def session_start(cwd, **env):
    return subprocess.run(["bash", str(HOOKS / "session-start.sh")], cwd=cwd, capture_output=True, text=True,
                          input=json.dumps({"session_id": "t", "hook_event_name": "SessionStart", "source": "startup"}),
                          env=clean_env(**env))


class TestSessionStartUnconfigured:
    def test_project_dir_gets_no_files(self, tmp_path):
        d = code_dir(tmp_path)
        result = session_start(d)
        assert result.returncode == 0
        assert sorted(p.name for p in d.iterdir()) == ["app.py"]
        assert "set-wiki-path" in json.loads(result.stdout)["systemMessage"]

    def test_empty_dir_is_not_scaffolded(self, tmp_path):
        session_start(tmp_path)
        assert list(tmp_path.iterdir()) == []

    def test_configured_path_scaffolded_not_cwd(self, tmp_path):
        d = code_dir(tmp_path)
        wiki = tmp_path / "wiki"
        session_start(d, CLAUDE_PLUGIN_OPTION_WIKI_PATH=str(wiki), CLAUDE_PLUGIN_OPTION_WIKI_DOMAIN="Legal")
        assert sorted(p.name for p in d.iterdir()) == ["app.py"]
        assert "Legal" in (wiki / "SCHEMA.md").read_text()


def test_session_stop_leaves_project_alone(tmp_path):
    d = code_dir(tmp_path)
    subprocess.run(["bash", str(HOOKS / "session-stop.sh")], cwd=d, input="{}", capture_output=True, text=True,
                   env=clean_env())
    assert sorted(p.name for p in d.iterdir()) == ["app.py"]


def test_launcher_refuses_without_wiki(tmp_path):
    d = code_dir(tmp_path)
    result = subprocess.run(["sh", str(HOOKS / "wiki-search.sh")], cwd=d, input="", capture_output=True,
                            text=True, timeout=30, env=clean_env(WIKI_CONFIGURED_PATH=""))
    assert result.returncode == 1
    assert "set-wiki-path" in result.stderr
    assert sorted(p.name for p in d.iterdir()) == ["app.py"]  # no .obsidian-mcp/ index left behind


def test_plugin_json_passes_option_to_wiki_search():
    manifest = json.loads((REPO_ROOT / ".claude-plugin" / "plugin.json").read_text())
    env = manifest["mcpServers"]["wiki-search"]["env"]
    assert env == {"WIKI_CONFIGURED_PATH": "${user_config.wiki_path}"}


SNIPPET_FILES = ["AGENTS.md", *[str(p.relative_to(REPO_ROOT)) for p in (REPO_ROOT / "skills").glob("*/SKILL.md")],
                 *[str(p.relative_to(REPO_ROOT)) for p in (REPO_ROOT / ".claude" / "agents").glob("*.md")]]


def test_no_cwd_fallback_left_in_docs():
    for f in SNIPPET_FILES:
        text = (REPO_ROOT / f).read_text()
        assert "${WIKI_PATH:-$(pwd)}" not in text, f
        assert "CLAUDE_PLUGIN_OPTION_wiki_path" not in text, f  # never set in the Bash tool


def run_snippet(cwd, substituted=None):
    """The resolution snippet from AGENTS.md, as Claude Code would hand it to Bash."""
    block = re.search(r"```bash\n(WIKI=.*?)```", (REPO_ROOT / "AGENTS.md").read_text(), re.S).group(1)
    if substituted is not None:
        block = block.replace("${user_config.wiki_path}", substituted)
    return subprocess.run(["bash", "-c", block + 'echo "[$WIKI]"'], cwd=cwd, capture_output=True, text=True,
                          env=clean_env()).stdout.strip()


class TestSnippet:
    def test_unsubstituted_in_project(self, tmp_path):
        assert run_snippet(code_dir(tmp_path)) == "[]"

    def test_substituted(self, tmp_path):
        assert run_snippet(code_dir(tmp_path), "/w") == "[/w]"

    def test_inside_wiki(self, tmp_path):
        (tmp_path / "SCHEMA.md").write_text("# Schema\n")
        assert run_snippet(tmp_path) == f"[{tmp_path}]"
