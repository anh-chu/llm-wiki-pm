# Ingest Guide — full procedure

The core skill's §2 stub gates the decision; this file is the full step-by-step.
Read it before ingesting a source — it defines provenance, page thresholds, and
the privacy filter, and skipping it produces orphan pages, missing cross-refs,
and laundered secondhand claims.

## ① Capture raw (choose source type)

- URL → `web_fetch` → save markdown to `raw/articles/<slug>.md`
- PDF → extract text → `raw/papers/<slug>.md` (keep PDF in `raw/assets/`)
- Paste/transcript → `raw/transcripts/<slug>.md`
- **Chat thread (any messaging tool — Slack, Teams, Discord, etc.)**: copy thread
  messages → `raw/internal/<channel>-<date>.md`. Add frontmatter:
  `source_channel: "<tool>:#channel-name"` (e.g. `"Slack:#product-strategy"`),
  `source_date_range: "YYYY-MM-DD"`, `source_thread_id: "<thread-id>"` (Slack
  `thread_ts`, or whatever stable thread identifier the tool exposes). Dedup:
  before saving, grep wiki for the same `source_thread_id` to avoid double-ingest.
  Strip @mentions to initials if private.
- **Email chain (any mail provider — Gmail, Outlook, etc.)**: export thread text →
  `raw/internal/email-<subject-slug>-<date>.md`. Add frontmatter:
  `source_channel: "<provider>"` (e.g. `"Gmail"`),
  `source_date_range: "YYYY-MM-DD/YYYY-MM-DD"`, `source_thread_id: "<thread-id>"`.
  Strip external email addresses if sensitive.
- **Current conversation**: when user says "from this conversation" or "use what
  we discussed", treat the session as a source. Save a summary to
  `raw/internal/conversation-<YYYY-MM-DD>.md`. Distinguish:
    - User-stated facts: attribute as `user, <date>`
    - Tool-retrieved (chat, email, web_fetch): attribute to original source
  Do not collapse these. Keep provenance separate in the raw file.
- Name descriptively: `raw/articles/gartner-test-automation-mq-2026.md`
- **Privacy filter (mandatory)**: strip API keys, tokens, passwords from raw.
  If the source contains customer-identifying info, deal sizes, 1:1 content,
  or internal-only strategy, set `private: true` on resulting wiki pages.

## ② Surface takeaways to user BEFORE writing wiki pages

What's interesting? What matters for the PM domain? Which entities/concepts does
this touch? (Skip in automated/batch contexts.)

## ③ Check existing pages

`grep -r` for every entity/concept mentioned. Read existing pages before deciding
create vs update.

## ④ Apply Page Thresholds (from SCHEMA.md)

- Create entity page only if 2+ sources mention OR central to current source
- **People specifically**: create a person entity page when a person appears in
  2+ sources, has a named role, or is central to a relationship being mapped.
  Don't wait for the user to ask. Apply the same 2+ threshold proactively.
- **Enrich from connected tools BEFORE writing** (per the Freshness-first protocol
  in Session Defaults — applies to every page type, not just people). Don't build
  a page by inferring from the prose of other wiki pages alone. Run a live sweep
  of connected tools — chat, email, meeting notes, CRM — for the topic and any
  names/emails/handles. Capture findings to `raw/internal/<topic>-<source>-<date>.md`
  and anchor each claim with inline provenance. If no tools are connected, write
  `coverage: stub` and list unknowns in `gaps:` rather than guessing.
- Passing mentions in footnotes don't warrant pages
- Update existing pages rather than duplicating

## ⑤ Write/update pages

- Required frontmatter (title, created, updated, type, tags, sources)
- Tags MUST come from SCHEMA.md taxonomy, add new tags there first
- Minimum 2 outbound `[[wikilinks]]` per page
- Contradictions → note both positions with dates + sources, add
  `contradictions: [page-name]` to frontmatter, flag in log
- Supersession: if a new page materially *replaces* (not just revises) an old one,
  set `supersedes: [old-slug]` on new page, `superseded_by: new-slug` on old page.
  Archive the old page. `lint --auto-fix` rewrites inbound links.
- **Inline provenance (mandatory):** every non-obvious factual claim must have an
  inline source marker: `[source: raw-slug, p.N]` or `[source: raw-slug, section-name]`.
  Frontmatter `sources:` lists all sources for the page; inline markers anchor
  specific claims to specific sources. Without inline markers, updates silently
  corrupt provenance.
- **Coverage marker:** set `coverage: stub | partial | comprehensive` in frontmatter.
  `stub` = bare entity with minimal facts. `partial` = some sections filled but
  known gaps. `comprehensive` = all known sections covered. Add `gaps:` list for
  partial/stub pages.
- **Confidence level:** set `confidence: verified | likely | rumor` when source
  quality varies. See SCHEMA.md for definitions.

## ⑥ Backlink audit

After creating a page, scan related pages and add inbound `[[links]]` so the new
page isn't an orphan.

## ⑦ Update `overview.md`

If the source shifts the domain synthesis, edit the overview. Keep it under 200
lines. Link heavily.

## ⑧ Update navigation + log

- Add new pages to `index.md` under correct section, alphabetical
- Bump total page count + "Last updated" header
- Append to `log.md`: `## [YYYY-MM-DD] ingest | <source title>` with a list of
  every file created/updated

## ⑨ Update MY-INTEGRATIONS.md (auto-log source routing)

After each ingest, append or update the source row in `$WIKI/MY-INTEGRATIONS.md`.
If the file doesn't exist, create it from `$CLAUDE_SKILL_DIR/templates/MY-INTEGRATIONS.md`.
Row format: `| <source-label> | <type> | <YYYY-MM-DD> | <N> | <notes> |`
Types: `web` | `chat` | `email` | `transcript` | `pdf` | `conversation` | `internal` | `other`
(`chat` covers any messaging tool — Slack, Teams, Discord, etc.; `email` covers
any mail provider. Record the specific tool in `<source-label>` / `source_channel`.)
This is how the skill learns which integrations you actually use. No fabrication —
only log sources actually ingested this session.

## ①⓪ Report to user

List every file touched. One source → 5-15 pages is normal. Confirm before
mass-updating (10+ pages).

## ①① Crystallize (for transcripts and research chains)

When ingesting a meeting transcript, 1:1 notes, or multi-source research, produce
a digest page under `queries/` with sections: Context, Decisions, Action Items,
Open Questions, Lessons/Patterns. Required frontmatter: title, type: query, tags,
sources, private. See `crystallize-guide.md`. Link affected entity pages back to it.

## ①② Entity promotion scan (after every ingest)

Scan pages you just created or updated for named people, companies, and products
described with 3+ attributes (role, style, concerns, position, history, etc.).
- If found in a concept page: prompt user, "X entities in [[page]] meet the entity
  threshold. Create individual entity pages?"
- Don't silently promote. Always confirm.
- After splitting, update the concept page to link out: `[[entity-slug]]` instead
  of the inline prose.
- Check whether a persona page is warranted for any promoted person entity (the
  `llm-wiki-persona` sub-skill handles persona pages).
