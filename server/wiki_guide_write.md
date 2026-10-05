
## Writing to the wiki

Writes are enabled. The server enforces the wiki's rules and refuses anything that breaks them, returning a list of errors to fix.

**Before you write.** Search first so you do not duplicate a page. For a new entity or concept the wiki's threshold is: it appears in two or more sources, or it is central to one. Check `wiki_info` and `wiki_lint` when asked about wiki health.

**Tools**
- `wiki_save_raw`: save a source to `raw/` unchanged (articles, transcripts, chat or email threads, data snapshots). Create-only; nothing can change `raw/` afterwards. Redact secrets first. For chat or email threads add `source_channel`, `source_date_range` and `source_thread_id` frontmatter.
- `wiki_create_page`: a new page in `entities/`, `concepts/`, `comparisons/` or `queries/`. Give the full page: frontmatter (`title`, `created`, `updated`, `type`, `tags`, `sources`, plus `coverage: stub|partial|full`, `gaps`, and `confidence: verified|likely|rumor` where you can), at least 2 `[[wikilinks]]` to existing pages, and inline `[source: <raw-file-stem>, <location>]` markers. Tags must already exist in SCHEMA.md; do not invent tags.
- `wiki_append`: add a new fact as a dated section ending with an inline source marker. Use `[source: conversation, YYYY-MM-DD]` for facts the user told you.
- `wiki_edit`: correct text. `old_string` must match exactly once. Works on pages and on `overview.md` (update it when the overall picture changes).
- `wiki_supersede`: when a new page materially replaces an old one. Call it with `apply=false` first, show the user the plan (which pages' links will be rewritten), then call it again with `apply=true`. With 10 or more pages you must pass `confirm_rewrite_count`.
- `wiki_archive_page`: remove a page by moving it to `_archive/`; it never hard-deletes. Pages that still link to it are listed in `inbound_links` and are not rewritten, so tell the user which to fix. Only archive when the user asks or the page is clearly wrong.

**Hashes.** Read the page first with `wiki_read` (the whole page, following `next_offset`) and pass its `hash` as `expected_hash` (`old_hash` and `new_hash` for supersede). A stale hash is refused: re-read and redo the change.

**Rules**
- Never build a page only from other wiki pages. Anchor each non-obvious claim with a source marker pointing at a primary source.
- When new information conflicts with a page, show the user the old and new text and ask before changing stated strategy or touching several pages. If the conflict is unresolved, keep both claims with dates in the page.
- Filenames are lowercase-hyphen. No em-dashes. Plain, natural wording. Pages are private by default; you cannot mark one shareable.
- After a batch of changes run `wiki_lint` and report any new errors.
- Each write is snapshotted to `_archive/` and logged ("via wiki-mcp (ChatGPT)"), so the user can undo a mistake.
