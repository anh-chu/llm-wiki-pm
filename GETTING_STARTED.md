# Getting Started

Two paths depending on who's driving the setup.

- **[Scenario 1](#scenario-1-human-user-with-claude-code)**: You are a human, using Claude Code, want a personal wiki
- **[Scenario 2](#scenario-2-application-orchestrated-scaffold)**: You are a platform/application scaffolding wikis for end-users programmatically

---

## Scenario 1: Human user with Claude Code

You've cloned this repo, you use Claude Code, you want a PM (or other-domain)
knowledge base working in 15 minutes.

### Install path A: Plugin (recommended)

Installs the skill and hooks together. The wiki auto-scaffolds on the first session start.

```bash
claude plugin marketplace add anh-chu/llm-wiki-pm
claude plugin install llm-wiki-pm@anh-chu/llm-wiki-pm
```

Restart Claude Code. You will be prompted for a wiki path and domain. On the first session start, the `SessionStart` hook creates this structure at your chosen path:

```
pm-wiki/
├── SCHEMA.md       # edit this, see step below
├── index.md
├── overview.md
├── log.md
├── raw/{articles,papers,transcripts,internal,assets}/
├── entities/
├── concepts/
├── comparisons/
├── queries/
└── _archive/
```

### Install path B: Skill-only (symlink)

Use this if you want manual control or prefer not to use the Claude Code plugin system.

```bash
git clone <repo-url> ~/llm-wiki-pm
mkdir -p ~/.claude/skills
ln -s ~/llm-wiki-pm/skills/llm-wiki-pm ~/.claude/skills/llm-wiki-pm
```

Restart Claude Code. Run `/skills` to confirm `llm-wiki-pm` appears.

The symlink installs the skill but not the plugin. The `SessionStart` health-check hook and `PostToolUse` link-check hook do not run, and the wiki is not auto-scaffolded. Create the wiki directory and set `WIKI_PATH` yourself:

```bash
mkdir -p ~/pm-wiki
echo 'export WIKI_PATH=$HOME/pm-wiki' >> ~/.bashrc && source ~/.bashrc
```

Then scaffold the wiki by telling Claude: "Set up my wiki at ~/pm-wiki using the llm-wiki-pm skill templates." Alternatively, use the Python scaffold snippet in Scenario 2.

### 2. Customize SCHEMA.md (5 minutes, critical)

Open `~/pm-wiki/SCHEMA.md`. Edit three sections:

1. **Domain**, one paragraph: what this wiki covers, what's out of scope
2. **Tag taxonomy**: add/remove tags for your specific competitors, customers,
   themes. Default is Katalon-PM-tuned; yours will differ.
3. **Page thresholds**: tune later after a dozen ingests; defaults are fine

Skipping this step = generic wiki that doesn't fit your domain.

### 3. Install qmd (strongly recommended upfront)

Your wiki will grow fast with frequent meetings. Grep alone degrades past
~200 pages. Install qmd now:

```bash
# Claude Code plugin (recommended)
claude plugin marketplace add tobi/qmd
claude plugin install qmd@qmd

# CLI for shell use
npm install -g @tobilu/qmd

# Wire your wiki as qmd collections
qmd collection add "$WIKI_PATH"      --name wiki
qmd collection add "$WIKI_PATH/raw"  --name raw
qmd context add qmd://wiki "PM knowledge base, entities, concepts, comparisons, queries"
qmd context add qmd://raw  "Immutable source docs, analyst reports, transcripts"
qmd embed
qmd status   # confirm everything is indexed
```

Optional, auto-reindex on file change (see `references/qmd-search.md` for
systemd setup).

### 4. First ingest

In Claude Code, open a session in any directory. Drop a source:

> Ingest this Gartner Magic Quadrant report for test automation:
> <paste URL or path to a PDF>

Claude will:
- Read SKILL.md, orient on SCHEMA + index + log + overview
- Run qmd to check existing pages
- Surface takeaways, ask what to emphasize
- Save raw source to `raw/articles/`
- Create/update 5-15 wiki pages with cross-references
- Update index.md, log.md, overview.md
- Tell you exactly what files it touched

### 5. First query

> What do we know about Tricentis pricing?

Claude reads overview.md, qmd-queries the wiki, synthesizes with citations,
offers to file the answer as a new page if it's substantial.

### 6. Mobile access (optional, 10 minutes)

If you want to read the wiki on your phone before meetings, use
obsidian-headless. See `references/obsidian-sync.md` for the full systemd
setup. TL;DR:

```bash
npm install -g obsidian-headless
ob login --email <email> --password '<pw>'
ob sync-create-remote --name "PM Wiki"
cd "$WIKI_PATH" && ob sync-setup --vault "<vault-id>"
ob sync --continuous       # or run as systemd service
```

Then install Obsidian on your phone, pair with the synced vault.

### 7. Weekly rhythm (after a few ingests)

- **Daily-ish**: ingest meeting transcripts and articles as they arrive
- **Weekly**: quick `qmd update && qmd embed` if you don't have the watcher
- **Bi-weekly**: `python3 ~/llm-wiki-pm/skills/llm-wiki-pm/scripts/lint.py $WIKI_PATH --auto-fix`
- **Monthly**: skim the overview.md, refresh if synthesis has drifted
- **Quarterly**: review SCHEMA.md tag taxonomy, archive dead pages

### Troubleshooting

- **Skill doesn't activate** → confirm symlink exists, restart Claude Code,
  run `/skills`. Check SKILL.md frontmatter is intact.
- **Claude can't find the wiki** → The skill resolves the wiki path in this order: `CLAUDE_PLUGIN_OPTION_wiki_path` (set at plugin enable time), then `WIKI_PATH`, then a built-in default. If you installed via plugin, check the path you entered when enabling it. For skill-only installs, run `echo $WIKI_PATH` and confirm it is set in the shell that launched Claude Code. Export in your rc file and re-launch.
- **qmd returns nothing** → `qmd status` shows collection health. Run
  `qmd update && qmd embed` if files exist but aren't indexed.
- **Pages multiplying on same entity** → you're skipping orientation.
  Tell Claude explicitly "read SCHEMA, index, log, overview first" at
  session start until it becomes habit.

### You are done

From here the loop is: ingest → query → lint → repeat. The wiki compounds.

---

## Scenario 2: Application-orchestrated scaffold

You are building a platform/application that provisions wikis for end-users
programmatically. The user doesn't trigger scaffolding themselves, your app does.

### Design decisions to make first

**1. Where does the skill live?**

- **Option A, shared install**: one copy per host, symlinked into each user's
  Claude Code config. Simpler, but all users get the same SKILL.md and scripts.
- **Option B, per-user copy**: copy the skill into each user's wiki root or
  a per-user `.claude/skills/` dir. Lets you version-pin per user, customize
  SCHEMA templates per domain.

Most orchestration apps want **Option B** for isolation.

**2. Where does the wiki live?**

- **Per-user local dir**: `/var/lib/yourapp/wikis/<user-id>/`, simplest
- **Per-user object storage sync**: local working copy + S3/R2 backup
- **Database-backed**: don't. Markdown files in a directory is the point.

**3. What domain does each wiki cover?**

Decide whether your app:
- Offers a single domain (all users = PMs → fixed SCHEMA template)
- Offers multiple domains (PM, research, personal) → user picks at provision
- Generates SCHEMA dynamically from an onboarding interview

### Programmatic scaffold
Replicate the scaffold logic from `session-start.sh` directly in your app.
The logic is straightforward: create subdirectories, copy and customize templates.

#### Python (direct, no subprocess)

```python
import shutil
from datetime import date
from pathlib import Path

SKILL_ROOT = Path("/opt/yourapp/llm-wiki-pm/skills/llm-wiki-pm")
TEMPLATES = SKILL_ROOT / "templates"

SUBDIRS = [
    "raw/articles", "raw/papers", "raw/transcripts",
    "raw/internal", "raw/assets",
    "entities", "concepts", "comparisons", "queries", "_archive",
]

def scaffold(wiki_path: Path, domain: str, user_id: str | None = None) -> None:
    wiki_path = Path(wiki_path).expanduser().resolve()
    if wiki_path.exists() and any(wiki_path.iterdir()):
        raise ValueError(f"{wiki_path} not empty")

    today = date.today().isoformat()
    wiki_path.mkdir(parents=True, exist_ok=True)
    for sub in SUBDIRS:
        (wiki_path / sub).mkdir(parents=True, exist_ok=True)

    # SCHEMA.md, customize per-domain by swapping templates or string-replacing
    schema = (TEMPLATES / "SCHEMA.md").read_text()
    schema = schema.replace(
        "Product management knowledge base.",
        f"{domain} knowledge base.",
    )
    (wiki_path / "SCHEMA.md").write_text(schema)

    # index, log, overview
    idx = (TEMPLATES / "index.md").read_text().replace("YYYY-MM-DD", today)
    (wiki_path / "index.md").write_text(idx)

    log = (TEMPLATES / "log.md").read_text()
    log += f"\n## [{today}] create | Wiki initialized\n"
    log += f"- Domain: {domain}\n"
    if user_id:
        log += f"- User: {user_id}\n"
    (wiki_path / "log.md").write_text(log)

    ov = (TEMPLATES / "overview.md").read_text().replace("YYYY-MM-DD", today)
    (wiki_path / "overview.md").write_text(ov)
```

#### Node.js / TypeScript

```ts
import { promises as fs } from "node:fs";
import { join } from "node:path";

const SKILL_ROOT = "/opt/yourapp/llm-wiki-pm/skills/llm-wiki-pm";
const TEMPLATES = join(SKILL_ROOT, "templates");
const SUBDIRS = [
  "raw/articles", "raw/papers", "raw/transcripts",
  "raw/internal", "raw/assets",
  "entities", "concepts", "comparisons", "queries", "_archive",
];

export async function scaffold(
  wikiPath: string,
  domain: string,
  userId?: string,
): Promise<void> {
  const today = new Date().toISOString().slice(0, 10);

  await fs.mkdir(wikiPath, { recursive: true });
  for (const sub of SUBDIRS) {
    await fs.mkdir(join(wikiPath, sub), { recursive: true });
  }

  const schema = (await fs.readFile(join(TEMPLATES, "SCHEMA.md"), "utf8"))
    .replace("Product management knowledge base.", `${domain} knowledge base.`);
  await fs.writeFile(join(wikiPath, "SCHEMA.md"), schema);

  const idx = (await fs.readFile(join(TEMPLATES, "index.md"), "utf8"))
    .replace("YYYY-MM-DD", today);
  await fs.writeFile(join(wikiPath, "index.md"), idx);

  let log = await fs.readFile(join(TEMPLATES, "log.md"), "utf8");
  log += `\n## [${today}] create | Wiki initialized\n- Domain: ${domain}\n`;
  if (userId) log += `- User: ${userId}\n`;
  await fs.writeFile(join(wikiPath, "log.md"), log);

  const ov = (await fs.readFile(join(TEMPLATES, "overview.md"), "utf8"))
    .replace("YYYY-MM-DD", today);
  await fs.writeFile(join(wikiPath, "overview.md"), ov);
}
```

### Installing the skill for each user

If each user runs Claude Code in their own container/environment:

```python
def install_skill_for_user(user_home: Path, skill_src: Path) -> None:
    skills_dir = user_home / ".claude" / "skills"
    skills_dir.mkdir(parents=True, exist_ok=True)
    target = skills_dir / "llm-wiki-pm"
    if target.exists() or target.is_symlink():
        target.unlink()
    # symlink if skill is read-only shared; copy if user may customize
    target.symlink_to(skill_src)
```

If your app runs Claude Code SDK programmatically (not interactive):

- Pass the skill directory to the SDK's `skills` option
- Inject `WIKI_PATH` into the env passed to each invocation
- Handle skill loading per-conversation

### Per-user SCHEMA customization

Static template replacement is fine for small domain counts. For richer
customization:

```python
def render_schema(domain: str, taxonomy: dict, thresholds: dict) -> str:
    template = (TEMPLATES / "SCHEMA.md").read_text()
    # swap domain
    template = template.replace(
        "Product management knowledge base.",
        f"{domain} knowledge base.",
    )
    # replace tag taxonomy section with generated one
    taxonomy_md = render_taxonomy(taxonomy)
    template = re.sub(
        r"## Tag Taxonomy.*?(?=\n## )",
        f"## Tag Taxonomy\n\n{taxonomy_md}\n",
        template,
        flags=re.DOTALL,
    )
    return template
```

Store domain presets as JSON/YAML in your app, render per-user on provision.

### qmd provisioning

If your platform provisions qmd too:

```python
def setup_qmd(wiki_path: Path, user_id: str) -> None:
    # Each user gets their own qmd db, isolated indexes, isolated search
    db_path = Path(f"/var/lib/yourapp/qmd/{user_id}.sqlite")
    db_path.parent.mkdir(parents=True, exist_ok=True)

    env = {**os.environ, "QMD_DB": str(db_path)}

    subprocess.run(["qmd", "collection", "add", str(wiki_path),
                    "--name", "wiki"], env=env, check=True)
    subprocess.run(["qmd", "collection", "add", str(wiki_path / "raw"),
                    "--name", "raw"], env=env, check=True)
    subprocess.run(["qmd", "context", "add", "qmd://wiki",
                    "PM knowledge base"], env=env, check=True)
    subprocess.run(["qmd", "embed"], env=env, check=True)
```

For multi-tenant platforms, strongly prefer the qmd SDK:

```ts
import { createStore } from "@tobilu/qmd";

const store = await createStore({
  dbPath: `/var/lib/yourapp/qmd/${userId}.sqlite`,
  config: {
    collections: {
      wiki: { path: wikiPath, pattern: "**/*.md" },
      raw:  { path: `${wikiPath}/raw`, pattern: "**/*.md" },
    },
  },
});
await store.update();
await store.embed();
await store.close();
```

Isolated per-user DB, no CLI subprocess overhead.

### Lifecycle hooks your app should implement

| Event                         | Hook                 | Purpose                                         |
| -------------------------------| ----------------------| -------------------------------------------------|
| User signup / wiki provision  | `scaffold()`         | Create dir structure + templates                |
| Source uploaded               | ingest pipeline      | Save to `raw/`, trigger re-index                |
| Page created/updated by agent | re-index             | `qmd update && qmd embed` or SDK call           |
| Nightly                       | `lint.py --auto-fix` | Keep wiki healthy                               |
| Monthly                       | export private audit | `grep -rl "^private: true"` report              |
| User deletion                 | GDPR delete          | Remove wiki dir + qmd DB + S3 backup            |
| Session start                 | inject context       | Load overview.md + recent log into agent prompt |

### Multi-tenant hardening

- **Filesystem isolation**: each wiki in its own dir, no shared paths
- **qmd isolation**: per-user db file (never share `dbPath`)
- **Privacy enforcement**: server-side `grep "^private: true"` filter before
  any export, not just client-side. Don't trust the agent to remember.
- **Audit log persistence**: ship `log.md` lines to your central logging for
  compliance
- **Backup**: `raw/` and wiki `.md` files are the data. qmd DB is
  regeneratable, don't need to back it up, just rebuild on restore
- **Versioning**: consider making each wiki a git repo under the hood ,
  automatic history, blame, rollback

### Onboarding flow UX (suggested)

When a new user signs up:

1. **Interview**: 3-5 questions to pick domain preset and seed taxonomy
2. **Scaffold**: create wiki dir + SCHEMA customized to answers
3. **First source**: prompt them to upload 1-3 sources immediately so the
   wiki isn't empty on first query
4. **First query**: ask them a seed question about their domain to
   demonstrate the compound-knowledge flow
5. **Habit cue**: explain the weekly rhythm (ingest → query → lint)

Skipping step 1 leaves users with a generic SCHEMA they'll never customize.
Skipping step 3 leaves them with an empty wiki that feels broken.

### API surface to expose to your users

Minimum viable:

```
POST /wikis                    # provision new wiki, returns wiki_id
POST /wikis/:id/sources        # upload a source to raw/
POST /wikis/:id/ingest         # trigger agent ingest flow
POST /wikis/:id/query          # agent query, returns answer + cited pages
POST /wikis/:id/lint           # run lint, returns report
GET  /wikis/:id/pages          # list wiki pages (excludes private if caller not owner)
GET  /wikis/:id/pages/:slug    # get one page
PATCH /wikis/:id/schema        # edit SCHEMA.md (taxonomy tweaks)
GET  /wikis/:id/export         # markdown bundle, private filtered
DELETE /wikis/:id              # GDPR delete
```

Claude Code can be invoked server-side (SDK) per-request, or the user's
Claude Code can connect to your wiki dir via a mounted volume / remote fs.

### What NOT to change

Keep these invariants if you want the skill to keep working:

- Directory structure (`raw/`, `entities/`, `concepts/`, `comparisons/`,
  `queries/`, `_archive/`)
- Required frontmatter fields (title, created, updated, type, tags, sources)
- Wikilink syntax `[[page-slug]]`
- `log.md` entry format `## [YYYY-MM-DD] action | subject`
- `index.md` section headers (Entities / Concepts / Comparisons / Queries)

Break these and `lint.py` and the skill's behavior drift.

### Monitoring your deployment

Metrics worth emitting:

- Pages per wiki (growth rate)
- Ingests per week per user
- Lint 🔴 errors per wiki (target: 0)
- Orphan page ratio (target: <10%)
- qmd index freshness (staleness in hours)
- Private page ratio (governance signal)
- Archive ratio (healthy pruning signal)

Alert on sudden jumps in 🔴 errors or orphan ratio, usually indicates the
agent is skipping orientation.

---

## Summary

|                      | Scenario 1 (human)           | Scenario 2 (platform)                    |
| ----------------------| ------------------------------| ------------------------------------------|
| Install              | symlink to ~/.claude/skills/ | copy/symlink per-user                    |
| Scaffold             | embed scaffold logic         | create dirs + copy templates (see Scenario 2) |
| Env                  | `WIKI_PATH` in rc            | pass per-request                         |
| qmd                  | `qmd collection add`, CLI    | per-user DB via SDK                      |
| SCHEMA               | edit by hand                 | render from presets                      |
| Lint                 | manual, bi-weekly            | nightly cron with `--auto-fix`           |
| Privacy              | trust user                   | server-side enforcement                  |
| Obsidian sync        | user-chosen                  | not applicable (platform-mediated reads) |
| Time to first ingest | ~15 min                      | ~30s after signup                        |
