---
title: "Persona: [Full Name]"
created: YYYY-MM-DD
updated: YYYY-MM-DD
type: persona
tags: [person, persona, internal]
sources: [entities/name.md, raw/internal/<tool>-channel-YYYY-MM-DD.md]
core_traits: []
language_patterns:
  sentence_length: short | medium | long | mixed
  capitalization: standard | lowercase | mixed
  punctuation: minimal | heavy | standard
tone_by_channel:        # one key per channel the person uses; examples below
  private_chat: ""        # e.g. Slack/Teams/Discord DM
  public_chat: ""         # e.g. Slack/Teams channel
  email_internal: ""
  email_external: ""
vocabulary_markers:
  hedging_level: low | medium | high
  humor_style: none | dry | casual
  signoff_patterns: []
code_switching: []
private: false
---

# Persona: [Full Name]

See also: [[name]] (person entity)

## Core Traits

3-5 sentences describing the person's overall communication character. Written
in natural prose, not bullets. Based only on observed source material.

## Communication by Channel

One section per communication channel this person actually uses and you have
source material for. Substitute the channels that apply to their stack — the
headers below (private chat, public chat, internal email, external email) are
common examples, not a fixed set. Drop channels with no data; add ones not listed
(team forum, ticket comments, video-call transcripts, etc.).

### Private chat (e.g. Slack/Teams/Discord DM)

- **Formality**: informal / formal / mixed
- **Sentence length**: short (1 line) / medium (2-3 lines) / long (paragraph)
- **Humor**: none / dry / casual
- **Sign-off**: none / "Thanks," / "Cheers," / other
- **Notes**: any distinctive patterns (emoji use, code-switching, response speed)

### Public chat channel

- **Formality**:
- **Sentence length**:
- **Humor**:
- **Sign-off**:
- **Notes**:

### Email (internal)

- **Formality**:
- **Sentence length**:
- **Humor**:
- **Sign-off**:
- **Notes**:

### Email (external / customer-facing)

- **Formality**:
- **Sentence length**:
- **Humor**:
- **Sign-off**:
- **Notes**:

## Cross-Channel Comparison

Columns = the channels you filled in above. Example layout:

| Dimension       | Private chat | Public chat | Email internal | Email external |
|-----------------|--------------|-------------|----------------|----------------|
| Formality       |              |             |                |                |
| Sentence length |              |             |                |                |
| Humor           |              |             |                |                |
| Sign-off        |              |             |                |                |
| Emoji use       |              |             |                |                |

## Vocabulary Markers

- **Hedging**: low / medium / high. Examples: [phrases if observed]
- **Humor style**: [description]
- **Recurring phrases**: [list if observed]
- **Code-switching**: [languages/registers, contexts]

## Source Notes

What data informed this analysis. Be explicit about which tiers have real
source material vs. inferred from limited data.

- Private chat: [X messages from <tool>:#channel, YYYY-MM to YYYY-MM]
- Email: [Y threads, date range]
- No data for: [channels with no source material]
