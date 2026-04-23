# Contributing to llm-wiki-pm

## Adding a New Operation to SKILL.md

1. Add a new numbered section (`### N. Operation Name`) after the last existing operation
2. Follow the established pattern: trigger conditions → numbered steps → log entry format
3. Update the "When This Skill Activates" list at the top of SKILL.md if the operation has a natural-language trigger
4. Add a reference doc to `skills/llm-wiki-pm/references/` if the operation is complex enough to warrant one
5. Update `plugin.json` description if the new operation is user-facing and notable

## Adding a Worker Agent

1. Create `.claude/agents/worker-<name>.md`
2. Required frontmatter: `name`, `description`, `model` (use `sonnet` for I/O workers)
3. Include the standard wiki path resolution block
4. **Output rule is mandatory**: workers write to `/tmp/<name>-<YYYYMMDD>.md` and return only a short status + path
5. Update `plugin.json` → `metadata.workerCount` and `metadata.skillArchitecture`

## Adding a Role Pack

1. Copy `.claude/roles/_template.md` → `.claude/roles/<role-id>.md`
2. Set `focus_tags` to a subset of the tag taxonomy in `templates/SCHEMA.md`
3. Update `plugin.json` → `metadata.rolePackCount`

## Version Bump Protocol

This project uses [semver](https://semver.org/):

| Change type | Version bump | Examples |
|-------------|-------------|---------|
| New operation, new worker, new role pack | **minor** (2.5.0 → 2.6.0) | Add §13, new worker agent |
| Bug fix, clarification, constraint tightening | **patch** (2.5.0 → 2.5.1) | Fix broken bash snippet, clarify orient gate |
| Breaking change to wiki structure, frontmatter schema | **major** (2.x.x → 3.0.0) | New required frontmatter field, changed directory layout |

When bumping version:
1. Update `version` in `.claude-plugin/plugin.json`
2. Update `version` in `.claude-plugin/marketplace.json`
3. Add entry to `CHANGELOG.md`
4. Tag the release: `git tag v<version>`

## Testing Checklist

Before opening a PR:

- [ ] Orient protocol still works on a fresh wiki (scaffold → read SCHEMA + index + log + overview)
- [ ] Ingest flow produces pages with valid frontmatter (title, type, tags, sources, updated, coverage)
- [ ] `scripts/lint.py` runs without error on a test wiki
- [ ] `scripts/backlinks.py` returns correct results for a known slug
- [ ] New operation logged to `log.md` correctly
- [ ] `plugin.json` version bumped if applicable
- [ ] No hardcoded wiki paths (all use `.wiki-path` resolution chain)

## What NOT to Change Without Discussion

- The three-layer wiki architecture (`raw/` / wiki pages / `SCHEMA.md`)
- The orient gate (steps ①-④ required before writes)
- The `[[wikilink]]` format — this is what makes the wiki Obsidian-compatible
- The `private: true` frontmatter convention — users rely on this for exports

## First-Time Setup for Development

```bash
git clone https://github.com/anh-chu/llm-wiki-pm
cd llm-wiki-pm

# Set wiki path (creates the file the SessionStart hook reads)
echo ~/test-wiki > .wiki-path

# The SessionStart hook scaffolds the wiki on first session start.
# To test without a full Claude Code session, manually create the structure:
mkdir -p ~/test-wiki/{raw/{articles,papers,transcripts,internal,assets},entities,concepts,comparisons,queries,_archive}
cp skills/llm-wiki-pm/templates/SCHEMA.md ~/test-wiki/SCHEMA.md
cp skills/llm-wiki-pm/templates/index.md ~/test-wiki/index.md
cp skills/llm-wiki-pm/templates/overview.md ~/test-wiki/overview.md
cp skills/llm-wiki-pm/templates/log.md ~/test-wiki/log.md

# Run lint on the scaffolded wiki (should report no errors)
python3 skills/llm-wiki-pm/scripts/lint.py ~/test-wiki
```
