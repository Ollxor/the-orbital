# The Overview — Website Update Instructions

## Summary of changes

Rename the site from "The Garden Landscape" to "The Overview." Update the landing page with a header section above the existing newsfeed. Add a "Why this matters" line to each news card. Add an About page. Hide the People page from public navigation. Add a basic "Join" flow with moderation. Minor copy and branding updates throughout. Update the domain you are deploying to.

---

## 1. Site name and branding

**Old name:** The Garden Landscape  
**New name:** The Overview  
**Subtitle:** Prototyping Our Way Towards Paradise  
**Tagline (footer/meta):** A living map of the movements building planetary governance  

Update the site title, browser tab title, meta tags, Open Graph tags, and any references in navigation or footer.

The Overview is both the name of this site and the working name for the broader initiative. The overall project does not have a final name yet — it is a game about building paradise, and the name will emerge as the project develops. For now, reference it simply as "the project" or "the initiative" where needed. Do not call it "The Garden" — that name may be used for one of the orientations or something else later. Update the domain you are deploying to.

---

## 2. Landing page header

The newsfeed remains the landing page. But add a header section above the feed. This header should be visible on first load without scrolling (or with minimal scrolling on mobile). It should feel like an invitation, not a wall of text.

### Header content (approximately):

```
THE OVERVIEW
Prototyping Our Way Towards Paradise

A living map of the people, organisations, and movements 
already building the future of planetary governance — 
through ecology, technology, play, ritual, and democratic innovation.

Four orientations. One emerging pattern.
```

Below that text, show four compact orientation cards in a horizontal row (stacking on mobile), colour-coded:

```
🌱 Garden of Eden [green: #D5E8D4]
Living systems, land stewardship, regenerative economics, indigenous knowledge.

🚀 Spaceship Earth [blue: #DAE8FC]  
Technology, infrastructure, data, AI, governance tools, alternative ownership.

🔮 Eleusinian Mysteries [purple: #E1D5E7]
Transformative games, ritual, experiential futures, festival culture, the psychology of awe.

🌍 General Assembly of Earth [gold: #FFF2CC]
Global governance innovation, participatory democracy, rights of nature, climate justice.
```

Each card is clickable and links to the corresponding orientation filter page (already exists at /orientations/GARDEN etc).

Below the orientation cards, the newsfeed begins with the existing "From the Field" section.

### Design notes:
- Keep it clean and minimal. No hero images or animations. The content is the hero.
- The header should not feel like a separate page — it should flow naturally into the feed.
- On return visits, users might want to skip straight to the feed. Consider a subtle "Skip to feed ↓" link, or make the header collapsible / shorter on subsequent visits (cookie-based).
- The orientation cards should use the same colour coding as the existing tag system.

---

## 3. "Why this matters" on news cards

Each news story card currently has: image, date, headline, summary, actor link, tags.

Add a new line after the summary, visually distinct (slightly smaller, different weight or colour), that connects the story to the larger Garden vision. Format:

```
Why this matters → [one sentence connecting to the pattern]
```

Examples based on existing stories:

- Kiss the Ground grants story: "Why this matters → Regenerative agriculture only scales when the financial architecture supports the people doing the work — the same design challenge the Assembly faces at every level."

- River Reuss referendum story: "Why this matters → If a Swiss canton can grant legal personhood to a river through direct democracy, the question shifts from whether governance can include nature to how fast."

- Luleå transition exhibition: "Why this matters → Governance that hides in policy documents stays abstract. Governance that shows up in a shopping mall becomes culture."

These lines should be written editorially (by humans or AI with human review), not auto-generated. They are the editorial voice of The Overview — the thing that turns a news aggregator into a publication with a perspective.

For existing stories that don't yet have this line, add them retroactively. For new stories going forward, make it a required field in the CMS/content pipeline.

---

## 4. About page

Add an "About" link in the main navigation (after "Feed", before "Actors").

### About page content:

```
ABOUT THE OVERVIEW

The Overview is a living map of the emerging movement for 
planetary governance — the people, organisations, networks, 
and initiatives already building the systems that could 
make a thriving future possible.

The name comes from the Overview Effect: the cognitive shift 
astronauts experience when seeing Earth from space. A border 
dissolves — not a political border, a psychological one. The 
one that separates you from everything else.

We believe that shift is possible on the ground. And we 
believe it is already happening — scattered across thousands 
of initiatives that don't yet see themselves as part of the 
same pattern.

The Overview exists to make that pattern visible.


THE FOUR ORIENTATIONS

The landscape organises around four orientations — not rigid 
categories, but positions in a field. Most people and 
organisations carry more than one.

[Show the same four orientation cards as the landing page, 
but with slightly longer descriptions:]

Garden of Eden
Those who organise around living relationship with land, 
ecology, food, and the tending of what exists. The garden is 
cultivation, embodiment, care, beauty, wildness. Every 
culture that has ever listened to the land belongs here.

Spaceship Earth
Those who organise around building, systems-thinking, 
technology, and the design of what doesn't yet exist. The 
spaceship is infrastructure, data, code, governance 
protocols. Every tradition of collective ingenuity belongs here.

Eleusinian Mysteries
Those who organise around ritual, performance, play, the 
sacred, and the transmission of wisdom that cannot be written 
down. The mystery is transformation, awe, and the technologies 
of meaning. Every culture that has ever used ceremony to hold 
its people together belongs here.

General Assembly of Earth
The cross-cutting frame where the other three meet. Global 
governance innovation, participatory democracy, rights of 
nature, climate justice, and the institutional design that 
could hold it all together.


THE PROJECT

The Overview is part of a larger initiative — still unnamed — 
to prototype planetary governance through play, simulation, 
and embodied experience.

The core premise: Eden is not behind us. It has never existed. 
It is something we could, for the first time in history, 
actually build. The question is not how we avoid crashing the 
ship — it is what kind of world is worth living in, and how 
we design it together.

The initiative is developing prototype assemblies where 
participants don't discuss governance — they govern. They 
don't theorise about alternative economies — they trade and 
invest within one. They don't read about the future — they 
live inside it for a weekend and carry that experience home.

The first prototype is planned for autumn 2026 in Sweden.

[Placeholder: link to manifesto PDF — coming soon]


CONTACT

The Overview is maintained by Olle Bjerkås, Martin Källström, 
and collaborators.

[contact email]
[link to ollebjerkas.se]
```

---

## 5. Hide the People page

Remove "People" from the main public navigation.

The page and its data should still exist and be accessible via direct URL (for admin/internal use), but it should not be discoverable through the site navigation. 

Optionally: add a simple password gate or basic auth to the People page so it's not indexable by search engines. Add a `noindex` meta tag to it either way.

---

## 6. Join / Sign up flow (basic first version)

Add a "Join the map" link in the navigation (or in the header section).

This is NOT a full account system. It's a simple submission form:

### Form fields:
- Name
- Email
- Organisation (optional)
- Short description: "What are you working on?" (max 280 characters)
- Orientation affinity: "Which orientation(s) resonate with you?" (multi-select checkboxes: Garden of Eden, Spaceship Earth, Eleusinian Mysteries, General Assembly of Earth)
- Location (city/country)
- Website or social link (optional)
- "How did you find The Overview?" (optional, freetext)

### Submission flow:
1. User fills in form and submits
2. User sees confirmation: "Thanks! Your submission will be reviewed by our team before appearing on the map."
3. Submission goes to a moderation queue (email notification to admin, or a simple admin dashboard)
4. Admin reviews and approves/rejects
5. Approved submissions appear on the Actors page (or a new "Community" section)

### Anti-spam:
- Honeypot field (hidden field that bots fill in, humans don't)
- Rate limiting (max 3 submissions per IP per hour)
- No CAPTCHA needed for v1 — honeypot + rate limiting is sufficient at this scale

### Privacy:
- Email is never displayed publicly
- Only name, organisation, description, orientation, location, and link are shown after approval
- Include a short privacy note: "Your email is only used to contact you about your submission. It is never displayed publicly or shared."

---

## 7. Navigation update

Current nav: Feed | Actors | Projects | People | Events | Tags | Graph

New nav: Feed | About | Actors | Projects | Events | Tags | Graph | Join

Remove People from the nav. Add About and Join.

Consider whether the nav is getting long. On mobile, it may need to collapse into a hamburger menu if it doesn't already.

---

## 8. Footer update

Current footer: "The Garden — Planetary Governance Research / Landscape Database"

New footer:
```
The Overview — Prototyping Our Way Towards Paradise
Contact: [email] · [link to About page]
```

---

## 9. Minor updates

- Add `<meta name="description" content="A living map of the movements building planetary governance — through ecology, technology, play, ritual, and democratic innovation.">` 
- Update Open Graph title and description for social sharing
- If the site has an RSS feed, update its title to "The Overview"
- If there's a favicon, consider a simple icon that works at small sizes (a small circle with four coloured quadrants matching the orientations, or similar)

---

## 10. Orientation reaction icons on news stories

Each news story card gets a set of four small reaction buttons at the bottom, after the tags. These let readers signal which orientation they see the story through.

### The four reaction icons:

```
🌱  Garden of Eden     — colour: #D5E8D4 / green
🚀  Spaceship Earth    — colour: #DAE8FC / blue  
🔮  Eleusinian Mysteries — colour: #E1D5E7 / purple
🌍  General Assembly   — colour: #FFF2CC / gold
```

### How they work:

- Each icon is a small clickable button, shown in a horizontal row beneath the story tags
- A reader can click one or more icons per story (multi-select, not single-select — a story can feel like both Garden and Spaceship)
- On click, the icon fills with its orientation colour and a counter increments: 🌱 12  🚀 34  🔮 7  🌍 28
- No login required to react. Use localStorage or a simple anonymous session to prevent one person spamming the same story, but don't gate it behind sign-up — the friction should be near zero
- The counts are visible to everyone — they are part of the content, not hidden analytics

### What this generates:

- A real-time "orientation heat map" across all stories — which orientations are most represented in the news, and which are people paying attention to
- A per-story orientation profile — does the community see the Swiss river referendum as primarily Assembly (governance/legal) or Mysteries (sacred/ritual)? The distribution is interesting data
- Over time, it reveals how the community thinks about the world — which is exactly the kind of data a governance simulation project needs

### Display:

On each news card, below the tags:

```
[tags row]

🌱 12   🚀 34   🔮 7   🌍 28     ← small, subtle, not dominant
```

On the story detail page, show the same reactions but slightly larger, with the orientation names visible on hover/tap:

```
🌱 Garden of Eden: 12   🚀 Spaceship Earth: 34   🔮 Eleusinian Mysteries: 7   🌍 General Assembly: 28
```

### Technical notes:
- Store reaction counts in a simple key-value store (Cloudflare KV works well for this on a Pages site)
- No user accounts needed — just increment a counter per story per orientation
- Rate limit: max 4 reactions per story per session (one per orientation)
- Consider adding a small "What's this?" tooltip on first visit: "How do you see this story? Tag it with the orientation(s) that resonate."

### Design notes:
- The icons should feel inviting but not demand attention. They are a quiet game mechanic, not a social media engagement trap.
- Don't show "0" counts — show the icons without numbers until the first reaction comes in, then show counts
- The emoji icons (🌱🚀🔮🌍) are placeholders — if the site develops custom icons for the orientations, use those instead. But emoji work fine for v1.

---

## What NOT to change

- The newsfeed content and format is working well. Don't redesign the cards.
- The orientation colour coding is good. Keep it consistent.
- The Actors, Projects, Events, Tags, and Graph pages are fine as-is for now.
- Don't add complexity to the tech stack. This is a Cloudflare Pages static site — keep it static where possible. The Join form can submit to a simple backend (Cloudflare Workers, a Google Form, or even a Formspree/Formspark endpoint).
