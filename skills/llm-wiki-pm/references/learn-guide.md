# Learn Guide — full post-task capture procedure

The core skill's §13 stub gates the decision; this file is the full step-by-step.
Read it before running a Learn pass — it defines the dedup gate and the
classification buckets, and skipping it produces duplicate facts and unclassified
captures.

Trigger: user accepts Proactive Behavior #7 offer, or explicitly says "what did we
learn?", "capture learnings", "record what we found", "save what we discussed".

## ① Scan conversation

Review the current task or discussion. Identify uncaptured: facts, decisions,
entity updates, relationship changes, open questions, contradictions. Only
PM-domain content. Skip opinions without specifics, hypotheticals, and casual asides.

## ② Dedup against wiki

For each candidate learning, search existing pages (wiki-search `semantic_search`
preferred, grep fallback). Drop anything already recorded. If a fact exists but
needs updating (newer info), mark it as an update rather than a new capture.

## ③ Classify

Bucket each surviving learning:
- `entity-update`: new fact about an existing entity → update that page
- `new-entity`: entity discussed with 3+ attributes but no page → create
- `concept-update`: new insight about an existing concept → update
- `decision`: a decision was made → create/update decision-tagged page
- `open-question`: factual question raised but unanswered → log under queries/
- `contradiction`: conflicts with existing wiki content → flag with both claims

## ④ Propose changes

Show user a compact list before writing anything:

```
Learnings from this task:
• Update [[entity-slug]] — added role change to VP Engineering
• Create entities/new-company.md — 4 attributes discussed
• Log decision: switched to vendor X for auth
• Open question: what's competitor Y's enterprise pricing?
```

If 10+ changes, get explicit sign-off per pitfalls.

## ⑤ Execute

On approval, apply changes using existing flows:
- Entity/concept updates: use §4 Update (show diffs, sweep stale variants)
- New entities: use §2 Ingest conventions (frontmatter, cross-refs, provenance)
- Decisions: use the Decision Journaling format (Proactive Behavior §5)
- Open questions: use the Open Question Backlog format (Proactive Behavior §4)
- Contradictions: surface both claims with dates and sources per pitfalls
- All pages: min 2 outbound `[[links]]`, inline provenance for non-obvious claims,
  `coverage:` and `gaps:` fields set

## ⑥ Log

Append to `log.md`:

```
## [YYYY-MM-DD] learn | <task-summary>
- Updated: entities/foo.md (added Q3 strategy shift)
- Created: entities/new-company.md
- Logged decision: auth-vendor-switch
- Open question: competitor-y-pricing
```

Single-line form: `## [YYYY-MM-DD] learn | <task-summary> | captured: N | updated: N | new: N`
