# Source Discipline (full reference)

The core `SKILL.md` carries a compressed **Source discipline** block in Session
Defaults with the four named guards. This file holds the full detail. Read it
when you are about to do a substantive ingest, a multi-source sweep, a
decision-bearing synthesis, or an exec-facing answer — i.e. exactly when getting
provenance wrong is expensive.

The through-line: **the wiki is a map, not the territory.** Verify from source;
use the wiki to know where to look. Much of this is enforced deterministically —
the `pre-write.sh` freshness gate injects a reminder when a knowledge page is
written with no primary source or inline `[source:]` marker, and `lint.py` flags
self-referential sourcing (🔴 for factual/decision pages), missing inline
provenance, missing `coverage:`, and stale `last_verified`. The prose below is
the judgment the hooks and lint cannot encode.

## Freshness-first (counterweight to wiki-first)

The wiki is only as good as what is fed into it. Wiki-first must not become a
self-reinforcing loop where the wiki only cites itself and drifts from reality.
For ANY substantive operation (answer, create, update) on any page type:

- **Before writing/updating a page**, sweep connected tools (Slack, Gmail,
  Granola/meetings, CRM, web) for newer primary sources on the topic. Ingest what
  you find to `raw/` and anchor claims with inline provenance. Don't build or
  revise a page purely from other wiki pages' prose — that launders secondhand
  mentions into false confidence.
- **One batch sweep satisfies freshness-first for a batch operation.** A
  daily-maintenance run or multi-page ingest does ONE registry-driven sweep up
  front, then writes all the pages that sweep covered — not one sweep per page.
  The per-page rule applies only to a standalone single-page decision-bearing edit.
- **When answering**, if the most relevant pages are thinly sourced, stale, or
  single-source, run a quick live search to corroborate before relying on them.
- **Default to ingest, not just recall.** Treat anything a connected tool surfaces
  that the wiki lacks as a candidate ingest, not a throwaway lookup.
- **Be honest about provenance age.** Distinguish "the wiki says X (as of
  <date>)" from "live sources confirm X today."
- **Respect cost.** Proportional to stakes: a quick lookup needn't trigger a full
  sweep; anything written, updated, or decision-bearing should be checked live.

## Source-completeness guard (anti-premature-closure)

A thin, empty, or errored result from a requested source is NOT permission to
stop — it is a signal your search, not the source, may be the problem.

- **Define the source set before you sweep (anti-omission).** Before any "ingest
  all sources" / daily-brief / multi-source sweep, enumerate the **canonical
  sweep registry** in `$WIKI/MY-INTEGRATIONS.md` (`## Sweep Registry`) and iterate
  every source listed. The registry, not your memory, defines "all sources." If
  it's missing, build the set from connected tools + the `Active Sources` table,
  confirm with the user, and write it to the registry before sweeping.
- **Empty ≠ done.** Run ≥2-3 query variations before concluding a source is empty
  (broaden/narrow terms, widen the window, try aliases/handles/scope variants,
  switch search syntax).
- **Distinguish three states:** `hits`, `empty-after-retries` (nothing after ≥2
  varied queries), `failed` (auth error, not connected, timeout). Never silently
  collapse `failed`/`empty-after-retries` into "covered."
- **Make voids visible.** Report the status of every requested source, including
  empty/failed ones: which source, queries tried, likely reason.
- **No closure language over an unresolved void.** Don't call a sweep complete
  while any requested source is `failed` or was abandoned after one query.
- **Proportional, not infinite.** ≥2 varied queries per source, then report state.

## Source-depth guard (open what you found)

Breadth of search is not depth of source. A hit that *references* content is not
the content.

- **Referenced ≠ read.** A Slack thread with an attached 1-pager, a message
  linking a Drive doc, a ticket citing a spec — the prose around the artifact is a
  pointer, not a substitute.
- **Open before you write.** Fetch the artifact (read the image, download the doc,
  follow the link) before producing any analysis that depends on it. Real tiers,
  prices, numbers, and matrices routinely live only inside the file and contradict
  the thread summary.
- **Name what you couldn't open.** If an artifact can't be fetched, treat it like
  a `failed` source: flag it as unread, don't synthesize over it, offer the next step.

## Provenance-tier & falsification guard (anti-laundering on the output side)

The guards above govern what goes INTO pages. This governs what comes OUT — in an
answer, synthesis, or decision artifact. Failure mode: "wiki-first" silently
becomes "wiki-only," and confident claims get laundered out of secondhand wiki
prose without ever being checked against primary data.

- **Tier every asserted claim (computed / primary / recalled).** Before putting a
  claim in an answer or decision artifact, classify it: `computed` (you ran a
  query/calc against primary data this session), `primary` (you read a live
  primary source this session), or `recalled` (from wiki prose or memory).
  Computed/primary are trustworthy; a recalled claim is a hypothesis until upgraded.
- **Never launder recalled into asserted.** Don't state a recalled claim as fact
  in a decision-bearing or exec-facing answer without upgrading it to
  primary/computed. Generalizing from a couple of named examples onto a whole
  population is the classic laundering move — label it a hypothesis, test it
  against the full dataset first.
- **Route to the authoritative source; don't wait to be told.** For targeting,
  pipeline, and quantitative questions the authoritative source is the primary
  system (CRM/SFDC, warehouse, Gong), not the wiki. The wiki is the index that
  points there.
- **Mandatory falsification pass before exec-facing synthesis.** For each headline
  claim, name the single query or source that would DISPROVE it, then run that
  check. Claims that survive get asserted; claims you couldn't test get labelled
  unverified.
- **Show your tiers when it matters.** In a decision artifact, mark which claims
  are computed/primary vs. still recalled/unverified so the reader can calibrate.
- **Self-select scope and altitude.** Default to the user's actual ownership and
  the audience in the room (check their own entity/role page) before opening with
  org-wide framing.
- **Recency ≠ authority.** A dated figure from a primary system still outranks a
  fresh secondhand wiki mention. Fresh does not mean true.
- **Proportional.** A casual lookup needs none of this; anything feeding a
  decision, a targeting call, or an exec conversation needs all of it.
