
# BAAHM/P

Default Kindship stack for agent-built web software.

## Version Baseline

| Dependency | Minimum | Notes |
|-----------|---------|-------|
| Node.js | 22.12.0 | Required by Astro 6; even-numbered versions only |
| Bun | Current stable | Primary runtime; check `bun --version` |
| Astro | 6.x | Content Layer API, `src/content.config.ts`, Zod 4 via `astro/zod` |
| htmx | 2.0.8 | Pin to exact version; see loading guidance below |
| Alpine.js | 3.x | Loaded automatically via `@astrojs/alpinejs` |
| Drizzle ORM | Latest | With `drizzle-kit` for migrations |
| PostgreSQL | 15+ | Any modern Postgres; 16+ preferred |

---

## 1. When to Use

Use this skill for any new web application, site, dashboard, portal, tool, or user-facing project unless the user explicitly requests a different stack. This includes:

- Content sites, blogs, documentation
- CRUD applications, admin panels
- Dashboards and internal tools
- Landing pages, marketing sites
- Forms-heavy applications
- Multi-page applications with server-driven interactions

## 2. When NOT to Use

Do not use this skill when:

- The user explicitly asks for React, Next.js, SvelteKit, Vue, Nuxt, or another framework
- The product is a mobile app (native or hybrid)
- The product is primarily a real-time collaborative editor (Google Docs-style)
- The product is canvas-heavy, drag-heavy, or WebGL-based
- The product is an SPA where most UI state is client-owned and rarely touches the server
- The product requires offline-first with complex client-side sync

If a substantial share of the project's interactivity depends on escape hatches, BAAHM/P may not be the right default. Flag it to the user and suggest an alternative.

## 3. Core Rules

These are non-negotiable. Follow them in every BAAHM/P project.

### Architecture

- Start in Astro **static mode** (the default, no adapter needed). Opt specific pages/endpoints into SSR with `export const prerender = false`. Add `@astrojs/node` and `output: 'server'` only when the majority of pages need on-demand rendering.
- Alpine.js owns **ephemeral client state**: toggles, modals, tabs, dropdowns, client-side filtering, animations. Anything that does NOT need the server.
- HTMX owns **server interactions via HTML**: form submissions, data fetching, search, pagination, infinite scroll. Anything that hits an endpoint and swaps DOM content.
- **Alpine must never become the source of truth for server-owned data.** Alpine may decorate or react to HTMX swaps, but canonical data lives in Postgres and arrives via HTMX.
- Markdown owns **content at rest**: pages, docs, changelogs, mission journals. Never use Markdown for mutable application state.
- PostgreSQL owns **canonical application state**: user data, mission state, relational data, agent memory.

### HTMX vs Astro Actions

Use the right tool for each interaction:

- **HTMX endpoints** → for UI flows that swap HTML fragments into the page (search results, CRUD lists, modals, tabs, inline editing). Return `text/html`.
- **Astro Actions** → for validated mutations or typed client-server calls that do not naturally return HTML fragments (API operations, background tasks, form submissions where you want Zod validation and type-safe return values). JSON is fine here.
- **JSON API endpoints** → only for external integrations, machine clients, webhooks, or mobile consumers.

### Code Style

- Keep logic local. No file-hopping to understand what a component does.
- No separate REST API that returns JSON for HTMX to consume. HTMX endpoints ARE the interface — they return HTML.
- Do not install React, Vue, Svelte, or Solid unless the user explicitly requests island interactivity Alpine cannot handle (rich text editing, complex drag-and-drop).
- Do not install an ORM other than Drizzle. No Prisma, no Sequelize.
- If `x-data` exceeds ~5 properties, extract to a named Alpine component via `Alpine.data()`. Otherwise, keep it inline.
- No `fetch()` calls inside Alpine `x-data`. That's HTMX's job.
- If client-side JavaScript grows beyond a small local snippet — roughly 20–30 lines or more than one concern — extract it into a named Alpine component or rethink the interaction.

## 4. Default Decisions

Agents get stuck on small choices. Use these defaults unless the user specifies otherwise:

| Decision | Default |
|----------|---------|
| IDs | `uuid` for external/user-facing entities; `serial` for internal/admin-only tables |
| Timestamps | `createdAt`, `updatedAt`, always UTC, always `timestamp` with `withTimezone: true` |
| Table naming | **Plural** (`users`, `posts`, `missions`) |
| Deletion | Soft delete via `deletedAt` timestamp; hard delete only when explicitly requested |
| Content format | `.md` first; `.mdx` only when embedded components are necessary |
| Forms | Native HTML `<form>` first, then enhance with HTMX attributes |
| Auth | Cookie/session-based; prefer Better Auth, or a custom session implementation when the auth surface is simple |
| Pagination | Cursor-based for user-facing feeds; offset-based for admin tables |
| Styling | Global CSS in `src/styles/global.css`; use CSS custom properties for theming |
| Package manager | Bun (never npm, yarn, or pnpm) |
| Lockfile | `bun.lock` (Bun's current default text format) |
| Config | No `bunfig.toml` unless explicitly needed — Bun works out of the box |

## 5. Project Structure

```
project-root/
├── astro.config.mjs
├── drizzle.config.ts
├── package.json
├── .env.example
├── src/
│   ├── content.config.ts          # Content collection schemas (Astro 5+ location)
│   ├── layouts/
│   │   └── Base.astro             # Base HTML shell (HTMX loaded here; Alpine injected by integration)
│   ├── pages/
│   │   ├── index.astro
│   │   └── api/                   # HTMX + API endpoints (file-based routing)
│   ├── components/
│   │   ├── [Name].astro           # Server-rendered Astro components
│   │   └── interactive/           # Alpine-enhanced components
│   ├── content/
│   │   └── [collection]/          # Markdown content files
│   │       └── *.md
│   ├── db/
│   │   ├── client.ts              # Drizzle + postgres connection
│   │   ├── schema.ts              # Table definitions (source of truth)
│   │   └── migrations/            # Generated SQL migrations
│   ├── lib/                       # Shared utilities
│   └── styles/
│       └── global.css
├── public/
│   └── htmx.min.js               # Self-hosted htmx (production default)
└── schemas/                       # Optional JSON Schema validation
```

### Naming Conventions

- Pages: `kebab-case.astro` — routes map to URLs
- Components: `PascalCase.astro`
- API endpoints: follow Astro's file-based routing in `src/pages/`; do not impose Express-style conventions
- Content: `kebab-case.md` with validated frontmatter
- Database tables: plural, snake_case in Postgres, camelCase in Drizzle schema

## 6. Layer Reference

### Bun

Bun is runtime, package manager, test runner, and bundler. No additional tooling required.

```bash
bun create astro@latest project-name
bun add alpinejs htmx.org drizzle-orm postgres
bun add -d drizzle-kit
# Optional: bun add -d @types/alpinejs  (for TypeScript type hints in Alpine components)
bun run dev        # development
bun test           # testing
bun run build      # production build
```

### Astro

Astro has two configuration postures. Use the one that matches the project.

**Static baseline** (default — no adapter, no server output):
```javascript
// astro.config.mjs — static sites, content sites, marketing pages
import { defineConfig } from 'astro/config';
import alpinejs from '@astrojs/alpinejs';

export default defineConfig({
  integrations: [alpinejs()],
});
```

**Server-capable variant** (when SSR, actions, or sessions are needed):
```javascript
// astro.config.mjs — apps with dynamic routes, auth, database-backed pages
import { defineConfig } from 'astro/config';
import node from '@astrojs/node';
import alpinejs from '@astrojs/alpinejs';

export default defineConfig({
  output: 'server',
  adapter: node({ mode: 'standalone' }),
  integrations: [alpinejs()],
});
```

Add `@astrojs/node` and `output: 'server'` only when the project actually needs SSR routes, Astro Actions, sessions, or other server features. For projects that only need a few dynamic endpoints, stay static and opt individual routes out of prerendering:

```astro
---
export const prerender = false;
// This endpoint renders on-demand
---
```

Key rules:
- Frontmatter (`---` fences) runs on the server
- Below the frontmatter is HTML with `{expressions}`
- Use `Astro.props` for component inputs, `Astro.request`/`Astro.url` for request context
- Prefer `.astro` components over framework components — they render to zero client JS

### Alpine.js

The `@astrojs/alpinejs` integration injects Alpine automatically on every page. **Do not add a separate `<script>` tag for Alpine** — it is already loaded by the integration.

Alpine lives in HTML attributes. No separate files, no build step.

```html
<div x-data="{ open: false, count: 0 }">
  <div x-show="open" x-transition>Content</div>
  <button @click="open = !open">Toggle</button>
  <button @click="count++">Count: <span x-text="count"></span></button>
  <input x-model="search" placeholder="Filter..." />
</div>
```

Extract to named component when `x-data` grows beyond ~5 properties:
```html
<div x-data="dropdown()"> ... </div>
<script>
document.addEventListener('alpine:init', () => {
  Alpine.data('dropdown', () => ({
    open: false,
    selected: null,
    toggle() { this.open = !this.open },
    select(item) { this.selected = item; this.open = false },
  }));
});
</script>
```

### HTMX

**Loading htmx**: Self-host in production. Download `htmx.min.js` v2.0.8 into `public/` and reference it from the base layout. For development or prototyping, a pinned CDN URL with SRI is acceptable:

```html
<!-- Production: self-hosted (preferred) -->
<script src="/htmx.min.js"></script>

<!-- Development / prototyping: pinned CDN with integrity -->
<script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js"
  integrity="sha384-/TgkGk7p307TH7EXJDuUlgG3Ce1UVolAOFopFekQkkXihi5u/6OCvVKyz1W+idaz"
  crossorigin="anonymous"></script>
```

**Base layout** (`src/layouts/Base.astro`):
```astro
---
interface Props {
  title: string;
}
const { title } = Astro.props;
---
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title}</title>
  <!-- Alpine is injected automatically by @astrojs/alpinejs — do NOT add a script tag for it -->
  <script src="/htmx.min.js"></script>
  <link rel="stylesheet" href="/styles/global.css" />
</head>
<body>
  <slot />
</body>
</html>
```

HTMX makes server requests and swaps HTML fragments via attributes:

```html
<!-- Load on page render -->
<div hx-get="/api/users" hx-trigger="load" hx-swap="innerHTML">Loading...</div>

<!-- Form submission -->
<form hx-post="/api/users" hx-target="#user-list" hx-swap="afterbegin">
  <input name="name" required />
  <button type="submit">Add</button>
</form>

<!-- Debounced search -->
<input type="search" name="q"
  hx-get="/api/search"
  hx-trigger="input changed delay:300ms"
  hx-target="#results" />

<!-- Delete with confirmation -->
<button hx-delete="/api/users/123" hx-confirm="Delete?" hx-target="closest tr" hx-swap="outerHTML">
  Delete
</button>
```

**HTMX endpoint** (Astro API route):
```typescript
// src/pages/api/users.ts
import type { APIRoute } from 'astro';
import { db } from '../../db/client';
import { users } from '../../db/schema';

export const prerender = false;

export const GET: APIRoute = async ({ url }) => {
  const results = await db.select().from(users);
  const html = results.map(u =>
    `<tr id="user-${u.id}"><td>${u.name}</td><td>${u.email}</td></tr>`
  ).join('');
  return new Response(html, { headers: { 'Content-Type': 'text/html' } });
};

export const POST: APIRoute = async ({ request }) => {
  const data = await request.formData();
  const [user] = await db.insert(users)
    .values({ name: data.get('name') as string })
    .returning();
  return new Response(
    `<tr id="user-${user.id}"><td>${user.name}</td></tr>`,
    { headers: { 'Content-Type': 'text/html' } }
  );
};
```

### Markdown (Content Collections)

Use Astro's Content Layer API. Config lives in `src/content.config.ts` (not the legacy `src/content/config.ts`). Import `z` from `astro/zod`, not from `zod` directly.

```typescript
// src/content.config.ts
import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const blog = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/blog' }),
  schema: z.object({
    title: z.string(),
    date: z.date(),
    draft: z.boolean().default(false),
    tags: z.array(z.string()).default([]),
  }),
});

export const collections = { blog };
```

Query in pages:
```astro
---
import { getCollection } from 'astro:content';
const posts = await getCollection('blog', ({ data }) => !data.draft);
---
{posts.map(post => (
  <article>
    <h2><a href={`/blog/${post.id}`}>{post.data.title}</a></h2>
  </article>
))}
```

### PostgreSQL (via Drizzle)

**Connection** (`src/db/client.ts`):
```typescript
import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema';

const client = postgres(import.meta.env.DATABASE_URL);
export const db = drizzle(client, { schema });
```

**Schema** (`src/db/schema.ts`):
```typescript
import { pgTable, uuid, text, timestamp, jsonb, boolean } from 'drizzle-orm/pg-core';
import { sql } from 'drizzle-orm';

export const users = pgTable('users', {
  id: uuid('id').primaryKey().default(sql`gen_random_uuid()`),
  name: text('name').notNull(),
  email: text('email').notNull().unique(),
  meta: jsonb('meta').$type<Record<string, unknown>>().default({}),
  active: boolean('active').default(true),
  createdAt: timestamp('created_at', { withTimezone: true }).defaultNow().notNull(),
  updatedAt: timestamp('updated_at', { withTimezone: true })
    .defaultNow()
    .notNull()
    .$onUpdate(() => new Date()),
  deletedAt: timestamp('deleted_at', { withTimezone: true }),
});
```

Note: `defaultNow()` only sets the value on INSERT. Use `$onUpdate(() => new Date())` on `updatedAt` so Drizzle sets it on every UPDATE via the ORM. Alternatively, use a database-level trigger if you want the database to own it.

**Migrations**:
```bash
bunx drizzle-kit generate    # generate migration from schema changes
bunx drizzle-kit migrate     # apply migrations
bunx drizzle-kit studio      # visual inspection
```

Every schema change must go through generate → review → migrate. Never modify the database directly.

## 7. Common Patterns

### Alpine + HTMX Together (Search)

Alpine owns input state. HTMX owns the server call. They cooperate through the DOM:

```html
<div x-data="{ query: '' }">
  <input x-model="query" name="q"
    hx-get="/api/search" hx-trigger="input changed delay:300ms"
    hx-target="#results" hx-indicator="#spinner"
    placeholder="Search..." />
  <span id="spinner" class="htmx-indicator">Searching...</span>
  <div id="results"></div>
</div>
```

### Modal with Server Content

Alpine controls visibility. HTMX loads the form:

```html
<div x-data="{ open: false }">
  <button @click="open = true"
    hx-get="/api/users/42/edit" hx-target="#modal-body">
    Edit
  </button>
  <div x-show="open" x-transition @click.outside="open = false" class="modal-overlay">
    <div class="modal" @click.stop>
      <div id="modal-body">Loading...</div>
      <button @click="open = false">Close</button>
    </div>
  </div>
</div>
```

### Tabs (No Page Load)

```html
<div x-data="{ tab: 'overview' }">
  <nav>
    <button @click="tab = 'overview'" :class="tab === 'overview' && 'active'"
      hx-get="/api/project/overview" hx-target="#tab-content">Overview</button>
    <button @click="tab = 'settings'" :class="tab === 'settings' && 'active'"
      hx-get="/api/project/settings" hx-target="#tab-content">Settings</button>
  </nav>
  <div id="tab-content"></div>
</div>
```

## 8. Escape Hatches

Extend when needed — don't replace the stack:

| Need | Extension |
|------|-----------|
| Rich text editing | Tiptap or ProseMirror as Astro island |
| Real-time / WebSocket | Bun's native WebSocket via `Bun.serve()` |
| Complex drag-and-drop | SortableJS (CDN, init with Alpine) |
| Data visualization | D3.js or Chart.js as Astro island |
| Auth | Better Auth (Astro middleware), or custom cookie/session implementation |
| File uploads | tus protocol or presigned URLs |
| Heavy client state | Nanostores (tiny, works with Astro) |

## 9. Agent Output Contract

When using this skill to build a project, produce these deliverables:

1. **Project tree** — directory structure matching Section 5
2. **Package install commands** — `bun create` + `bun add` for all dependencies
3. **Config files** — `astro.config.mjs` (static or server variant as appropriate), `drizzle.config.ts`, `.env.example`
4. **Base layout** — `src/layouts/Base.astro` with HTMX loaded via `<script>` and Alpine injected by the `@astrojs/alpinejs` integration (no manual Alpine script tag)
5. **First page** — `src/pages/index.astro` rendering content
6. **One interactive HTMX flow** — a form, search, or CRUD interaction with a working API endpoint returning HTML
7. **Database schema + migration** — at least one table in `src/db/schema.ts` with a generated migration
8. **Content collection** — `src/content.config.ts` with at least one collection if the project includes content
9. **Run/build/deploy commands** — documented in a README or presented to the user

## 10. Deployment

**Required env**:
```
DATABASE_URL=postgresql://user:pass@host:5432/dbname
```

**Preferred targets** (Kindship infra):
1. Hetzner VPS with Docker (via Portainer or Coolify)
2. Cloudflare Pages (static) + Workers (API) if serverless preferred

**Dockerfile** (for server-capable projects):
```dockerfile
FROM oven/bun:1 AS build
WORKDIR /app
COPY package.json bun.lock ./
RUN bun install --frozen-lockfile
COPY . .
RUN bun run build

FROM oven/bun:1-slim
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/node_modules ./node_modules
COPY package.json .
ENV HOST=0.0.0.0
ENV PORT=4321
EXPOSE 4321
CMD ["bun", "./dist/server/entry.mjs"]
```

---

## Appendix: Rationale

**Why Bun** — Single tool replaces Node, npm, and most build tooling. Fewer moving parts means fewer agent failure modes.

**Why Astro** — Static-first with islands. `.astro` files look like HTML with a server fence. Agents produce reliable output because the mental model is simple.

**Why Alpine** — Lives in HTML attributes (`x-data`, `x-on`, `x-show`). No file switching, no component trees. Everything is colocated and declarative.

**Why HTMX** — Server communication without fetch calls, client state, or API client layers. HTML-native attributes map naturally to how LLMs generate markup.

**Why Markdown** — The lingua franca of LLMs. Agents generate valid `.md` with frontmatter more reliably than any other content format.

**Why PostgreSQL** — Schemas act as contracts. If an agent writes malformed data, it fails loudly. `jsonb` columns provide document-store flexibility within a structured context. Migrations create an auditable history of how the data model evolved — valuable for mission-persistent intelligence. SQL is extremely well-represented in LLM training data — agents produce more reliable SQL than MongoDB aggregation pipelines.

**Why Drizzle** — SQL-close without heavy abstraction. Type-safe. Migration tooling built in. No Prisma schema language, no Mongoose magic. Just tables, columns, and queries.