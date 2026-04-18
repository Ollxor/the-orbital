import type { APIRoute } from 'astro';
import newsData from '../data/news.json';

const SITE = 'https://theorbital.net';

export const GET: APIRoute = () => {
  const sorted = [...newsData].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());

  const items = sorted.map(story => `
    <item>
      <title><![CDATA[${story.title}]]></title>
      <link>${SITE}/news/${story.slug}</link>
      <guid isPermaLink="true">${SITE}/news/${story.slug}</guid>
      <pubDate>${new Date(story.date).toUTCString()}</pubDate>
      <description><![CDATA[${story.summary} — ${story.insight}]]></description>
      ${story.orientations.map(o => `<category>${o}</category>`).join('\n      ')}
    </item>`).join('');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>The Orbital — Planetary Systems Governance</title>
    <link>${SITE}</link>
    <description>Tracking the emergent movement for planetary systems governance.</description>
    <language>en</language>
    <atom:link href="${SITE}/rss.xml" rel="self" type="application/rss+xml" />
    ${items}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: { 'Content-Type': 'application/xml; charset=utf-8' },
  });
};
