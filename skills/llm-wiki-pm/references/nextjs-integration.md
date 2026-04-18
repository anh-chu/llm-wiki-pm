# Next.js / Node Integration

Embed the wiki graph inside your own Next.js app. Server parses the markdown
vault → graph JSON → client renders force-directed graph with click-through
to page content.

Assumes Next.js 14+ App Router. Adjust for Pages Router as needed.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  Next.js app                                                 │
│                                                              │
│  ┌────────────────┐    ┌─────────────────┐    ┌───────────┐ │
│  │ Wiki filesystem│───▶│ lib/wiki-graph  │───▶│ API route │ │
│  │  /wikis/<id>/  │    │  (parse + auth) │    │ /api/...  │ │
│  └────────────────┘    └─────────────────┘    └─────┬─────┘ │
│                                                     │       │
│                                          ┌──────────▼─────┐ │
│                                          │ <WikiGraph />  │ │
│                                          │ (client, R3D)  │ │
│                                          └────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

Server does:
- Walk wiki dir
- Parse frontmatter + `[[wikilinks]]`
- Filter `private: true` based on caller's auth
- Emit graph JSON (nodes + edges)

Client does:
- Fetch graph JSON
- Render interactive graph
- Drill into page content on node click

## Library Choice

| Library                        | Rendering | Nodes | Best for                                        |
| --------------------------------| -----------| -------| -------------------------------------------------|
| **react-force-graph-2d**       | Canvas    | ~5k   | Dynamic force layout, fast, recommended default |
| **react-force-graph-3d**       | WebGL     | ~10k  | 3D option, same API                             |
| **@xyflow/react** (React Flow) | SVG       | ~500  | Curated layouts, pretty, editable               |
| **react-cytoscapejs**          | Canvas    | ~10k  | Advanced graph algorithms, heavier              |
| **react-sigma**                | WebGL     | ~50k  | Large wikis, performance                        |

**Recommendation**: `react-force-graph-2d` for MVP. Switch to `react-sigma`
if you have multi-tenant wikis with 1000+ pages each.

## Install

```bash
npm install react-force-graph-2d gray-matter glob remark remark-wiki-link unified
# dev types
npm install -D @types/node
```

## Server: Graph Parser

`lib/wiki-graph.ts`:

```ts
import { readFile } from "node:fs/promises";
import { join, relative } from "node:path";
import { glob } from "glob";
import matter from "gray-matter";

const WIKILINK_RE = /\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]/g;
const WIKI_DIRS = ["entities", "concepts", "comparisons", "queries"] as const;

export type GraphNode = {
  id: string;                    // slug
  path: string;                  // relative wiki path
  title: string;
  type: string;                  // entity | concept | comparison | query | summary
  tags: string[];
  updated: string;
  private: boolean;
  superseded: boolean;
  degree: number;                // inbound + outbound count
};

export type GraphEdge = {
  source: string;                // slug
  target: string;                // slug
  kind: "wikilink" | "supersedes";
};

export type WikiGraph = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

export type BuildOpts = {
  wikiPath: string;
  includePrivate?: boolean;      // caller-authorized to see private pages?
};

export async function buildGraph(opts: BuildOpts): Promise<WikiGraph> {
  const { wikiPath, includePrivate = false } = opts;

  const files: string[] = [];
  for (const d of WIKI_DIRS) {
    const hits = await glob(`${d}/**/*.md`, { cwd: wikiPath });
    files.push(...hits);
  }

  type Raw = {
    slug: string;
    path: string;
    frontmatter: Record<string, any>;
    links: string[];
  };

  const raws: Raw[] = [];
  for (const rel of files) {
    if (rel.includes("/lint-") || rel.endsWith(".canvas")) continue;
    const full = join(wikiPath, rel);
    const text = await readFile(full, "utf8");
    const { data, content } = matter(text);

    const links: string[] = [];
    for (const m of content.matchAll(WIKILINK_RE)) {
      links.push(m[1].trim());
    }

    const slug = rel.split("/").pop()!.replace(/\.md$/, "");
    raws.push({ slug, path: rel, frontmatter: data, links });
  }

  // Filter private if caller not authorized
  const visible = raws.filter((r) => includePrivate || r.frontmatter.private !== true);
  const visibleSlugs = new Set(visible.map((r) => r.slug));

  // Build nodes
  const degree = new Map<string, number>();
  const edges: GraphEdge[] = [];

  for (const r of visible) {
    for (const target of r.links) {
      if (!visibleSlugs.has(target)) continue;      // skip broken / hidden
      if (target === r.slug) continue;              // skip self-links
      edges.push({ source: r.slug, target, kind: "wikilink" });
      degree.set(r.slug, (degree.get(r.slug) ?? 0) + 1);
      degree.set(target, (degree.get(target) ?? 0) + 1);
    }

    // Supersession edges
    const supersedes = r.frontmatter.supersedes;
    if (Array.isArray(supersedes)) {
      for (const old of supersedes) {
        if (visibleSlugs.has(old)) {
          edges.push({ source: r.slug, target: old, kind: "supersedes" });
        }
      }
    }
  }

  const nodes: GraphNode[] = visible.map((r) => ({
    id: r.slug,
    path: r.path,
    title: r.frontmatter.title ?? r.slug,
    type: r.frontmatter.type ?? "entity",
    tags: Array.isArray(r.frontmatter.tags) ? r.frontmatter.tags : [],
    updated: r.frontmatter.updated ?? "",
    private: r.frontmatter.private === true,
    superseded: r.frontmatter.superseded_by != null,
    degree: degree.get(r.slug) ?? 0,
  }));

  return { nodes, edges };
}

export async function getPageContent(
  wikiPath: string,
  slug: string,
  includePrivate = false,
): Promise<{ frontmatter: Record<string, any>; body: string } | null> {
  // Find the file by slug across wiki dirs
  for (const d of WIKI_DIRS) {
    const hits = await glob(`${d}/**/${slug}.md`, { cwd: wikiPath });
    if (hits.length === 0) continue;
    const full = join(wikiPath, hits[0]);
    const text = await readFile(full, "utf8");
    const { data, content } = matter(text);
    if (data.private === true && !includePrivate) return null;
    return { frontmatter: data, body: content };
  }
  return null;
}

export async function getBacklinks(
  wikiPath: string,
  slug: string,
  includePrivate = false,
): Promise<GraphNode[]> {
  const graph = await buildGraph({ wikiPath, includePrivate });
  const incoming = graph.edges
    .filter((e) => e.target === slug)
    .map((e) => e.source);
  return graph.nodes.filter((n) => incoming.includes(n.id));
}
```

## API Routes

`app/api/wikis/[id]/graph/route.ts`:

```ts
import { NextRequest, NextResponse } from "next/server";
import { buildGraph } from "@/lib/wiki-graph";
import { authorize } from "@/lib/auth";
import { wikiPathFor } from "@/lib/wikis";

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } },
) {
  const user = await authorize(req);
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const wikiPath = await wikiPathFor(params.id);
  if (!wikiPath) return NextResponse.json({ error: "not found" }, { status: 404 });

  const canViewPrivate = await user.ownsWiki(params.id);
  const graph = await buildGraph({ wikiPath, includePrivate: canViewPrivate });

  return NextResponse.json(graph, {
    headers: {
      "Cache-Control": "private, max-age=30",
    },
  });
}
```

`app/api/wikis/[id]/pages/[slug]/route.ts`:

```ts
import { NextRequest, NextResponse } from "next/server";
import { getPageContent, getBacklinks } from "@/lib/wiki-graph";
import { authorize } from "@/lib/auth";
import { wikiPathFor } from "@/lib/wikis";

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string; slug: string } },
) {
  const user = await authorize(req);
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });

  const wikiPath = await wikiPathFor(params.id);
  if (!wikiPath) return NextResponse.json({ error: "not found" }, { status: 404 });

  const canViewPrivate = await user.ownsWiki(params.id);
  const page = await getPageContent(wikiPath, params.slug, canViewPrivate);
  if (!page) return NextResponse.json({ error: "not found" }, { status: 404 });

  const backlinks = await getBacklinks(wikiPath, params.slug, canViewPrivate);

  return NextResponse.json({ ...page, backlinks });
}
```

## Client: Graph Component

`components/WikiGraph.tsx`:

```tsx
"use client";

import { useEffect, useRef, useState } from "react";
import dynamic from "next/dynamic";
import type { WikiGraph, GraphNode } from "@/lib/wiki-graph";

// force-graph needs window; dynamic import with ssr:false
const ForceGraph2D = dynamic(() => import("react-force-graph-2d"), {
  ssr: false,
});

const TYPE_COLORS: Record<string, string> = {
  entity:     "#60a5fa",   // blue
  concept:    "#34d399",   // green
  comparison: "#f59e0b",   // amber
  query:      "#a78bfa",   // purple
  summary:    "#f472b6",   // pink
};

export function WikiGraph({
  wikiId,
  onNodeClick,
  height = 600,
}: {
  wikiId: string;
  onNodeClick?: (node: GraphNode) => void;
  height?: number;
}) {
  const [graph, setGraph] = useState<WikiGraph | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`/api/wikis/${wikiId}/graph`)
      .then((r) => r.json())
      .then((g) => {
        setGraph(g);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [wikiId]);

  if (loading) return <div style={{ height }}>Loading graph…</div>;
  if (!graph) return <div style={{ height }}>Failed to load graph.</div>;

  // react-force-graph mutates the data shape; pass a cloned version
  const data = {
    nodes: graph.nodes.map((n) => ({ ...n })),
    links: graph.edges.map((e) => ({ ...e })),
  };

  return (
    <ForceGraph2D
      graphData={data}
      height={height}
      nodeLabel={(n: any) => `${n.title}\n${n.tags.join(", ")}`}
      nodeColor={(n: any) => TYPE_COLORS[n.type] ?? "#999"}
      nodeVal={(n: any) => Math.max(2, Math.log(1 + n.degree) * 3)}
      linkColor={(l: any) => (l.kind === "supersedes" ? "#ef4444" : "#444")}
      linkDirectionalArrowLength={(l: any) => (l.kind === "supersedes" ? 4 : 0)}
      onNodeClick={(n: any) => onNodeClick?.(n)}
      cooldownTicks={100}
      enableNodeDrag
    />
  );
}
```

## Page View with Backlinks

`app/wikis/[id]/page.tsx`:

```tsx
"use client";

import { useState } from "react";
import { WikiGraph } from "@/components/WikiGraph";
import { PageDetail } from "@/components/PageDetail";
import type { GraphNode } from "@/lib/wiki-graph";

export default function WikiPage({ params }: { params: { id: string } }) {
  const [selected, setSelected] = useState<GraphNode | null>(null);

  return (
    <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16 }}>
      <WikiGraph
        wikiId={params.id}
        onNodeClick={(n) => setSelected(n)}
        height={720}
      />
      {selected && (
        <PageDetail wikiId={params.id} slug={selected.id} />
      )}
    </div>
  );
}
```

`components/PageDetail.tsx`:

```tsx
"use client";

import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type PageData = {
  frontmatter: Record<string, any>;
  body: string;
  backlinks: Array<{ id: string; title: string; type: string }>;
};

export function PageDetail({ wikiId, slug }: { wikiId: string; slug: string }) {
  const [page, setPage] = useState<PageData | null>(null);

  useEffect(() => {
    fetch(`/api/wikis/${wikiId}/pages/${slug}`)
      .then((r) => r.json())
      .then(setPage);
  }, [wikiId, slug]);

  if (!page) return <div>Loading…</div>;

  return (
    <aside>
      <h2>{page.frontmatter.title}</h2>
      <div style={{ fontSize: 12, color: "#888" }}>
        {page.frontmatter.type} · updated {page.frontmatter.updated}
      </div>

      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Render [[wikilinks]] as internal links
          // pre-process body or use remark-wiki-link plugin
        }}
      >
        {page.body}
      </ReactMarkdown>

      <h3>Backlinks</h3>
      <ul>
        {page.backlinks.map((b) => (
          <li key={b.id}>
            <a href={`/wikis/${wikiId}?slug=${b.id}`}>{b.title}</a>
            <span style={{ color: "#888" }}> ({b.type})</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
```

## Rendering Wikilinks in Markdown

`[[slug]]` syntax isn't valid markdown. Two options:

### Option A: Pre-process before ReactMarkdown

```ts
function preprocessWikilinks(body: string, wikiId: string): string {
  return body.replace(
    /\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]/g,
    (_, slug, alias) => `[${alias ?? slug}](/wikis/${wikiId}?slug=${slug})`,
  );
}
```

Pass the transformed body to `<ReactMarkdown>`.

### Option B: remark plugin

```bash
npm install remark-wiki-link
```

```ts
import remarkWikiLink from "remark-wiki-link";

<ReactMarkdown
  remarkPlugins={[
    remarkGfm,
    [remarkWikiLink, {
      pageResolver: (name: string) => [name],
      hrefTemplate: (permalink: string) =>
        `/wikis/${wikiId}?slug=${permalink}`,
    }],
  ]}
>
  {page.body}
</ReactMarkdown>
```

## Performance

For wikis under ~500 pages, parse-on-request is fine. At scale:

### Server-side cache

```ts
// lib/wiki-graph-cache.ts
const cache = new Map<string, { graph: WikiGraph; ts: number }>();
const TTL_MS = 60_000;

export async function buildGraphCached(opts: BuildOpts): Promise<WikiGraph> {
  const key = `${opts.wikiPath}:${opts.includePrivate}`;
  const hit = cache.get(key);
  if (hit && Date.now() - hit.ts < TTL_MS) return hit.graph;
  const graph = await buildGraph(opts);
  cache.set(key, { graph, ts: Date.now() });
  return graph;
}
```

Invalidate on wiki writes (ingest/update/lint hooks).

### Precompute + persist

For multi-tenant at scale, run graph parsing as a background job after any
wiki write → persist to Postgres/Redis → API route just reads JSON.

Schema:

```sql
CREATE TABLE wiki_graphs (
  wiki_id TEXT PRIMARY KEY,
  graph_json JSONB NOT NULL,
  graph_public_json JSONB NOT NULL,     -- excludes private nodes
  updated_at TIMESTAMPTZ NOT NULL
);
```

API route picks the right column based on auth. O(1) serve.

### Pagination for huge graphs

At 5k+ nodes, filter before sending:

- By tag: `?tag=competitive`
- By type: `?type=entity`
- By degree: only show top-N connected nodes
- By subgraph: start from a node, BFS 2 hops out

Client then fetches subgraphs on demand as user navigates.

## Privacy: server-side enforcement

Critical for Scenario 2:

1. **Filter at `buildGraph`**: private nodes + edges to/from them are
   removed before the JSON ever leaves the server
2. **Never trust query params**: compute `includePrivate` from auth,
   not from client input
3. **Sanitize error messages**: "page not found" regardless of whether
   the page exists but is private, or doesn't exist at all

## Real-time updates

Options:

### Polling

Client refetches graph every N seconds. Simplest.

### Server-sent events

```ts
// app/api/wikis/[id]/graph/stream/route.ts
export async function GET(req: NextRequest, { params }) {
  const stream = new ReadableStream({
    async start(controller) {
      const watcher = watchWiki(wikiPathFor(params.id));
      for await (const _ of watcher) {
        const graph = await buildGraph({ wikiPath, includePrivate: true });
        controller.enqueue(`data: ${JSON.stringify(graph)}\n\n`);
      }
    },
  });
  return new Response(stream, {
    headers: { "Content-Type": "text/event-stream" },
  });
}
```

Use `chokidar` for file watching. Rate-limit to avoid flood on bulk ingests.

### WebSocket with Y.js for collaborative editing

If multiple users edit the same wiki simultaneously, reach for Y.js /
Liveblocks. Out of scope for read-only graph.

## Styling Recommendations

- Node color by `type` (entity/concept/comparison/query)
- Node size by `degree` (popular pages bigger)
- Edge color: gray for wikilinks, red for supersession
- Edge thickness: constant or by link count (if two pages link each other)
- Hover tooltip: title + tags + updated date
- Click: open side panel with page body + backlinks
- Legend: small box showing type → color mapping

## Integration with qmd search

Add a search box above the graph:

```tsx
const [filter, setFilter] = useState("");

// Debounced qmd query via your API
useEffect(() => {
  if (!filter) return setHighlightedIds(new Set());
  fetch(`/api/wikis/${wikiId}/search?q=${encodeURIComponent(filter)}`)
    .then((r) => r.json())
    .then((hits) => setHighlightedIds(new Set(hits.map((h) => h.id))));
}, [filter]);
```

Pass `highlightedIds` to the graph, nodes not in the set render at low
opacity, nodes in the set pulse or glow. User searches → graph highlights
matching subgraph.

## Full MVP Checklist

- [ ] `lib/wiki-graph.ts`, parser, backlinks, privacy filter
- [ ] `app/api/wikis/[id]/graph/route.ts`, graph JSON endpoint
- [ ] `app/api/wikis/[id]/pages/[slug]/route.ts`, page + backlinks
- [ ] `components/WikiGraph.tsx`, force-graph component
- [ ] `components/PageDetail.tsx`, side panel with markdown + backlinks
- [ ] `app/wikis/[id]/page.tsx`, split-pane layout
- [ ] Wikilink preprocessing (Option A or B above)
- [ ] Auth wiring (your existing system)
- [ ] Cache layer if > 500 pages or > 10 users

## Open-source reference

Karpathy's own example of this pattern visualized lives in community projects
like [Quartz](https://github.com/jackyzha0/quartz). Good code to read even
if you don't use it directly, see their `quartz/components/Graph.tsx` for
how they handle force-graph config, and `quartz/plugins/transformers/links.ts`
for their wikilink parser. Similar shape to what's above, MIT licensed.
