
## Writing to the wiki

Writes are enabled. The server enforces the wiki's rules and refuses anything that breaks them, returning a list of errors to fix.

- Read the page first with `wiki_read` and keep its `hash`. Read the whole page (follow `next_offset`) before editing it.
- Prefer `wiki_append` for a new fact (a dated section ending with an inline `[source: conversation, YYYY-MM-DD]` marker) and `wiki_edit` to correct text (`old_string` must match exactly once). Pass the page's `hash` as `expected_hash`; a stale hash is refused, so re-read and redo.
- Use `wiki_create_page` only for a topic with no page yet. Search first so you do not duplicate one. Give it the full page: frontmatter (`title`, `created`, `updated`, `type`, `tags`, `sources`), at least 2 `[[wikilinks]]` to existing pages, and inline `[source: ...]` markers. Tags must already exist in SCHEMA.md; do not invent tags.
- To remove a page use `wiki_archive_page` (needs the page's `hash`). It moves the page to `_archive/` and removes its index line; it never hard-deletes. Pages that still link to it are listed in `inbound_links` and are not rewritten, so tell the user which pages to fix. Only archive when the user asks or the page is clearly superseded or wrong.
- Filenames are lowercase-hyphen, in `entities/`, `concepts/`, `comparisons/` or `queries/`. Nothing else can be written.
- No em-dashes. Plain, natural wording.
- Confirm with the user before changing a page's stated strategy or any change touching several pages, and say which page you changed and why.
- Each write is snapshotted to `_archive/` and logged, so a mistake can be undone by the user.
