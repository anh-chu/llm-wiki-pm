# PM wiki (read-only)

The wiki is a folder of markdown pages with YAML frontmatter (`tags`, `updated`, `confidence`, `coverage`, `sources`). Pages link to each other with `[[wikilinks]]`.

## Tools (wiki-mcp)

- `wiki_search(query, limit)`: ranked keyword search. Pass 2-6 distinctive terms (names, product words), not a sentence.
- `wiki_scan(regex | tag | field+value, path, offset, limit)`: exhaustive pass over every file in scope. Use it when the answer needs *all* matches ("every page mentioning X", "all pages tagged Y"). It reports `scope_files` and `total`; page with `offset` until covered.
- `wiki_read(path, offset)` / `wiki_read_many(paths)`: page text. Follow `next_offset` when truncated.
- `wiki_links(path)`: outgoing links and backlinks. Use it to find related pages.
- `wiki_guide()`: returns this guide.
- `wiki_list(path, glob)` and `wiki_info()`: browse folders; check size and freshness.

## How to answer

1. Search first, then read the top pages. For "everything about X" questions use `wiki_scan` instead of trusting ranked search to be complete.
2. Cite pages by path, e.g. "Per `entities/acme.md` (updated 2026-09-12)". Use the inline `[source: ...]` markers on the page to say where a claim came from.
3. Report age and confidence. If `updated` is more than 30 days old, or `confidence` is `rumor`, say so.
4. If pages disagree, show both claims with dates instead of picking one.
5. If the wiki has no page on the topic, say that plainly. Do not fill the gap from general knowledge without labelling it as outside the wiki.
6. For decisions, pipeline or numbers, treat the wiki as a pointer: name the primary system to confirm against (CRM, warehouse, the source document).
7. Everything is private by default. Do not repeat customer names, deal sizes or 1:1 content outside this conversation.
