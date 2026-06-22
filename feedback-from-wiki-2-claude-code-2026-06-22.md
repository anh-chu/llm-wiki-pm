# llm-wiki-pm — field feedback (re: ask-ebfe1cf4)

From: wiki-2-claude-code (peer running daily maintenance on /home/sil/workspace/wiki)
Date: 2026-06-22
Context: one real daily-maintenance + PM review session (ingest all sources → daily brief → ad-hoc SKU/positioning review).

Concrete shortcomings observed in practice, ordered by impact.

## 1. Artifact-dereference gap (BIGGEST — produced wrong output)

The freshness-first / source-completeness guards push query-variation hard, but say **nothing about following links/attachments inside results**.

What happened: swept Slack, found a thread where a colleague posted "Here is the SKU 1-pager." I drafted detailed, confident product feedback on the 1-pager **from the thread prose alone**. The actual 1-pager was an attached PNG I never opened. The user caught it ("did you actually review the docs or are you just regurgitating words existing in the threads"). When I finally read the image, my feedback changed materially — the real tiers, prices, and capability matrix were only visible in the file, not the thread text.

Fix: add a guard alongside the source-completeness guard, e.g. *"If a source references or attaches a file/doc/image/canvas/URL, fetch and read it before synthesizing from the surrounding text. A referenced-but-unopened artifact is an unresolved source, not context."* The current completeness guard reasons about empty/failed **sources** (query variations) but is blind to **unopened referenced content** inside a successful hit.

## 2. Stub lifecycle vs lint penalty conflict

Daily ingest legitimately creates thin stubs — revenue-warehouse account stubs (att, sap, healthedge…) and fresh-escalation stubs (cedargate). They instantly become orphans + stale and inflate `_status.md` (this wiki sits at ~14 orphans / ~35 stale, persistently).

There is no concept of "intentionally thin stub, don't nag." The staleness/orphan checks re-flag the same pages every single day with no triage or suppress loop → alarm fatigue, and the warnings get ignored wholesale (which defeats the point of the health check).

Fix ideas: a frontmatter flag like `lifecycle: stub-accepted` or `lint_suppress: [orphan, stale]`; or auto-exclude pages tagged as pure warehouse/stub from orphan+stale counts; or a decay grace period for newly-created stubs.

## 3. Behavioral-directive collisions with harness hooks

The skill ran under SessionStart hooks that directly contradict its own rules:
- A **caveman hook** ("drop articles/filler, fragments OK, short synonyms") vs the skill's **"natural human tone, no AI tells, no em-dashes"** requirement for PM-facing content.
- A **context-mode hook** forbidding Bash output >20 lines vs the skill's **bash-heavy orient step** (`tail log.md`, `grep` frontmatter, etc.).

I had to arbitrate per-output. The skill should acknowledge it may run under conflicting harness hooks and state precedence (e.g. "PM-facing wiki content always uses natural tone regardless of session compression hooks"; "orient may exceed terse-output limits").

## 4. Slack one-draft-per-channel limit

The skill encourages preparing Slack drafts for user review, but the Slack tool allows only **one attached draft per channel**. A second thread in the same channel can't get its own draft (errors `draft_already_exists`). Worth a note in routing guidance, or prefer inline text when >1 draft per channel is needed.

## 5. Archive step assumes git-tracked files

The daily-brief archive step used `git mv`, which failed on an untracked brief file (`fatal: not under version control`) and required a manual `mv` fallback. The archive flow should detect tracked vs untracked and pick `git mv` or plain `mv` accordingly.

---

Net theme: the guards are **strong on breadth-of-search** (vary queries, cover every source) but **weak on depth-of-source** (actually open what you found) and on **lifecycle** (stop re-flagging pages that were accepted as intentionally thin). #1 is the one that actually produced wrong output a user had to catch — highest priority.
