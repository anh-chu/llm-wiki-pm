---
name: llm-wiki-review
description: Independent review of every answer or page built from the wiki, before it reaches the user. A separate reviewer (Claude Opus by default, another Claude model, Codex CLI, or a command the user sets) checks each statement against its sources, searches for what the answer left out, and checks the reasoning; then you revise. Run it before reporting any wiki-based answer, page write, brief or analysis.
when_to_use: Run before you report anything that states facts or conclusions drawn from the wiki or its raw/ sources - a query answer ("what did customer A ask for in Q4"), an ingest or update, a brief, a research finding, an analysis or synthesis. The review-gate Stop hook blocks the end of a turn that read or wrote wiki content (pages, raw/ sources, wiki search) without it; bookkeeping files such as CLAUDE.md, index.md, log.md and _status.md do not count. Skip only when the user says "no review" or "skip review", or the turn only navigated (listed files, opened a page for the user to read) and stated nothing.
allowed-tools: Read Grep Write Bash
---

# LLM Wiki Review

Sub-skill of llm-wiki-pm. A wrong fact in a PM answer is expensive: "customer A asked for X in Q4" gets repeated in roadmaps and customer calls. Tests on product memos showed a separate reviewer followed by a revision cut errors by about three quarters; a self-check by the author gained less. So the reviewer is always a separate context, never you re-reading your own draft.

## 1. Write the draft down

Write your draft answer or page, exactly as you would send it, to a temp file outside the wiki:

```bash
DRAFT=$(mktemp /tmp/wiki-review-draft.XXXXXX.md)
```

Put the user's question on the first line as `Question: ...`, then the draft. Keep every `[source: ...]` marker and `[[wikilink]]`: the reviewer checks against them. A page write is reviewed before you report it; if you already wrote it, the review may still change it.

## 2. Run the review script

Run the script next to this file (its path is this skill's base directory). Copy this line exactly; the script picks the configured reviewer itself:

```bash
WIKI_REVIEWER_OPTION='${user_config.reviewer}' "<this skill's directory>/run-review.sh" "$DRAFT"
```

Add a second argument only when the user named a reviewer in this request ("review with codex" → `"$DRAFT" codex`). Never pass a reviewer otherwise, not even `claude`.

The script resolves the wiki, fills `reviewer-prompt.md`, runs the reviewer and prints the review. Run it once per turn: after you revise, do not run it again unless the user asks or the revision brought in sources the first review never saw. Always use it: do not review in your own context or start your own subagent instead, and do not choose a different model. The review-gate hook only accepts a turn that ran this script.

Reviewer values (the user's choice for this turn, else `WIKI_REVIEWER`, else the plugin option `reviewer`, else `claude:opus`):

| Value | Reviewer |
|---|---|
| `claude` | a separate read-only Claude process, account default model |
| `claude:haiku`, `claude:sonnet`, `claude:opus` | the same on that model (`claude:opus` is the default) |
| `codex` | Codex CLI in a read-only sandbox |
| anything else | a shell command that reads the prompt on stdin and prints the review |

If the script fails, say so and run it again with `claude:opus`; never skip the review silently.

## 3. Revise

For each point the reviewer raises, decide: **accept** (fix the draft) or **reject** (the reviewer is wrong; say why in one line). Do not accept a point just because a reviewer made it: check it against the source yourself. Reviewers are usually right, but not always. If a point is about something missing and the missing fact is real, add it with its source.

If you change a statement, the source must support the new text. Never resolve a point by softening wording until it is unfalsifiable.

## 4. Report

Send the revised answer. End it with one line:

`Reviewed by <reviewer>: <n> points, <a> fixed, <r> rejected.` followed by anything still open (an unverified claim, a source the reviewer could not reach, a gap only the user can fill).

For a page write, also append to `log.md`: `## [YYYY-MM-DD] review | <page> | <reviewer>: <n> points, <a> fixed, <r> rejected`.

Delete the draft file.
