interface Env {
  REACTIONS: KVNamespace;
}

interface ReactionCounts {
  garden: number;
  spaceship: number;
  temple: number;
  assembly: number;
}

const VALID_ORIENTATIONS = ["garden", "spaceship", "temple", "assembly"];

function emptyReactions(): ReactionCounts {
  return { garden: 0, spaceship: 0, temple: 0, assembly: 0 };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

// GET /api/reactions?slug=some-article-slug
// Returns counts for a single slug, or batch with ?slugs=a,b,c
export const onRequestGet: PagesFunction<Env> = async (context) => {
  const url = new URL(context.request.url);
  const slug = url.searchParams.get("slug");
  const slugs = url.searchParams.get("slugs");

  if (slug) {
    const raw = await context.env.REACTIONS.get(`reactions:${slug}`);
    const counts = raw ? JSON.parse(raw) : emptyReactions();
    return jsonResponse(counts);
  }

  if (slugs) {
    const slugList = slugs.split(",").slice(0, 50); // max 50 at once
    const results: Record<string, ReactionCounts> = {};
    await Promise.all(
      slugList.map(async (s) => {
        const raw = await context.env.REACTIONS.get(`reactions:${s}`);
        results[s] = raw ? JSON.parse(raw) : emptyReactions();
      })
    );
    return jsonResponse(results);
  }

  return jsonResponse({ error: "Provide ?slug= or ?slugs= parameter" }, 400);
};

// POST /api/reactions
// Body: { slug: "article-slug", orientation: "garden" }
export const onRequestPost: PagesFunction<Env> = async (context) => {
  let body: { slug?: string; orientation?: string };
  try {
    body = await context.request.json();
  } catch {
    return jsonResponse({ error: "Invalid request body" }, 400);
  }

  const slug = (body.slug || "").trim();
  const orientation = (body.orientation || "").trim().toLowerCase();

  if (!slug) {
    return jsonResponse({ error: "slug is required" }, 400);
  }
  if (!VALID_ORIENTATIONS.includes(orientation)) {
    return jsonResponse({ error: "Invalid orientation" }, 400);
  }

  const key = `reactions:${slug}`;
  const raw = await context.env.REACTIONS.get(key);
  const counts: ReactionCounts = raw ? JSON.parse(raw) : emptyReactions();

  counts[orientation as keyof ReactionCounts]++;

  await context.env.REACTIONS.put(key, JSON.stringify(counts));

  return jsonResponse(counts);
};
