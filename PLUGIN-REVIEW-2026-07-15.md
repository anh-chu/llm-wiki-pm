# llm-wiki-pm — Brutal Plugin Review & Remediation Plan

Date: 2026-07-15 · Method: 7-lens review → adversarial verify per finding → synthesis (65 agents). 39 findings survived verification, 18 rejected. Top-3 findings independently re-verified against source by the maintainer.

Distribution decision: **distributed** (marketplace + GitHub) → proper-noun scrub is in scope.

---

## Bottom line

The deterministic layer (hooks, `lint.py`, 3-layer data model, concurrency lock) is genuinely good and should be preserved. The problem is the always-on `SKILL.md`: ~12k effective always-on tokens, and its highest-severity guardrails are **prose that structurally cannot fire** — the exact failure the retro documented. Two guards are actively misleading (a `(enforced)` label with nothing enforcing it; a `private: true` model that contradicts the `shareable`-allowlist `lint.py` actually reads). There is also a real P0 shell bug and the primary retrieval path names tools that don't exist.

Through-line of the fix: **cut redundant prose ~half, convert the mechanizable guards into hooks/lint, relabel the fake gates as checklists, fix the tool naming and privacy contradiction, fix the P0, add one fast path.**

## Always-on token budget

| | Estimate |
|---|---|
| Current effective always-on | ~12,000 |
| Target | ~6,500 |

Biggest single lever: remove the `session-start.sh` forced-load clause so the ~8.2k `SKILL.md` loads only on PM-relevant turns (via the skill's own `when_to_use` trigger) instead of every session's first message. Within `SKILL.md`, the prose cuts total roughly −3.0k to −3.7k.

---

## P0 — ship immediately (verified against source)

**A1. Fix `session-stop.sh` infinite log re-rotation.** `hooks/session-stop.sh:29`
`ENTRY_COUNT=$(grep -c '^## \[' "$LOG_FILE" 2>/dev/null || echo 0)` — `grep -c` prints `0` *and* exits 1 on zero matches, so `|| echo 0` appends a second line → `ENTRY_COUNT="0\n0"`, the `-le 500` test errors, falls through, and **rotates the log on every SessionEnd** (spawning `log-YYYY-part-2/3/…`, moving the real log aside each time).
Fix: `... 2>/dev/null || true)` then `ENTRY_COUNT=${ENTRY_COUNT:-0}`. Add regression tests (header-only log must NOT rotate; >500-entry log must). · effort S · tok 0

---

## P1 — high leverage (recommended this batch)

**A2 (REVISED — preserves set-and-forget). Replace the full forced-load with a slim always-on trigger primer.** `hooks/session-start.sh` (additionalContext, ~line 231).
Rationale: the forced-load conflates two jobs — (a) keeping the *ambient watcher* alive so proactive behaviors (#1 Recall, #2 Ambient Capture, #3 Contradiction) fire in conversations that don't already look wiki-shaped [this IS set-and-forget], and (b) loading the entire ~8.2k-token `SKILL.md`. Only (a) needs to be always-on. Plain deletion (original A2) would lose the watcher and weaken set-and-forget; keeping the full load pays 8.2k every session. Split them.
Change: replace the "Before responding to the first user message — regardless of what it is — invoke the skill…" sentence with a ~300–400 token primer that lists ONLY the ambient triggers and says: if the user drops a PM fact / named entity / decision / open question — even in passing — invoke `llm-wiki-pm`; otherwise do not load it. Keep the health/lock/path `$CONTEXT`. Full `SKILL.md` then loads only when a trigger fires or the user asks for an operation (via `when_to_use`).
Result: ambient capture still fires everywhere (set-and-forget intact); always-on drops ~8.2k → ~0.4k on non-wiki sessions. · effort S · **tok ≈ −7500 (non-wiki sessions), set-and-forget preserved** · prose→mechanism

**A3. Collapse the five prose guards into one.** `SKILL.md:125-157` (+ `:574-579`, `lint.py:246-252`). Keep ~250 tokens: a wiki-first+freshness line that *points at* the already-firing pre-write hook + lint checks (input side already enforced); a one-line provenance-tier/falsification rule pointing to a reference for detail. **Preserve verbatim** the three named anchors sub-skills cite (Source-completeness, Source-depth, Provenance-tier & falsification guard) + source-completeness's registry/3-state (hits/empty/failed) rule + source-depth's "open the referenced artifact" rule. Move un-hookable falsification detail + scope/altitude + "route to authoritative source" to a reference. Extend `lint.py` self-referential check so a `queries/` synthesis sourced only from wiki pages is a hard 🔴. · effort L · tok −1600 · prose→mechanism

**A4. Convert pre-update snapshot to a hook.** `hooks/pre-write.sh` (+ `SKILL.md:372-375, 560-561`). After the gated-dir check, if the target exists, copy it to `_archive/<slug>-<date>.md` (idempotent). Cut the "mandatory" snapshot prose to one line noting the hook does it. The one unrecoverable operation should not depend on the model remembering. · effort M · tok −80 · prose→mechanism

**A5. Fix phantom retrieval tool naming.** `SKILL.md:169,175,347-349,379,389`; **must-fix** `references/update-guide.md:30` (a fake `wiki-search semantic_search "..."` bash command). The bundled MCP exposes an action dispatcher — `view(action=semantic_search|read|backlinks)`, `global_search` for exact phrases — not a bare `wiki-search` command. Following the skill literally, the agent finds no such tool and silently falls back to grep/Read (the degraded path the skill warns against). Add one canonical mapping line; fix the fake bash. · effort M · tok −80

**A6. Kill the `private: true` / `shareable` contradiction.** `AGENTS.md:61`, `research:254`, `persona:64/137/145`, `brief:252`, `templates/persona.md:23`. `lint.py` reads only `shareable` (absence = private); the `private: true` prose points at a flag lint never reads → false protection confidence. Rewrite to the allowlist model. Delete the `private:` field from persona template. (`lint.py:67-68 is_private` = dead code — delete, see open decisions.) · effort S · tok −30

**A7. Relabel the fake Orient gate.** `SKILL.md:294-299`. Drop `(enforced)` + "refuse any write operation"; replace with a 2-3 line checklist. A PreToolUse hook cannot verify four Reads happened this session, so don't fake it as a hook either. Keep steps ①-④ verbatim. · effort S · tok −70

**A8. Collapse 8 Proactive Behaviors → 2.** `SKILL.md:55-112`. (A) named-entity/person mention → one-line recall iff a page exists, always flag rumor/unverified (merges #1/#3/#6). (B) after a substantive PM fact/task → one capture offer after the mandatory dedup search (merges #2/#4/#5/#7, keep "dedup gate"). Keep the max-1/turn + skip-code/debug limits. Cut #8 Tool Discovery (move trigger to `recommended-tools.md`). · effort M · tok −550

**A9. Convert coverage:/gaps: guard to a lint check.** `lint.py` per-page loop + `SKILL.md:567-568`. Warn (🟡) if a factual-type page lacks `coverage:`. Shorten the Pitfall to point at the check. · effort M · tok 0 · prose→mechanism

**A10. Fix confidence-decay to use the schema field, not `grep "competitive"`.** `session-start.sh:161-163` + `SKILL.md:288-290` + `SCHEMA.md:263-265`. Parse frontmatter `tags`/`confidence_decay_days` instead of grepping the literal word. Delete Orient step ⑦ (hook precomputes + step ⑧ surfaces). · effort M · tok −60 · prose→mechanism

**A11. Fix `wiki-search.sh` path resolution.** `hooks/wiki-search.sh:10`. Use the same precedence as the other four hooks (`.wiki-path` → plugin option → `WIKI_PATH` → pwd). Add a smoke test. · effort S · tok 0

**A12. Delete `references/nextjs-integration.md` (610 lines) + pointer at `SKILL.md:593`.** `obsidian-sync.md` already covers multi-device/viewing zero-build. · effort S · tok −15

**A13. Add a ≤6-line MICRO-CAPTURE fast path.** `SKILL.md:22-27, ~321`. For a single conversational fact only (`source conversation|<date>`): skip ingest-guide read, crystallize, entity-promotion, per-op freshness sweep. Keep exactly one mandatory step: dedup search (append vs create-stub). Still orients once/session. Full 12-step ingest stays for files/URLs/transcripts/warehouse/email/chat and any batch. · effort M · tok +300 (worth it — kills 14-step ceremony for the common case)

**A14. Add tests for untested critical code.** `tests/test_hooks.py`. Priority: (1) pre-write freshness gate (grounded vs ungrounded, Edit-without-content reads disk, non-wiki paths); (2) `lint.py --json` shape + self-referential/orphan/broken-link + `merge_sort_index` idempotence; (3) contract test that `session-start.sh` parses `lint.py --json`. · effort L · tok 0 · prose→mechanism

---

## P2 — polish (defer or fold in opportunistically)

**A15.** Trim Pitfalls `SKILL.md:532-579` to items not already a step/guard. Keep: never-touch-raw/, thresholds, tags-to-SCHEMA-first, contradictions-explicit, min-2-backlinks, confirm-10+, rotate-at-500, human-tone (verbatim), supersede fields, session-lock, dedup. Delete restatements (orient-first, private-by-default, use-wiki-search-first, snapshot, verify-writes, coverage-markers, don't-launder). · tok −340
**A16.** De-dup authority in `AGENTS.md:14-25,37-45` → one-line pointers at core; repoint "per AGENTS.md" cites in brief/persona/prd/research, drop brittle step-counts. Keep `AGENTS.md` as a thin entry point. · tok 0
**A17.** Trim Pre-Flight/Orient overlap `SKILL.md:236-303` (drop duplicated WIKI-resolver bash; single `_status.md` surfacing; move "Harness-hook precedence" essay to a reference). Do NOT merge the two lists. · tok −220
**A18.** Delete Architecture ASCII tree `:209-234` (→ pointer + move to ingest/schema refs); delete PM Workflow Patterns `:512-527`; delete model-routing table `:200-207` (already in worker frontmatter). · tok −560
**A19.** Move query-path falsification to a conditional pointer `SKILL.md:351-356`; shorten source-depth guard `:145-148` to ~3 lines. · tok −200 (see open decision — inline-at-point-of-use does fire better)
**A20.** Hook data-hygiene: `post-write.sh:109-112` stop appending "clean" `_status.md` (kills per-write growth/race); `session-start.sh:196-208` cap STALE/DECAY lists to top 20. · tok 0
**A21.** Small dedup/label fixes `SKILL.md:74,534`. · tok −30
**A22.** **Scrub baked-in proper nouns (distributed).** `references/crystallize-guide.md:13,103-144` hardcodes real names (line 13 "always crystallize 1:1 with <name>" primes one relationship); placeholder-ize + mark SCHEMA sample lines. · effort S · tok 0

---

## Keep — do NOT touch

- The deterministic hook layer: session-start health/staleness/decay/orphan snapshot; the start/stop concurrency lock with EXIT trap; post-write broken-wikilink detection; **especially the `pre-write.sh` freshness gate** — the correct prose→PreToolUse-additionalContext conversion, and the template for the snapshot/coverage fixes. No-jq portability, realpath containment, always-exit-0 non-blocking are all correct.
- `lint.py` deterministic checks: self-referential-source, missing-inline-provenance, stale `last_verified`, index auto-sort/backfill (`merge_sort_index` verified idempotent + non-destructive). Enforcement done right.
- The Orient gate's *shape* (short conditional) as the model for surviving prose guards — just drop the `(enforced)` label.
- The 3-layer data model (raw immutable / entities+concepts owned / SCHEMA governance), supersession-with-archive, and **confidence vs coverage as orthogonal axes** — both load-bearing; do not merge.
- The three named guard anchors (sub-skills cite them by name) — shorten prose, keep the names + source-completeness registry/3-state rule verbatim.
- Human-tone / overrides-session-hooks Pitfall lines (`:545-549`) — verbatim behavioral contract.

## Open decisions

1. **`lint.py:67-68 is_private()`** — confirmed dead code (0 call sites). Distributed → recommend deleting in the privacy-reconciliation commit (it's the ghost the drifted `private:true` prose hooks into).
2. **Rewrite all ~9 `wiki-search semantic_search` shorthands** to `view(action=...)` vs leave them disambiguated by one canonical mapping line. Low stakes.
3. **Recency-vs-authority micro-guard** (a dated primary figure outranks a fresh secondhand mention) — only worth ~+12 tokens IF the provenance-tier bullet is being edited anyway; otherwise drop (a 6th micro-guard worsens salience decay).
4. **`raw/inbox/` capture queue + lint age-warning** — genuinely useful capability gap, but +25 lines to `lint.py` + a schema concept. Recommend deferring until the micro-capture fast path (A13) is in use.
5. **Query-path falsification: inline vs pointer** — real tension; an inline reminder at the synthesis point is the kind that *does* fire. A19's conditional one-liner is a compromise; owner may prefer slightly longer inline.

---

*Next: on go, execute A1 (P0) first with its regression test, then P1 A2–A14, running the test suite after the hook/script changes. `SKILL.md` edits are interdependent — done sequentially by one editor with re-read verification, not parallelized.*
