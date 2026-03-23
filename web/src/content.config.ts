import { defineCollection } from 'astro:content';
import { glob } from 'astro/loaders';
import { z } from 'astro/zod';

const news = defineCollection({
  loader: glob({ pattern: '**/*.md', base: './src/content/news' }),
  schema: z.object({
    title: z.string(),
    date: z.coerce.date(),
    summary: z.string(),
    featured: z.boolean().default(false),
    image: z.string().optional(),
    imageAlt: z.string().optional(),
    actors: z.array(z.number()).default([]),
    projects: z.array(z.number()).default([]),
    tags: z.array(z.string()).default([]),
    sources: z.array(z.object({
      title: z.string(),
      url: z.string().url(),
    })).default([]),
  }),
});

export const collections = { news };
