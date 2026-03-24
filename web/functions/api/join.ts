interface Env {
  SUBMISSIONS: KVNamespace;
}

interface JoinSubmission {
  name: string;
  email: string;
  organisation?: string;
  description: string;
  orientations: string[];
  location: string;
  link?: string;
  referral?: string;
  website_url?: string;
}

function sanitizeName(name: string): string {
  return name
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

function isValidEmail(email: string): boolean {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function jsonResponse(body: Record<string, unknown>, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

export const onRequestPost: PagesFunction<Env> = async (context) => {
  const { request, env } = context;

  // Parse body
  let body: JoinSubmission;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: "Invalid request body." }, 400);
  }

  // Honeypot check — return 200 silently to avoid revealing detection
  if (body.website_url) {
    return jsonResponse({ success: true });
  }

  // Validate required fields
  const name = (body.name || "").trim();
  const email = (body.email || "").trim();
  const description = (body.description || "").trim();
  const location = (body.location || "").trim();
  const orientations = body.orientations || [];

  if (!name) {
    return jsonResponse({ error: "Name is required." }, 400);
  }
  if (!email || !isValidEmail(email)) {
    return jsonResponse({ error: "A valid email is required." }, 400);
  }
  if (!description) {
    return jsonResponse({ error: "Please describe what you are working on." }, 400);
  }
  if (description.length > 280) {
    return jsonResponse({ error: "Description must be 280 characters or fewer." }, 400);
  }
  if (!location) {
    return jsonResponse({ error: "Location is required." }, 400);
  }
  if (!Array.isArray(orientations) || orientations.length === 0) {
    return jsonResponse({ error: "Please select at least one orientation." }, 400);
  }

  const validOrientations = [
    "garden-of-eden",
    "spaceship-earth",
    "eleusinian-mysteries",
    "general-assembly",
  ];
  const invalidOrientations = orientations.filter(
    (o) => !validOrientations.includes(o)
  );
  if (invalidOrientations.length > 0) {
    return jsonResponse({ error: "Invalid orientation selected." }, 400);
  }

  // Rate limiting — max 3 submissions per hour per IP
  const ip = request.headers.get("CF-Connecting-IP") || "unknown";
  const rateLimitKey = `ratelimit:${ip}`;
  const rateLimitRaw = await env.SUBMISSIONS.get(rateLimitKey);
  const now = Date.now();
  const oneHour = 60 * 60 * 1000;

  let timestamps: number[] = [];
  if (rateLimitRaw) {
    try {
      timestamps = JSON.parse(rateLimitRaw);
    } catch {
      timestamps = [];
    }
  }

  // Filter to timestamps within the last hour
  timestamps = timestamps.filter((ts) => now - ts < oneHour);

  if (timestamps.length >= 3) {
    return jsonResponse(
      { error: "Too many submissions. Please try again later." },
      429
    );
  }

  // Record this submission timestamp
  timestamps.push(now);
  await env.SUBMISSIONS.put(rateLimitKey, JSON.stringify(timestamps), {
    expirationTtl: 3600,
  });

  // Store submission
  const timestamp = new Date().toISOString();
  const sanitized = sanitizeName(name);
  const kvKey = `join:${timestamp}:${sanitized}`;

  const submission = {
    name,
    email,
    organisation: (body.organisation || "").trim(),
    description,
    orientations,
    location,
    link: (body.link || "").trim(),
    referral: (body.referral || "").trim(),
    submittedAt: timestamp,
    ip,
  };

  await env.SUBMISSIONS.put(kvKey, JSON.stringify(submission));

  return jsonResponse({ success: true });
};
