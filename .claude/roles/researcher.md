---
role_id: researcher
display_name: Researcher / Analyst
aliases: [researcher, analyst, market researcher, product analyst, competitive analyst]
focus_tags: [competitive, ai, strategy, comparison, question, prediction]
preferred_output_format: file
crystallize_template: research-synthesis
surface_confidence_threshold: verified
---

# Role Pack: Researcher / Analyst

## Recommended Integrations

| Integration | Why it matters for you |
|---|---|
| qmd hybrid search | BM25 + vector + rerank — critical for finding nuanced thematic connections across sources |
| WebFetch | Ingest analyst reports, papers, and press directly into raw/articles/ and raw/papers/ |

## Suggested Agent Mode

`team` — delegate fetching to worker-source-fetcher, validation to worker-link-validator. Focus your session on synthesis and coverage audit.

## Notes

- **Higher confidence bar**: `surface_confidence_threshold: verified` means only well-sourced pages surface proactively — reduces noise during deep research
- **Output as file**: substantial syntheses go to `queries/<slug>/README.md` automatically rather than inline
- **Coverage audit is your friend**: run §12 regularly to find whitespace in the competitive landscape
- **Comparison pages**: prioritize `comparisons/` — they're the highest-value artifact for researchers
- After each major ingest, run §12 Coverage Audit to identify what's still missing
