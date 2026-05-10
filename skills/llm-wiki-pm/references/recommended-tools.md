# Recommended Tools

Optional MCP servers that enhance the wiki when connected. The plugin bundles
only `wiki-search` (semantic + TF-IDF over your wiki). Everything below is
opt-in — install what you need.

Suggest these to users via Proactive Behavior #8 when their query would benefit.

---

## Research & Content (zero-setup, no API keys)

**RSS Feed Reader**
RSS/Atom parsing, digests, OPML import. 11 tools.
```
claude mcp add rss -- npx -y @0xquinto/rss-mcp
```
*When to suggest:* user wants to monitor competitor blogs or industry feeds.

**YouTube Transcript**
Extract transcripts from YouTube videos for wiki ingest.
```
claude mcp add youtube-transcript -- npx -y @kimtaeyoon83/mcp-server-youtube-transcript
```
*When to suggest:* user shares a YouTube URL to ingest.

**Web Reader**
URL → clean markdown. Faster than WebFetch for large pages.
```
claude mcp add read-website -- npx -y @just-every/mcp-read-website-fast
```
*When to suggest:* user ingests many web pages and WebFetch is too slow.

**Wayback Machine**
Internet Archive search, retrieve archived pages, compare snapshots.
```
claude mcp add wayback-machine -- npx -y mcp-wayback-machine
```
*When to suggest:* user wants historical versions of competitor pages.

**Web Search (DuckDuckGo/Bing/SearXNG)**
Multi-engine search, no API key. Alternative to built-in WebSearch.
```
claude mcp add web-search -- npx -y @zhafron/mcp-web-search
```
*When to suggest:* user needs search beyond Claude Code's built-in WebSearch.

**Wikipedia**
Article lookup, "on this day", image retrieval.
```
claude mcp add wikipedia -- npx -y @shelm/wikipedia-mcp-server
```
*When to suggest:* user researches a public entity and wants Wikipedia context.

**arXiv Papers**
Search, metadata, full-text paper reading, category listing.
```
claude mcp add arxiv -- npx -y @cyanheads/arxiv-mcp-server
```
*When to suggest:* user researches academic/AI topics.

**News**
Real-time news, event clustering, topic filtering.
```
claude mcp add news -- npx -y @newsmcp/server
```
*When to suggest:* user asks about recent events or industry news.

**App Store / Google Play**
App reviews, rankings, version history, similar apps. 20 tools.
```
claude mcp add app-insight -- npx -y @jeromyfu/app-insight-mcp
```
*When to suggest:* user researches mobile apps or competitor app ratings.

---

## Search (API key required)

**Brave Search MCP**
Independent search index. 2,000 free queries/month, then $3/1K.
```
npm install -g @anthropic/brave-search-mcp
# Set BRAVE_API_KEY from https://brave.com/search/api/
```
*When to suggest:* user needs deeper web search beyond DuckDuckGo/SearXNG.

**Exa MCP**
Semantic search — finds results keyword engines miss. $7/1K searches.
```
npm install -g exa-mcp-server
# Set EXA_API_KEY from https://exa.ai/
```
*When to suggest:* user wants "find companies doing X" or conceptual queries.

**Tavily MCP**
Long-context retrieval with research mode. Free tier available.
```
npm install -g @anthropic/tavily-mcp
# Set TAVILY_API_KEY from https://tavily.com/
```
*When to suggest:* user needs multi-step research with synthesized results.

---

## Content Capture

**Firecrawl MCP**
Crawl entire sites, structured extraction, clean markdown output.
```
npm install -g firecrawl-mcp-server
# Set FIRECRAWL_API_KEY from https://firecrawl.dev/
```
*When to suggest:* user wants to ingest an entire competitor site or docs section.

---

## People / Company Intelligence

**LinkedIn MCP (Apify)**
Profiles, companies, jobs, posts. $5/month free credits covers light usage.
```
# Configure via Apify MCP: https://apify.com/mcp/linkedin-mcp-server
# Set APIFY_TOKEN from https://console.apify.com/
```
*When to suggest:* user researches a person or company and wants LinkedIn data.

**SEC EDGAR MCP**
10-K, 10-Q, insider trading data. Free, no API key, but Python-based.
```
pip install sec-edgar-mcp
claude mcp add sec-edgar -- uvx sec-edgar-mcp
```
*When to suggest:* user asks about a public company's financials or filings.

---

## Analytics

**SimilarWeb MCP**
Competitor traffic estimates, audience demographics, referral sources.
```
# Official remote MCP: https://developers.similarweb.com/docs/similarweb-mcp
# Requires SimilarWeb API subscription
```
*When to suggest:* user asks "how much traffic does competitor X get?"

---

## Reviews

**G2 / Capterra (Apify)**
Software reviews, ratings, pricing, competitive comparisons.
```
# Configure via Apify: https://apify.com/sovereigntaylor/g2-reviews-scraper
# Set APIFY_TOKEN
```
*When to suggest:* user evaluates or compares SaaS products.

---

## Social Listening

**Twitter/X (Xpoz)**
Brand monitoring across Twitter, Instagram, TikTok, Reddit. Free npm SDK.
```
npm install -g @xpoz/sdk
# Free, no platform API keys needed
```
*When to suggest:* user wants social sentiment or brand mentions.

---

## Knowledge Management

**Readwise MCP**
Highlights, annotations, and read-later library integration.
```
# Official MCP: https://readwise.io/mcp
# Set READWISE_TOKEN from https://readwise.io/access_token
```
*When to suggest:* user mentions reading lists, highlights, or bookmarked articles.

---

## Grounded Search & Synthesis

**NotebookLM MCP**
Citation-backed Q&A, audio overview generation, notebook management via Google
NotebookLM. 35 tools. Requires Google account login via browser (one-time).
```
pip install notebooklm-mcp
claude mcp add notebooklm -- uvx notebooklm-mcp
```
*When to suggest:* user wants grounded answers with source citations, audio
summaries of research, or to manage NotebookLM notebooks from the CLI.
